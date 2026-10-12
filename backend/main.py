import base64, hashlib, json, os, re, secrets, sqlite3, time, uuid
from pathlib import Path
from contextlib import contextmanager
import base58, httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from nacl.signing import VerifyKey
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).with_name('.env'))
DB = os.getenv('DEVPROOF_DB', str(Path(__file__).with_name('devproof.sqlite3')))
RPC = os.getenv('SOLANA_RPC_URL', 'https://api.devnet.solana.com')
GENESIS = 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG'
MEMO = 'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr'
PATTERN = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/([1-9]\d*)/?$')
app = FastAPI(title='DevProof API')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('FRONTEND_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET','POST'], allow_headers=['Content-Type'])

@contextmanager
def database():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS proofs (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS challenges (nonce TEXT PRIMARY KEY, proof TEXT, wallet TEXT, message TEXT, expires INTEGER, used INTEGER DEFAULT 0)')
    try:
        with con:
            yield con
    finally:
        con.close()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def read_proof(pid, con=None):
    if con is None:
        with database() as conn:
            return read_proof(pid, conn)
    row = con.execute('SELECT data FROM proofs WHERE id=?', (pid,)).fetchone()
    if not row: raise HTTPException(404,'Comprovante não encontrado.')
    return json.loads(row['data'])

def save(con, proof):
    con.execute('INSERT OR REPLACE INTO proofs VALUES (?,?)', (proof['id'],canonical(proof)))

def validate_signature(wallet, message, signature):
    try:
        key = base58.b58decode(wallet)
        if len(key) != 32: raise ValueError()
        VerifyKey(key).verify(message.encode('utf-8'),base64.b64decode(signature,validate=True))
    except Exception:
        raise HTTPException(400,'Assinatura de carteira inválida.')

async def github(link):
    match = PATTERN.fullmatch(link.strip())
    if not match: raise HTTPException(422,'Use https://github.com/usuario/repositorio/pull/1.')
    owner, repo, number = match.groups()
    headers = {'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'}
    if os.getenv('GITHUB_TOKEN'): headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f'https://api.github.com/repos/{owner}/{repo}/pulls/{number}', headers=headers)
        if response.status_code == 404: raise HTTPException(404,'Pull request público não encontrado.')
        if response.status_code in (403,429): raise HTTPException(429,'GitHub limitou a consulta. Aguarde e tente novamente.')
        response.raise_for_status()
        d = response.json()
        if d['base']['repo']['private']: raise HTTPException(400,'Somente repositórios públicos são aceitos.')
        return {'title':d['title'],'author':d['user']['login'],'repository':d['base']['repo']['full_name'],'number':d['number'],'state':'merged' if d['merged'] else d['state'],'url':d['html_url'],'sha':d['head']['sha']}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        raise HTTPException(503,'GitHub indisponível ou resposta inesperada. Tente novamente.')

async def rpc(method, params=None):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response=await client.post(RPC,json={'jsonrpc':'2.0','id':1,'method':method,'params':params or []})
        response.raise_for_status()
        d=response.json()
        if 'error' in d:
            error = d['error']
            raise HTTPException(503, {'category': 'rpc_failure', 'stage': 'verify', 'code': error.get('code'), 'original_message': error.get('message', ''), 'message': 'RPC da Solana recusou a consulta.', 'method': method})
        if 'result' not in d: raise ValueError('Resposta RPC sem result.')
        return d['result']
    except httpx.TimeoutException as exc:
        raise HTTPException(504, {'category': 'timeout', 'stage': 'verify', 'code': type(exc).__name__, 'original_message': str(exc), 'message': 'Tempo esgotado ao consultar a devnet. A transação pode ter sido enviada.', 'method': method}) from exc
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(503, {'category': 'rpc_failure', 'stage': 'verify', 'code': type(exc).__name__, 'original_message': str(exc), 'message': 'RPC da Solana indisponível. Tente verificar novamente.', 'method': method}) from exc

async def devnet():
    if await rpc('getGenesisHash') != GENESIS: raise HTTPException(400,'Rede incompatível: somente Solana devnet é permitida.')

def memo_text(proof): return 'devproof:v1:'+proof['hash']

async def check_transaction(proof, signature, commitment='confirmed'):
    try:
        if len(base58.b58decode(signature)) != 64:
            raise ValueError()
    except ValueError:
        raise HTTPException(400, 'Formato da assinatura de transação inválido.')
    await devnet()
    tx=await rpc('getTransaction',[signature,{'encoding':'json','commitment':commitment,'maxSupportedTransactionVersion':0}])
    if tx is None: raise HTTPException(409,'Transação ainda não confirmada ou não encontrada na devnet.')
    try:
        message=tx['transaction']['message']
        keys=message['accountKeys']
        signers=keys[:message['header']['numRequiredSignatures']]
        expected=proof['confirmation']['wallet']
        valid=False
        for ix in message['instructions']:
            if keys[ix['programIdIndex']]==MEMO:
                text=base58.b58decode(ix['data']).decode('utf-8')
                accounts=[keys[i] for i in ix['accounts']]
                if text==memo_text(proof) and expected in accounts and expected in signers: valid=True
        if tx['meta'] is None or tx['meta']['err'] is not None or not valid or tx['transaction']['signatures'][0]!=signature: raise ValueError()
        return {'slot':tx['slot'],'block_time':tx['blockTime'],'network':'devnet','signature':signature}
    except (KeyError,IndexError,ValueError,UnicodeError,TypeError):
        raise HTTPException(400,'Transação incompatível: confira sucesso, memo e signatário esperado.')

class Link(BaseModel):
    url: str=Field(max_length=500)
class Declaration(Link):
    statement: str=Field(min_length=5,max_length=1000)
class Wallet(BaseModel):
    wallet: str=Field(max_length=50)
class Confirmation(BaseModel):
    nonce: str=Field(max_length=100)
    signature: str=Field(max_length=100)
class Transaction(BaseModel):
    signature: str=Field(min_length=64,max_length=90)

class RecoveryRequest(BaseModel):
    signature: str | None = Field(default=None, min_length=64, max_length=90)

@app.get('/health')
def health():
    with database() as con: con.execute('SELECT 1')
    return {'status':'ok','projeto':'DevProof','storage':'sqlite','network':'devnet'}

@app.post('/entregas/consultar')
async def consult(body: Link): return await github(body.url)

@app.post('/comprovantes',status_code=201)
async def create(body: Declaration):
    if len(body.statement.strip())<5: raise HTTPException(422,'Descreva a entrega em pelo menos cinco caracteres.')
    pid=str(uuid.uuid4())
    payload={'version':'devproof/1','id':pid,'created_at':int(time.time()),'delivery':await github(body.url),'statement':body.statement.strip()}
    proof={'id':pid,'payload':payload,'hash':digest(payload),'state':'rascunho','confirmation':None,'transaction':None,'error':None}
    with database() as con: save(con,proof)
    return proof

@app.get('/comprovantes/{pid}')
def get_proof(pid: str): return read_proof(pid)

@app.post('/comprovantes/{pid}/desafio')
def challenge(pid: str,body: Wallet):
    try:
        if len(base58.b58decode(body.wallet))!=32: raise ValueError()
    except ValueError: raise HTTPException(422,'Endereço de carteira inválido.')
    proof=read_proof(pid)
    if proof['state']!='rascunho': raise HTTPException(409,'Comprovante já confirmado.')
    integrity(proof)
    nonce=secrets.token_hex(32)
    expires=int(time.time())+600
    message=canonical({'domain':'DevProof','version':1,'network':'devnet','intent':'confirm_delivery','wallet':body.wallet,'proof_id':pid,'delivery_url':proof['payload']['delivery']['url'],'hash':proof['hash'],'nonce':nonce,'expires_at':expires})
    with database() as con: con.execute('INSERT INTO challenges (nonce,proof,wallet,message,expires) VALUES (?,?,?,?,?)',(nonce,pid,body.wallet,message,expires))
    return {'nonce':nonce,'message':message,'expires_at':expires}

@app.post('/comprovantes/{pid}/confirmar')
def confirm(pid: str,body: Confirmation):
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT * FROM challenges WHERE nonce=? AND proof=?',(body.nonce,pid)).fetchone()
        if not row or row['used'] or row['expires']<=time.time(): raise HTTPException(409,'Desafio expirado, inexistente ou já utilizado.')
        proof=read_proof(pid,con)
        if proof['state']!='rascunho': raise HTTPException(409,'Comprovante já confirmado.')
        integrity(proof)
        validate_signature(row['wallet'],row['message'],body.signature)
        proof['confirmation']={'wallet':row['wallet'],'message':row['message'],'signature':body.signature,'confirmed_at':int(time.time())}
        proof['state']='confirmado_por_carteira'
        con.execute('UPDATE challenges SET used=1 WHERE proof=?',(pid,))
        save(con,proof)
    return proof

def integrity(proof):
    if proof['id']!=proof['payload']['id'] or digest(proof['payload'])!=proof['hash']: raise HTTPException(400,'Integridade inválida: conteúdo alterado.')
    if proof['confirmation']:
        c=proof['confirmation']
        validate_signature(c['wallet'],c['message'],c['signature'])
        try: signed=json.loads(c['message'])
        except ValueError: raise HTTPException(400,'Mensagem inválida.')
        expected={'domain':'DevProof','version':1,'network':'devnet','intent':'confirm_delivery','wallet':c['wallet'],'proof_id':proof['id'],'delivery_url':proof['payload']['delivery']['url'],'hash':proof['hash']}
        if any(signed.get(k)!=v for k,v in expected.items()): raise HTTPException(400,'Confirmação não corresponde ao comprovante.')

@app.post('/comprovantes/{pid}/preparar-registro')
async def prepare(pid: str):
    proof=read_proof(pid)
    if not proof['confirmation'] or proof['state']=='registrado': raise HTTPException(409,'Confirme com a carteira antes de registrar; registro concluído é imutável.')
    if proof.get('pending_signature'):
        raise HTTPException(409, 'Há assinatura pendente. Consulte o registro antes de permitir outro envio.')
    if proof['state'] == 'aguardando_registro' or proof.get('registration_attempt') or proof.get('recovery'):
        raise HTTPException(409, 'Resolva a tentativa anterior pela recuperação com verificação de expiração.')
    integrity(proof)
    await devnet()
    block=await rpc('getLatestBlockhash',[{'commitment':'confirmed'}])
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        proof=read_proof(pid,con)
        if proof['state']=='registrado': raise HTTPException(409,'Comprovante já registrado.')
        if proof.get('pending_signature'):
            raise HTTPException(409, 'Há assinatura pendente. Consulte o registro antes de permitir outro envio.')
        if proof['state'] == 'aguardando_registro' or proof.get('registration_attempt') or proof.get('recovery'):
            raise HTTPException(409, 'Existe outra tentativa ativa. Verifique a expiração antes de preparar novamente.')
        proof.update(state='aguardando_registro',error=None)
        proof['registration_attempt'] = {'id': str(uuid.uuid4()), 'blockhash': block['value']['blockhash'], 'last_valid_block_height': block['value']['lastValidBlockHeight'], 'context_slot': block['context']['slot'], 'wallet': proof['confirmation']['wallet'], 'hash': proof['hash'], 'prepared_at': int(time.time())}
        save(con,proof)
    return {'memo':memo_text(proof),'program_id':MEMO,'wallet':proof['confirmation']['wallet'],'attempt_id':proof['registration_attempt']['id'],**block['value']}

@app.post('/comprovantes/{pid}/registrar')
async def register(pid: str,body: Transaction):
    proof=read_proof(pid)
    if not proof['confirmation']: raise HTTPException(409,'Confirmação de carteira necessária.')
    if proof['state']=='registrado':
        if proof['transaction']['signature']!=body.signature: raise HTTPException(409,'Comprovante já registrado com outra transação.')
        return proof
    # Guarda a referência antes de chamar a rede; timeout ou queda não apaga o envio.
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        current = read_proof(pid, con)
        if current['state'] == 'registrado':
            if current['transaction']['signature'] != body.signature:
                raise HTTPException(409, 'Comprovante já registrado com outra transação.')
            return current
        if current.get('pending_signature') and current['pending_signature'] != body.signature:
            raise HTTPException(409, 'Consulte primeiro a assinatura pendente; não substitua uma tentativa não resolvida.')
        current['pending_signature'] = body.signature
        current['state'] = 'aguardando_registro'
        save(con, current)
    try:
        integrity(proof)
        result=await check_transaction(proof,body.signature)
    except HTTPException as exc:
        with database() as con:
            con.execute('BEGIN IMMEDIATE')
            current=read_proof(pid,con)
            if current['state']!='registrado':
                detail = exc.detail
                diagnostic = detail if isinstance(detail, dict) else {'category': 'verification_failure', 'stage': 'verify', 'code': exc.status_code, 'original_message': detail, 'message': detail}
                current.update(state='aguardando_registro' if exc.status_code in (409,503,504) else 'falha',error=diagnostic['message'],error_diagnostic=diagnostic,pending_signature=body.signature)
                save(con,current)
        raise
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        proof=read_proof(pid,con)
        if proof['state']=='registrado': return proof
        proof.update(state='registrado',transaction=result,error=None)
        proof.pop('error_diagnostic', None)
        proof.pop('pending_signature',None)
        save(con,proof)
    return proof

@app.post('/comprovantes/{pid}/buscar-registro')
async def find_registration(pid: str):
    """Busca limitada; ausência no histórico não é prova de que nunca houve envio."""
    proof = read_proof(pid)
    if not proof['confirmation']:
        raise HTTPException(409, 'Confirmação de carteira necessária.')
    integrity(proof)
    await devnet()
    signatures = await rpc('getSignaturesForAddress', [proof['confirmation']['wallet'], {'limit': 100, 'commitment': 'confirmed'}])
    found = []
    for entry in signatures:
        if entry.get('blockTime') is not None and entry['blockTime'] < proof['confirmation']['confirmed_at']:
            continue
        if entry.get('memo') and proof['hash'] not in entry['memo']:
            continue
        try:
            await check_transaction(proof, entry['signature'])
            found.append(entry['signature'])
        except HTTPException as exc:
            if exc.status_code not in (400, 409):
                raise
    return {'signatures': found, 'scanned': len(signatures), 'limit': 100, 'message': 'A busca considera até 100 transações confirmadas. Ausência de resultado não exclui envio pendente ou fora desse histórico.'}

@app.post('/comprovantes/{pid}/verificar')
async def verify(pid: str):
    proof=read_proof(pid)
    integrity(proof)
    if proof['transaction']: await check_transaction(proof,proof['transaction']['signature'])
    return {'integrity':True,'wallet_signature':bool(proof['confirmation']),'onchain':bool(proof['transaction']),'network':'devnet','checked_at':int(time.time())}


async def finalized_registration_scan(proof):
    """Só uma busca paginada concluída permite decidir ausência no RPC confiável."""
    options = {'limit': 100, 'commitment': 'finalized'}
    scanned = 0
    seen = set()
    for _ in range(10):
        page = await rpc('getSignaturesForAddress', [proof['confirmation']['wallet'], options])
        for entry in page:
            signature = entry['signature']
            if signature in seen:
                raise HTTPException(409, 'Histórico repetido pelo RPC; recuperação inconclusiva.')
            seen.add(signature)
            scanned += 1
            if entry.get('memo') and proof['hash'] not in entry['memo']:
                continue
            try:
                result = await check_transaction(proof, signature, commitment='finalized')
                return result, scanned
            except HTTPException as exc:
                if exc.status_code != 400:
                    # Mesmo um null para uma entrada do histórico deixa lacuna.
                    raise
        if len(page) < 100:
            return None, scanned
        options = {**options, 'before': page[-1]['signature']}
    raise HTTPException(409, 'Limite de 1000 transações atingido. Histórico incompleto; bloqueio mantido.')


@app.post('/comprovantes/{pid}/recuperar-tentativa')
async def recover_attempt(pid: str, body: RecoveryRequest):
    proof = read_proof(pid)
    integrity(proof)
    if not proof['confirmation']:
        raise HTTPException(409, 'Confirmação de carteira necessária.')
    await devnet()
    if proof['state'] == 'registrado':
        await check_transaction(proof, proof['transaction']['signature'])
        return {'retry_allowed': False, 'registered': True, 'proof': proof, 'message': 'Registro existente verificado. Não reenvie.'}
    if body.signature:
        try:
            if len(base58.b58decode(body.signature)) != 64:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, 'Assinatura pública de transação inválida.')
        with database() as con:
            con.execute('BEGIN IMMEDIATE')
            current = read_proof(pid, con)
            if canonical(current) != canonical(proof):
                raise HTTPException(409, 'Tentativa mudou durante a consulta. Recarregue.')
            if current.get('pending_signature') and current['pending_signature'] != body.signature:
                raise HTTPException(409, 'A assinatura informada difere da tentativa pendente.')
            current['pending_signature'] = body.signature
            save(con, current)
            proof = current
    attempt = proof.get('registration_attempt')
    frontier = proof.get('recovery')
    history = proof.get('registration_history', [])
    if (not attempt and not frontier and not proof.get('pending_signature')
            and proof['state'] == 'confirmado_por_carteira' and history
            and history[-1]['evidence']['reason'] == 'expired_and_finalized_history_checked'):
        return {'retry_allowed': True, 'registered': False, 'proof': proof,
                'evidence': history[-1]['evidence'],
                'message': 'Tentativa anterior já recuperada. Uma nova tentativa pode ser preparada.'}
    if not attempt and not frontier:
        # Tentativa legada: não inventa o blockhash perdido. Um marco posterior
        # limita a validade de qualquer hash preparado ANTES deste marco.
        block = await rpc('getLatestBlockhash', [{'commitment': 'processed'}])
        frontier = {'id': str(uuid.uuid4()), 'kind': 'legacy_expiry_frontier', 'blockhash': block['value']['blockhash'], 'last_valid_block_height': block['value']['lastValidBlockHeight'], 'context_slot': block['context']['slot'], 'wallet': proof['confirmation']['wallet'], 'hash': proof['hash'], 'started_at': int(time.time())}
        with database() as con:
            con.execute('BEGIN IMMEDIATE')
            current = read_proof(pid, con)
            if canonical(current) != canonical(proof):
                raise HTTPException(409, 'Tentativa mudou durante a consulta. Recarregue.')
            current['recovery'] = frontier
            save(con, current)
        return {'retry_allowed': False, 'registered': False, 'last_valid_block_height': frontier['last_valid_block_height'], 'proof': current, 'message': 'Marco de expiração criado para a tentativa antiga. Aguarde a altura finalizada ultrapassar o limite e consulte a recuperação novamente.'}
    bound = attempt or frontier
    if bound['wallet'] != proof['confirmation']['wallet'] or bound['hash'] != proof['hash']:
        raise HTTPException(409, 'Dados da tentativa não correspondem ao comprovante. Bloqueio mantido.')
    height = await rpc('getBlockHeight', [{'commitment': 'finalized'}])
    limit = bound['last_valid_block_height']
    if height <= limit:
        return {'retry_allowed': False, 'registered': False, 'finalized_block_height': height, 'last_valid_block_height': limit, 'proof': proof, 'message': 'A rede finalizada ainda não ultrapassou o limite da tentativa. Bloqueio mantido.'}
    valid = await rpc('isBlockhashValid', [bound['blockhash'], {'commitment': 'processed'}])
    if valid['value']:
        raise HTTPException(409, 'RPC ainda considera o blockhash válido. Bloqueio mantido.')
    signature = proof.get('pending_signature')
    if signature:
        statuses = await rpc('getSignatureStatuses', [[signature], {'searchTransactionHistory': True}])
        status = statuses['value'][0]
        if status is not None and status.get('confirmationStatus') != 'finalized':
            raise HTTPException(409, 'Transação conhecida ainda não finalizada. Consulte novamente; não reenvie.')
        if status is not None and status.get('err') is None:
            # Não libera uma assinatura bem-sucedida que o histórico possa omitir.
            result = await check_transaction(proof, signature, commitment='finalized')
            scanned = 1
        else:
            result, scanned = await finalized_registration_scan(proof)
    else:
        result, scanned = await finalized_registration_scan(proof)
    evidence = {'checked_at': int(time.time()), 'network': 'devnet', 'genesis_hash': GENESIS, 'finalized_block_height': height, 'last_valid_block_height': limit, 'blockhash_valid': False, 'scanned': scanned, 'reason': 'existing_verified_registration' if result else 'expired_and_finalized_history_checked'}
    with database() as con:
        con.execute('BEGIN IMMEDIATE')
        current = read_proof(pid, con)
        if canonical(current) != canonical(proof):
            raise HTTPException(409, 'Tentativa mudou durante a recuperação. Nenhum bloqueio foi removido.')
        history = current.setdefault('registration_history', [])
        history.append({'attempt': attempt, 'recovery': frontier, 'signature': signature, 'error': current.get('error'), 'diagnostic': current.get('error_diagnostic'), 'evidence': evidence})
        for key in ('pending_signature', 'registration_attempt', 'recovery', 'error_diagnostic'):
            current.pop(key, None)
        current['error'] = None
        if result:
            current.update(state='registrado', transaction=result)
        else:
            current['state'] = 'confirmado_por_carteira'
        save(con, current)
    return {'retry_allowed': result is None, 'registered': result is not None, 'proof': current, 'evidence': evidence, 'message': 'Registro existente verificado; não reenvie.' if result else 'Tentativa anterior expirada e histórico finalizado conferido. Nova tentativa pode ser preparada sem refazer a declaração.'}
