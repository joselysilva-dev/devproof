import { useEffect, useRef, useState } from 'react'
import { PublicKey, Transaction, TransactionInstruction } from '@solana/web3.js'
import { Buffer } from 'buffer'
import './App.css'

type Delivery = { title: string; author: string; repository: string; number: number; state: string; url: string; sha: string }
type Proof = { id: string; payload: { delivery: Delivery; statement: string }; hash: string; state: string; confirmation: { wallet: string } | null; transaction: { signature: string } | null; pending_signature?: string; error: string | null }
type Provider = { publicKey: PublicKey | null; connect(): Promise<{ publicKey: PublicKey }>; signMessage(message: Uint8Array, encoding: string): Promise<{ signature: Uint8Array }>; signAndSendTransaction(transaction: Transaction): Promise<{ signature: string }> }
declare global { interface Window { phantom?: { solana?: Provider } } }
const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const labels: Record<string, string> = { rascunho: 'Rascunho', confirmado_por_carteira: 'Confirmado por carteira', aguardando_registro: 'Aguardando registro', registrado: 'Registrado na devnet', falha: 'Falha no registro' }
async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(API + path, { method: body === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(45000) })
  } catch {
    throw new Error('Não foi possível acessar a API no prazo esperado. Confira se o backend está iniciado e tente novamente.')
  }
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Confira os campos e tente novamente.')
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
  const [lookup, setLookup] = useState(new URLSearchParams(location.search).get('comprovante') || '')
  const lock = useRef(false)
  async function run(action: () => Promise<void>) {
    if (lock.current) return
    lock.current = true; setBusy(true); setMessage('')
    try { await action() } catch (error) {
      const walletError = typeof error === 'object' && error !== null && 'code' in error
      setMessage(walletError ? 'A carteira recusou ou não concluiu a solicitação. Confira a conexão, a rede devnet e o saldo de teste.' : error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.')
    }
    finally { lock.current = false; setBusy(false) }
  }
  useEffect(() => {
    const id = new URLSearchParams(location.search).get('comprovante')
    if (id) request<Proof>('/comprovantes/' + encodeURIComponent(id)).then(setProof).catch(error => setMessage(error.message))
  }, [])
  function provider() {
    const p = window.phantom?.solana
    if (!p) throw new Error('Instale a extensão Phantom para conectar uma carteira Solana. Use somente devnet.')
    return p
  }
  async function connect() {
    const result = await provider().connect()
    const address = result.publicKey.toBase58()
    setWallet(address)
    return address
  }
  async function refresh(id: string) { setProof(await request<Proof>('/comprovantes/' + id)) }
  async function confirm() {
    if (!proof) return
    const address = await connect()
    const challenge = await request<{ nonce: string; message: string }>('/comprovantes/' + proof.id + '/desafio', { wallet: address })
    const signed = await provider().signMessage(new TextEncoder().encode(challenge.message), 'utf8')
    setProof(await request<Proof>('/comprovantes/' + proof.id + '/confirmar', { nonce: challenge.nonce, signature: Buffer.from(signed.signature).toString('base64') }))
    setMessage('Confirmação validada pela API. O titular da carteira confirmou esta declaração.')
  }
  async function register(signature?: string) {
    if (!proof) return
    let txSignature = signature
    if (!txSignature) {
      const address = await connect()
      if (address !== proof.confirmation?.wallet) throw new Error('Conecte a mesma carteira que confirmou a declaração.')
      const prep = await request<{ memo: string; program_id: string; wallet: string; blockhash: string; lastValidBlockHeight: number }>('/comprovantes/' + proof.id + '/preparar-registro', {})
      await refresh(proof.id)
      const blockhash = new PublicKey(prep.blockhash).toBase58()
      const tx = new Transaction({ feePayer: new PublicKey(prep.wallet), blockhash, lastValidBlockHeight: prep.lastValidBlockHeight }).add(new TransactionInstruction({ programId: new PublicKey(prep.program_id), keys: [{ pubkey: new PublicKey(prep.wallet), isSigner: true, isWritable: false }], data: Buffer.from(prep.memo, 'utf8') }))
      // Phantom deve estar em devnet; o servidor confirma a rede por genesis hash.
      txSignature = (await provider().signAndSendTransaction(tx)).signature
      localStorage.setItem('devproof:pending:' + proof.id, txSignature)
    }
    try {
      setProof(await request<Proof>('/comprovantes/' + proof.id + '/registrar', { signature: txSignature }))
      localStorage.removeItem('devproof:pending:' + proof.id)
      setMessage('Registro verificado pelo servidor na Solana devnet.')
    } catch (error) { await refresh(proof.id); throw error }
  }
  const current = proof?.payload.delivery || delivery
  const pending = proof ? proof.pending_signature || localStorage.getItem('devproof:pending:' + proof.id) : null
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
          {proof.confirmation && proof.state !== 'registrado' && <><p>Na Phantom, selecione devnet e obtenha SOL de teste no <a href="https://faucet.solana.com" target="_blank" rel="noreferrer">faucet oficial</a>. A transação contém apenas o hash e cobra uma taxa em SOL de teste.</p>{pending ? <button disabled={busy} onClick={() => void run(() => register(pending))}>Verificar transação enviada</button> : <button disabled={busy} onClick={() => void run(() => register())}>Registrar hash na devnet</button>}{proof.state === 'falha' && pending && <p><button disabled={busy} onClick={() => { localStorage.removeItem('devproof:pending:' + proof.id); setProof({ ...proof, pending_signature: undefined }) }}>Preparar nova tentativa</button></p>}</>}
          {proof.error && <p className="erro">{proof.error}</p>}{proof.transaction && <p><a href={'https://explorer.solana.com/tx/' + proof.transaction.signature + '?cluster=devnet'} target="_blank" rel="noreferrer">Ver transação na devnet ↗</a></p>}</>}
      </section>
    </div>
    <section className="painel consulta"><span className="passo">03 / VERIFICAÇÃO</span><h2>Consulte um comprovante</h2><form onSubmit={e => { e.preventDefault(); void run(async () => { const result = await request<Proof>('/comprovantes/' + encodeURIComponent(lookup.trim())); setProof(result); history.replaceState(null, '', '?comprovante=' + result.id); setMessage('Comprovante carregado. Clique em verificar para conferir a integridade.') }) }}><label htmlFor="lookup">ID do comprovante</label><input id="lookup" required value={lookup} onChange={e => setLookup(e.target.value)} /><button disabled={busy}>Consultar comprovante</button></form>{proof && <p><button disabled={busy} onClick={() => void run(async () => { const v = await request<{ integrity: boolean; wallet_signature: boolean; onchain: boolean }>('/comprovantes/' + proof.id + '/verificar', {}); setMessage(`Integridade válida. Assinatura de carteira: ${v.wallet_signature ? 'válida' : 'ainda ausente'}. Registro na devnet: ${v.onchain ? 'verificado novamente' : 'ainda ausente'}.`) })}>Verificar integridade e registro</button></p>}</section>
    <p id="resultado" className="mensagem" role="status" aria-live="polite">{busy ? 'Processando… Aguarde a API ou confirme a solicitação na carteira.' : message}</p>
    <footer>Protótipo para hackathon. Somente devnet. Não informe seed phrase ou chave privada. O hash prova integridade do conteúdo; a declaração permanece uma afirmação do titular da carteira.</footer>
  </main>
}
export default App
