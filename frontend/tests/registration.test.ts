import { test } from 'node:test'
import assert from 'node:assert/strict'
import { diagnose, OperationError, verifyBeforeSend, withTimeout } from '../src/registration.ts'

const signature = '2'.repeat(88)
test('somente 4001 é rejeição do usuário; preserva código e mensagem', () => {
  const rejected = diagnose({ code: 4001, message: 'User rejected the request.' }, 'send')
  assert.equal(rejected.diagnostic.category, 'wallet_rejected')
  assert.equal(rejected.diagnostic.original_message, 'User rejected the request.')
  assert.equal(rejected.diagnostic.code, 4001)
  assert.equal(diagnose({ code: -32603, message: 'Internal error' }, 'send').diagnostic.category, 'send_failure')
  assert.equal(diagnose({ code: 4900, message: 'Disconnected' }, 'wallet').diagnostic.category, 'wallet_failure')
})
test('timeout e verificação são distintos', () => {
  assert.equal(diagnose(new DOMException('timed out', 'TimeoutError'), 'send').diagnostic.category, 'timeout')
  assert.equal(diagnose(new Error('API unavailable'), 'verify').diagnostic.category, 'verification_failure')
})
test('assinatura pendente consulta antes e impede novo envio', async () => {
  let sends = 0
  await assert.rejects(verifyBeforeSend(signature, async () => { throw new Error('pending') }, async () => { sends++; return signature }, () => {}), OperationError)
  assert.equal(sends, 0)
})
test('persiste assinatura antes de falha de verificação', async () => {
  let saved = ''
  await assert.rejects(verifyBeforeSend(undefined, async () => { assert.equal(saved, signature); throw new Error('RPC failed') }, async () => signature, s => { saved = s }), (e: unknown) => e instanceof OperationError && e.diagnostic.signature === signature && e.diagnostic.stage === 'verify')
})
test('erro de envio com assinatura consulta registro e recupera sucesso verificado', async () => {
  const result = await verifyBeforeSend(undefined, async s => { assert.equal(s, signature); return 'verified' }, async () => { throw { code: -32603, message: 'Internal error after broadcast', signature } }, () => {})
  assert.equal(result, 'verified')
})
test('falha ao recuperar não mascara erro original de envio', async () => {
  await assert.rejects(verifyBeforeSend(undefined, async () => { throw new Error('RPC down') }, async () => { throw { code: -32603, message: 'Original send failure', signature } }, () => {}), (e: unknown) => e instanceof OperationError && e.diagnostic.code === -32603 && e.diagnostic.original_message === 'Original send failure')
})
test('timeout não cancela a carteira; resposta tardia continua recuperável', async () => {
  let resolve!: (signature: string) => void
  let remembered = ''
  const operation = new Promise<string>(r => { resolve = r }).then(s => { remembered = s; return s })
  await assert.rejects(withTimeout(operation, 1), (e: unknown) => e instanceof DOMException && e.name === 'TimeoutError')
  resolve(signature)
  await operation
  assert.equal(remembered, signature)
})
