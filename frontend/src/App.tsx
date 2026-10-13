import { useEffect, useRef, useState } from 'react'
import { PublicKey, Transaction, TransactionInstruction } from '@solana/web3.js'
import { Buffer } from 'buffer'
import bs58 from 'bs58'
import { diagnose, verifyBeforeSend, withTimeout } from './registration'
import type { Diagnostic, Stage } from './registration'
import './App.css'

type Delivery = { title: string; author: string; repository: string; number: number; state: string; url: string; sha: string }
type Proof = { id: string; payload: { delivery: Delivery; statement: string }; hash: string; state: string; confirmation: { wallet: string } | null; transaction: { signature: string } | null; pending_signature?: string; error: string | null; error_diagnostic?: Diagnostic }
type Provider = { publicKey: PublicKey | null; connect(): Promise<{ publicKey: PublicKey }>; signMessage(message: Uint8Array, encoding: string): Promise<{ signature: Uint8Array }>; signAndSendTransaction(transaction: Transaction): Promise<{ signature: string }> }
declare global { interface Window { phantom?: { solana?: Provider } } }
function readLocal(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}
function writeLocal(key: string, value: string | null): boolean {
  try { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value); return true } catch { return false }
}
const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const labels: Record<string, string> = { rascunho: 'Rascunho', confirmado_por_carteira: 'Confirmado por carteira', aguardando_registro: 'Aguardando registro', registrado: 'Registrado na devnet', falha: 'Falha no registro' }
async function request<T>(path: string, body?: unknown, stage: Stage = 'api'): Promise<T> {
  let response: Response
  try {
    response = await fetch(API + path, { method: body === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(45000) })
  } catch (error) {
    throw diagnose(error, stage)
  }
  let data
  try { data = await response.json() } catch (error) { throw diagnose(error, stage) }
  if (!response.ok) {
    const detail = data.detail
    const original = typeof detail === 'string' ? detail : detail?.original_message || detail?.message || JSON.stringify(detail)
    const error = diagnose({ code: detail?.code ?? response.status, message: original }, stage)
    error.diagnostic.http_status = response.status
    if (detail?.category === 'timeout') error.diagnostic.category = 'timeout'
    error.diagnostic.message = typeof detail === 'string' ? detail : detail?.message || 'Confira os campos e tente novamente.'
    throw error
  }
  return data
}
function App() {
  const [link, setLink] = useState('')
  const [statement, setStatement] = useState('')
  const [delivery, setDelivery] = useState<Delivery | null>(null)
  const [proof, setProof] = useState<Proof | null>(null)
  const [wallet, setWallet] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [diagnostic, setDiagnostic] = useState<Diagnostic | null>(null)
  const [recoverySignature, setRecoverySignature] = useState('')
  const [lookup, setLookup] = useState(new URLSearchParams(location.search).get('comprovante') || '')
  const lock = useRef(false)
  async function run(action: () => Promise<void>) {
    if (lock.current) return
    lock.current = true; setBusy(true); setMessage(''); setDiagnostic(null)
    try { await action() } catch (error) {
      const detail = diagnose(error, 'api').diagnostic
      setDiagnostic(detail); setMessage(error instanceof Error && !('diagnostic' in error) ? error.message : detail.message)
    }
    finally { lock.current = false; setBusy(false) }
  }
  useEffect(() => {
    const id = new URLSearchParams(location.search).get('comprovante')
    if (id) request<Proof>('/comprovantes/' + encodeURIComponent(id)).then(value => {
      setProof(value)
      try {
        const saved = readLocal('devproof:diagnostic:' + id)
        if (saved) setDiagnostic(JSON.parse(saved) as Diagnostic)
      } catch { /* diagnóstico inválido não impede consultar o comprovante */ }
    }).catch(error => setMessage(error.message))
  }, [])
  function provider() {
    const p = window.phantom?.solana
    if (!p) throw new Error('Instale a extensão Phantom para conectar uma carteira Solana. Use somente devnet.')
    return p
  }
  async function connect() {
    let result
    try { result = await provider().connect() } catch (error) { throw diagnose(error, 'wallet') }
    const address = result.publicKey.toBase58()
    setWallet(address)
    return address
  }
  async function refresh(id: string) { setProof(await request<Proof>('/comprovantes/' + id)) }
  async function confirm() {
    if (!proof) return
    const address = await connect()
    const challenge = await request<{ nonce: string; message: string }>('/comprovantes/' + proof.id + '/desafio', { wallet: address })
    let signed
    try { signed = await provider().signMessage(new TextEncoder().encode(challenge.message), 'utf8') } catch (error) { throw diagnose(error, 'wallet') }
    setProof(await request<Proof>('/comprovantes/' + proof.id + '/confirmar', { nonce: challenge.nonce, signature: Buffer.from(signed.signature).toString('base64') }))
    setMessage('Confirmação validada pela API. O titular da carteira confirmou esta declaração.')
  }
  async function register(signature?: string) {
    if (!proof) return
    // Atualiza o servidor antes de decidir: a tela pode estar desatualizada.
    const latest = await request<Proof>('/comprovantes/' + proof.id)
    setProof(latest)
    if (latest.state === 'registrado') {
      await request('/comprovantes/' + proof.id + '/verificar', {}, 'verify')
      setMessage('Registro existente verificado novamente na devnet.'); return
    }
    let pending = latest.pending_signature || signature || readLocal('devproof:pending:' + proof.id) || undefined
    if (!pending && latest.state === 'aguardando_registro') {
      // Recupera também tentativas feitas antes da correção, sem assinatura armazenada.
      const found = await request<{ signatures: string[] }>('/comprovantes/' + proof.id + '/buscar-registro', {}, 'verify')
      pending = found.signatures[0]
    }
    const remember = (s: string, attemptId?: string) => {
      if (attemptId && readLocal('devproof:attempt:' + proof.id) !== attemptId) {
        writeLocal('devproof:late-signature:' + proof.id, s)
        return
      }
      setProof(p => p?.id === proof.id ? { ...p, pending_signature: s } : p)
      writeLocal('devproof:pending:' + proof.id, s)
    }
    const send = async () => {
      if (readLocal('devproof:uncertain:' + proof.id)) throw new Error('Envio anterior inconclusivo. Busque o registro ou informe a assinatura do histórico da Phantom antes de enviar novamente.')
      const address = await connect()
      if (address !== proof.confirmation?.wallet) throw new Error('Conecte a mesma carteira que confirmou a declaração.')
      const prep = await request<{ memo: string; program_id: string; wallet: string; blockhash: string; lastValidBlockHeight: number; attempt_id: string }>('/comprovantes/' + proof.id + '/preparar-registro', {})
      if (!writeLocal('devproof:attempt:' + proof.id, prep.attempt_id)) throw new Error('Não foi possível guardar a tentativa local. Recupere pela verificação de expiração antes de tentar novamente.')
      await refresh(proof.id)
      const blockhash = new PublicKey(prep.blockhash).toBase58()
      const tx = new Transaction({ feePayer: new PublicKey(prep.wallet), blockhash, lastValidBlockHeight: prep.lastValidBlockHeight }).add(new TransactionInstruction({ programId: new PublicKey(prep.program_id), keys: [{ pubkey: new PublicKey(prep.wallet), isSigner: true, isWritable: false }], data: Buffer.from(prep.memo, 'utf8') }))
      // Phantom deve estar em devnet; o servidor confirma a rede por genesis hash.
      // Se a aba cair após aprovar, não presumir que nenhum envio ocorreu.
      if (!writeLocal('devproof:uncertain:' + proof.id, 'true')) throw new Error('Armazenamento local indisponível. Nenhuma solicitação de envio foi iniciada; habilite o armazenamento antes de registrar.')
      try {
        const operation = provider().signAndSendTransaction(tx).then(result => {
          // A resposta pode chegar depois do timeout da interface: ainda deve ser guardada.
          if (result.signature) remember(result.signature, prep.attempt_id)
          return result
        })
        const result = await withTimeout(operation, 90000)
        if (!result.signature) throw new Error('Phantom não retornou assinatura após solicitação de envio.')
        remember(result.signature, prep.attempt_id)
        writeLocal('devproof:uncertain:' + proof.id, null)
        return result.signature
      } catch (error) {
        const recovered = tx.signature ? bs58.encode(tx.signature) : undefined
        const detail = diagnose(error, 'send', recovered)
        if (detail.diagnostic.category === 'wallet_rejected') writeLocal('devproof:uncertain:' + proof.id, null)
        writeLocal('devproof:diagnostic:' + proof.id, JSON.stringify(detail.diagnostic))
        if (detail.diagnostic.signature) {
          remember(detail.diagnostic.signature)
          // Expõe somente a assinatura pública ao mecanismo de recuperação.
          throw Object.assign(detail, { signature: detail.diagnostic.signature })
        }
        throw detail
      }
    }
    try {
      const result = await verifyBeforeSend(pending, s => request<Proof>('/comprovantes/' + proof.id + '/registrar', { signature: s }, 'verify'), send, remember)
      setProof(result)
      writeLocal('devproof:pending:' + proof.id, null)
      writeLocal('devproof:uncertain:' + proof.id, null)
      setMessage('Registro verificado pelo servidor na Solana devnet.')
    } catch (error) {
      const detail = diagnose(error, 'verify')
      writeLocal('devproof:diagnostic:' + proof.id, JSON.stringify(detail.diagnostic))
      try { await refresh(proof.id) } catch { /* não substituir o erro original */ }
      throw detail
    }
  }
  async function searchRegistration() {
    if (!proof) return
    const result = await request<{ signatures: string[]; scanned: number; message: string }>('/comprovantes/' + proof.id + '/buscar-registro', {}, 'verify')
    if (result.signatures[0]) await register(result.signatures[0])
    else setMessage(`Nenhum registro compatível encontrado em ${result.scanned} transações. ${result.message} Confira o histórico da Phantom; uma tentativa inconclusiva não é liberada automaticamente.`)
  }
  async function recoverAttempt() {
    if (!proof) return
    const latest = await request<Proof>('/comprovantes/' + proof.id)
    const signature = latest.pending_signature || readLocal('devproof:pending:' + proof.id) || undefined
    const result = await request<{ retry_allowed: boolean; registered: boolean; proof: Proof; message: string }>('/comprovantes/' + proof.id + '/recuperar-tentativa', signature ? { signature } : {}, 'verify')
    setProof(result.proof)
    if (result.retry_allowed || result.registered) {
      // Só esta decisão do servidor, baseada em devnet, libera o bloqueio local.
      writeLocal('devproof:uncertain:' + proof.id, null)
      writeLocal('devproof:pending:' + proof.id, null)
      writeLocal('devproof:attempt:' + proof.id, null)
      setRecoverySignature('')
    }
    setMessage(result.message)
  }
  const current = proof?.payload.delivery || delivery
  const pending = proof ? proof.pending_signature || readLocal('devproof:pending:' + proof.id) : null
  return <main className="app">
    <header className="cabecalho"><a className="marca" href="/">DevProof<span>●</span></a><span className="etiqueta">MVP · Solana devnet</span></header>
    <section className="introducao"><p className="destaque">SEU TRABALHO, COM EVIDÊNCIAS</p><h1>Mostre o que você construiu.</h1><p className="descricao">Entregas públicas do GitHub, confirmações por carteira e comprovantes verificáveis.</p></section>
    <div className="grid">
      <section className="painel" aria-labelledby="titulo-entrega"><span className="passo">01 / ENTREGA</span><h2 id="titulo-entrega">Comece com um pull request</h2><p>Cole o link de uma contribuição pública.</p>
        <form onSubmit={e => { e.preventDefault(); void run(async () => {
          if (!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[1-9]\d*\/?$/.test(link.trim())) throw new Error('Informe um link como https://github.com/usuario/repositorio/pull/1')
          const result = await request<Delivery>('/entregas/consultar', { url: link.trim() }); setDelivery(result); setProof(null); setMessage('Dados consultados na API do GitHub.')
        }) }}><label htmlFor="link">Link do pull request no GitHub</label><input id="link" type="url" required value={link} onChange={e => setLink(e.target.value)} placeholder="https://github.com/usuario/repositorio/pull/1" /><button disabled={busy}>Consultar GitHub →</button></form>
        {current && <dl><dt>Título</dt><dd><a href={current.url} target="_blank" rel="noreferrer">{current.title}</a></dd><dt>Autor no GitHub</dt><dd>{current.author}</dd><dt>Repositório / número</dt><dd>{current.repository} #{current.number}</dd><dt>Estado no momento da consulta</dt><dd>{current.state}</dd><dt>URL</dt><dd>{current.url}</dd><dt>SHA do commit da entrega</dt><dd><code>{current.sha}</code></dd></dl>}
      </section>
      <section className="painel" aria-labelledby="titulo-confirmacao"><span className="passo">02 / CONFIRMAÇÃO</span><h2 id="titulo-confirmacao">Declare e confirme</h2><p>A confirmação vem do titular da carteira. Ela não comprova identidade GitHub nem participação no repositório.</p>
        {!proof ? <form onSubmit={e => { e.preventDefault(); void run(async () => { if (!delivery) throw new Error('Consulte uma entrega primeiro.'); const result = await request<Proof>('/comprovantes', { url: delivery.url, statement }); setProof(result); setLookup(result.id); history.replaceState(null, '', '?comprovante=' + result.id); setMessage('Rascunho persistido. Compartilhe o link com o colaborador para confirmar.') }) }}><label htmlFor="statement">Declaração de entrega</label><textarea id="statement" minLength={5} maxLength={1000} required value={statement} onChange={e => setStatement(e.target.value)} placeholder="Descreva o trabalho entregue e o que deve ser confirmado." /><button disabled={busy || !delivery}>Criar declaração</button></form> : <><p className="status">{labels[proof.state]}</p><blockquote>{proof.payload.statement}</blockquote><p>ID: <code>{proof.id}</code></p><p>SHA-256: <code>{proof.hash}</code></p><a href={'?comprovante=' + proof.id}>Link para compartilhar e consultar</a><p><button disabled={busy} onClick={() => void run(async () => { await connect() })}>Conectar Phantom</button></p><p>Carteira conectada: <code>{wallet || 'Nenhuma'}</code></p>{proof.confirmation && <p>Confirmado pelo titular de: <code>{proof.confirmation.wallet}</code></p>}
          {proof.state === 'rascunho' && <button disabled={busy} onClick={() => void run(confirm)}>Assinar confirmação</button>}
          {proof.confirmation && proof.state !== 'registrado' && <><p>Na Phantom, selecione devnet e obtenha SOL de teste no <a href="https://faucet.solana.com" target="_blank" rel="noreferrer">faucet oficial</a>. A transação contém apenas o hash e cobra uma taxa em SOL de teste.</p>{pending ? <button disabled={busy} onClick={() => void run(() => register(pending))}>Verificar transação enviada</button> : <button disabled={busy} onClick={() => void run(() => register())}>Registrar hash na devnet</button>}<p><button disabled={busy} onClick={() => void run(searchRegistration)}>Buscar registro na devnet</button></p><p>Antes de recuperar, feche solicitações antigas pendentes na Phantom. A API só libera novo envio após verificar expiração e histórico finalizado.</p><p><button disabled={busy} onClick={() => void run(recoverAttempt)}>Recuperar tentativa verificando expiração</button></p><form onSubmit={e => { e.preventDefault(); void run(() => register(recoverySignature.trim())) }}><label htmlFor="recovery">Assinatura da transação no histórico da Phantom (opcional)</label><input id="recovery" value={recoverySignature} onChange={e => setRecoverySignature(e.target.value)} pattern="[1-9A-HJ-NP-Za-km-z]{64,90}" required /><button disabled={busy}>Consultar esta assinatura sem reenviar</button></form></>}
          {proof.error && <p className="erro">{proof.error}</p>}{proof.transaction && <p><a href={'https://explorer.solana.com/tx/' + proof.transaction.signature + '?cluster=devnet'} target="_blank" rel="noreferrer">Ver transação na devnet ↗</a></p>}</>}
      </section>
    </div>
    <section className="painel consulta"><span className="passo">03 / VERIFICAÇÃO</span><h2>Consulte um comprovante</h2><form onSubmit={e => { e.preventDefault(); void run(async () => { const result = await request<Proof>('/comprovantes/' + encodeURIComponent(lookup.trim())); setProof(result); history.replaceState(null, '', '?comprovante=' + result.id); setMessage('Comprovante carregado. Clique em verificar para conferir a integridade.') }) }}><label htmlFor="lookup">ID do comprovante</label><input id="lookup" required value={lookup} onChange={e => setLookup(e.target.value)} /><button disabled={busy}>Consultar comprovante</button></form>{proof && <p><button disabled={busy} onClick={() => void run(async () => { const v = await request<{ integrity: boolean; wallet_signature: boolean; onchain: boolean }>('/comprovantes/' + proof.id + '/verificar', {}); setMessage(`Integridade válida. Assinatura de carteira: ${v.wallet_signature ? 'válida' : 'ainda ausente'}. Registro na devnet: ${v.onchain ? 'verificado novamente' : 'ainda ausente'}.`) })}>Verificar integridade e registro</button></p>}</section>
    <p id="resultado" className="mensagem" role="status" aria-live="polite">{busy ? 'Processando… Aguarde a API ou confirme a solicitação na carteira.' : message}</p>
    {(diagnostic || proof?.error_diagnostic) && <details className="painel"><summary>Diagnóstico técnico do erro</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(diagnostic || proof?.error_diagnostic, null, 2)}</pre></details>}
    <footer>Protótipo para hackathon. Somente devnet. Não informe seed phrase ou chave privada. O hash prova integridade do conteúdo; a declaração permanece uma afirmação do titular da carteira.</footer>
  </main>
}
export default App
