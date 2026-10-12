export type Stage = 'api' | 'wallet' | 'send' | 'verify'
export type Diagnostic = {
  category: string; stage: Stage; code: string | number | null; original_message: string;
  name: string; signature?: string; http_status?: number; message: string
}

export class OperationError extends Error {
  diagnostic: Diagnostic
  constructor(diagnostic: Diagnostic) { super(diagnostic.message); this.diagnostic = diagnostic }
}

function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' ? value as Record<string, unknown> : {}
}

export function errorSignature(error: unknown): string | undefined {
  const e = record(error)
  const signature = e.signature ?? record(e.data).signature ?? record(e.error).signature ?? record(e.diagnostic).signature
  return typeof signature === 'string' && /^[1-9A-HJ-NP-Za-km-z]{64,90}$/.test(signature) ? signature : undefined
}

export function withTimeout<T>(operation: Promise<T>, milliseconds: number): Promise<T> {
  // Não cancela uma solicitação da carteira; ela ainda pode retornar após o timeout.
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new DOMException('Wallet request timed out; transaction submission is unknown.', 'TimeoutError')), milliseconds)
    operation.then(value => { clearTimeout(timer); resolve(value) }, error => { clearTimeout(timer); reject(error) })
  })
}

export function diagnose(error: unknown, stage: Stage, signature?: string): OperationError {
  if (error instanceof OperationError) {
    if (signature) error.diagnostic.signature = signature
    return error
  }
  const e = record(error)
  const code = typeof e.code === 'string' || typeof e.code === 'number' ? e.code : null
  const name = typeof e.name === 'string' ? e.name : 'Error'
  const original = typeof e.message === 'string' ? e.message : String(error)
  const timeout = name === 'TimeoutError' || name === 'AbortError' || /timed?\s*out|timeout/i.test(original)
  const rejected = (stage === 'wallet' || stage === 'send') && Number(code) === 4001
  const category = rejected ? 'wallet_rejected' : timeout ? 'timeout' : stage === 'verify' ? 'verification_failure' : stage === 'send' ? 'send_failure' : stage === 'wallet' ? 'wallet_failure' : 'api_failure'
  const message = rejected ? 'Solicitação rejeitada pelo usuário na Phantom.' : timeout ? `Tempo esgotado na etapa ${stage}. O envio pode ter ocorrido; consulte antes de tentar novamente.` : stage === 'send' ? 'Falha ao assinar/enviar pela Phantom. O erro não comprova recusa nem ausência de envio.' : stage === 'verify' ? 'Não foi possível verificar o registro na devnet. Não envie outra transação antes de consultar esta tentativa.' : stage === 'wallet' ? 'Falha na conexão ou assinatura pela carteira. Confira o diagnóstico original.' : 'Falha ao acessar a API. Confira se o backend está iniciado.'
  return new OperationError({ category, stage, code, original_message: original, name, signature: signature || errorSignature(error), message })
}

export async function verifyBeforeSend<T>(pending: string | undefined, verify: (signature: string) => Promise<T>, send: () => Promise<string>, remember: (signature: string) => void): Promise<T> {
  // Uma assinatura conhecida sempre segue para verificação, jamais para outro envio.
  if (pending) {
    try { return await verify(pending) } catch (error) { throw diagnose(error, 'verify', pending) }
  }
  let signature: string
  try { signature = await send() } catch (error) {
    const recovered = errorSignature(error)
    if (recovered) {
      remember(recovered)
      try { return await verify(recovered) } catch { /* mantém o erro original de envio */ }
    }
    throw diagnose(error, 'send', recovered)
  }
  // Persistir antes da consulta: um timeout da API não perde a referência do envio.
  remember(signature)
  try { return await verify(signature) } catch (error) { throw diagnose(error, 'verify', signature) }
}
