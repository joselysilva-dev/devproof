import base64, copy, importlib, json
import base58, httpx, pytest
from fastapi.testclient import TestClient
from nacl.signing import SigningKey
from backend import main as m

URL='https://github.com/octocat/Hello-World/pull/1'
DELIVERY={'title':'Entrega real na produção, fixture no teste','author':'octocat','repository':'octocat/Hello-World','number':1,'state':'open','url':URL,'sha':'a'*40}

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'DB',str(tmp_path/'test.sqlite3'))
    return TestClient(m.app)

@pytest.fixture
def proof(client,monkeypatch):
    async def github(url): return DELIVERY.copy()
    monkeypatch.setattr(m,'github',github)
    return client.post('/comprovantes',json={'url':URL,'statement':'Entreguei uma melhoria.'}).json()

def signed(client,proof):
    key=SigningKey.generate()
    wallet=base58.b58encode(bytes(key.verify_key)).decode()
    challenge=client.post(f"/comprovantes/{proof['id']}/desafio",json={'wallet':wallet}).json()
    signature=base64.b64encode(key.sign(challenge['message'].encode()).signature).decode()
    return key,challenge,signature

def confirm(client,proof):
    key,c,s=signed(client,proof)
    r=client.post(f"/comprovantes/{proof['id']}/confirmar",json={'nonce':c['nonce'],'signature':s})
    assert r.status_code==200
    return r.json(),key

def test_invalid_link(client):
    assert client.post('/entregas/consultar',json={'url':'https://evil.test/pull/1'}).status_code==422

@pytest.mark.parametrize('status,expected',[(404,404),(403,429),(429,429),(500,503),(200,200)])
def test_github_status(client,monkeypatch,status,expected):
    payload={'title':'PR','user':{'login':'autor'},'base':{'repo':{'private':False,'full_name':'o/r'}},'number':1,'merged':False,'state':'open','html_url':URL,'head':{'sha':'a'*40}}
    class MockClient:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,*args,**kwargs): return httpx.Response(status,json=payload,request=httpx.Request('GET',URL))
    monkeypatch.setattr(m.httpx,'AsyncClient',MockClient)
    r=client.post('/entregas/consultar',json={'url':URL})
    assert r.status_code==expected
    if status==200: assert r.json()['sha']=='a'*40

def test_github_timeout(client,monkeypatch):
    class MockClient:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,*args,**kwargs): raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(m.httpx,'AsyncClient',MockClient)
    assert client.post('/entregas/consultar',json={'url':URL}).status_code==503

def test_invalid_and_reused_signature(client,proof):
    key,c,s=signed(client,proof)
    path=f"/comprovantes/{proof['id']}/confirmar"
    assert client.post(path,json={'nonce':c['nonce'],'signature':base64.b64encode(b'0'*64).decode()}).status_code==400
    assert client.post(path,json={'nonce':c['nonce'],'signature':s}).status_code==200
    assert client.post(path,json={'nonce':c['nonce'],'signature':s}).status_code==409

def test_expired_challenge(client,proof):
    _,c,s=signed(client,proof)
    with m.database() as con: con.execute('UPDATE challenges SET expires=0')
    assert client.post(f"/comprovantes/{proof['id']}/confirmar",json={'nonce':c['nonce'],'signature':s}).status_code==409

def test_cross_proof(client,proof,monkeypatch):
    _,c,s=signed(client,proof)
    other=client.post('/comprovantes',json={'url':URL,'statement':'Outro comprovante.'}).json()
    assert client.post(f"/comprovantes/{other['id']}/confirmar",json={'nonce':c['nonce'],'signature':s}).status_code==409

def test_tamper(client,proof):
    p,_=confirm(client,proof)
    p['payload']['statement']='Alteração indevida'
    with m.database() as con: m.save(con,p)
    assert client.post(f"/comprovantes/{p['id']}/verificar",json={}).status_code==400

def test_rehashed_tamper(client,proof):
    p,_=confirm(client,proof)
    p['payload']['statement']='Alterado com hash novo'
    p['hash']=m.digest(p['payload'])
    with m.database() as con: m.save(con,p)
    assert client.post(f"/comprovantes/{p['id']}/verificar",json={}).status_code==400

def transaction(p,signature):
    return {'slot':123,'blockTime':1000,'meta':{'err':None},'transaction':{'signatures':[signature],'message':{'accountKeys':[p['confirmation']['wallet'],m.MEMO],'header':{'numRequiredSignatures':1},'instructions':[{'programIdIndex':1,'accounts':[0],'data':base58.b58encode(m.memo_text(p).encode()).decode()}]}}}

@pytest.mark.parametrize('variant',['valid','memo','signer','accounts','failed','network','pending'])
def test_transaction(client,proof,monkeypatch,variant):
    p,_=confirm(client,proof)
    signature=base58.b58encode(b'1'*64).decode()
    tx=transaction(p,signature)
    if variant=='memo': tx['transaction']['message']['instructions'][0]['data']=base58.b58encode(b'other').decode()
    if variant=='signer': tx['transaction']['message']['header']['numRequiredSignatures']=0
    if variant=='accounts': tx['transaction']['message']['instructions'][0]['accounts']=[]
    if variant=='failed': tx['meta']['err']={'InstructionError':[0,'error']}
    async def rpc(method,params=None):
        if method=='getGenesisHash': return 'mainnet' if variant=='network' else m.GENESIS
        return None if variant=='pending' else tx
    monkeypatch.setattr(m,'rpc',rpc)
    r=client.post(f"/comprovantes/{p['id']}/registrar",json={'signature':signature})
    assert r.status_code==(200 if variant=='valid' else 409 if variant=='pending' else 400)
    saved=client.get(f"/comprovantes/{p['id']}").json()
    assert saved['state']==('registrado' if variant=='valid' else 'aguardando_registro' if variant=='pending' else 'falha')
    if variant=='valid':
        assert client.post(f"/comprovantes/{p['id']}/verificar",json={}).json()['onchain']
        assert client.post(f"/comprovantes/{p['id']}/registrar",json={'signature':signature}).status_code==200

def test_canonical():
    assert m.canonical({'z':1,'a':'ação'})=='{"a":"ação","z":1}'
    assert m.digest({'z':1,'a':'ação'})==m.digest({'a':'ação','z':1})

def test_bad_transaction_signature(client,proof):
    p,_=confirm(client,proof)
    assert client.post(f"/comprovantes/{p['id']}/registrar",json={'signature':'0'*64}).status_code==400

def test_draft_cannot_register(client,proof):
    assert client.post(f"/comprovantes/{proof['id']}/registrar",json={'signature':'1'*64}).status_code==409

def test_persistence_new_api(client,proof,monkeypatch):
    path=m.DB
    reloaded=importlib.reload(m)
    monkeypatch.setattr(reloaded,'DB',path)
    fresh=TestClient(reloaded.app)
    assert fresh.get('/comprovantes/'+proof['id']).json()['hash']==proof['hash']

def test_pending_blocks_new_prepare(client,proof,monkeypatch):
    p,_=confirm(client,proof)
    p['pending_signature']=base58.b58encode(b'2'*64).decode()
    with m.database() as con: m.save(con,p)
    async def unexpected(*args): raise AssertionError('Não consultar blockhash nem permitir novo envio')
    monkeypatch.setattr(m,'rpc',unexpected)
    assert client.post(f"/comprovantes/{p['id']}/preparar-registro",json={}).status_code==409

def test_pending_cannot_be_overwritten(client,proof):
    p,_=confirm(client,proof)
    p['pending_signature']=base58.b58encode(b'2'*64).decode()
    with m.database() as con: m.save(con,p)
    r=client.post(f"/comprovantes/{p['id']}/registrar",json={'signature':base58.b58encode(b'3'*64).decode()})
    assert r.status_code==409
    assert m.read_proof(p['id'])['pending_signature']==p['pending_signature']

@pytest.mark.parametrize('failure',['rpc','timeout'])
def test_rpc_diagnostic_and_signature_persisted(client,proof,monkeypatch,failure):
    p,_=confirm(client,proof)
    signature=base58.b58encode(b'2'*64).decode()
    class MockClient:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs):
            assert m.read_proof(p['id'])['pending_signature']==signature
            if failure=='timeout': raise httpx.ReadTimeout('Original read timed out')
            return httpx.Response(200,json={'error':{'code':-32005,'message':'Original node unhealthy'}},request=httpx.Request('POST','https://api.devnet.solana.com'))
    monkeypatch.setattr(m.httpx,'AsyncClient',MockClient)
    response=client.post(f"/comprovantes/{p['id']}/registrar",json={'signature':signature})
    assert response.status_code==(504 if failure=='timeout' else 503)
    d=response.json()['detail']
    assert d['code']==('ReadTimeout' if failure=='timeout' else -32005)
    assert d['original_message']==('Original read timed out' if failure=='timeout' else 'Original node unhealthy')
    stored=m.read_proof(p['id'])
    assert stored['state']=='aguardando_registro'
    assert stored['pending_signature']==signature
    assert stored['error_diagnostic']==d

@pytest.mark.parametrize('found',[False,True])
def test_find_registration_only_reports_verified(client,proof,monkeypatch,found):
    p,_=confirm(client,proof)
    signature=base58.b58encode(b'2'*64).decode()
    async def rpc(method,params=None):
        if method=='getGenesisHash': return m.GENESIS
        if method=='getSignaturesForAddress': return [{'signature':signature,'blockTime':p['confirmation']['confirmed_at']+1,'memo':None}]
        tx=transaction(p,signature)
        if not found: tx['transaction']['message']['instructions'][0]['data']=base58.b58encode(b'unrelated').decode()
        return tx
    monkeypatch.setattr(m,'rpc',rpc)
    r=client.post(f"/comprovantes/{p['id']}/buscar-registro",json={})
    assert r.status_code==200
    assert r.json()['signatures']==([signature] if found else [])
    # Descoberta não altera o comprovante nem declara registro concluído.
    assert m.read_proof(p['id'])['state']=='confirmado_por_carteira'

def recovery_proof(client,proof):
    p,_=confirm(client,proof)
    p['state']='aguardando_registro'
    p['registration_attempt']={'id':'test-attempt','blockhash':'1'*32,'last_valid_block_height':100,'wallet':p['confirmation']['wallet'],'hash':p['hash']}
    with m.database() as con: m.save(con,p)
    return p

def test_prepare_saves_expiry_and_blocks_duplicate(client,proof,monkeypatch):
    p,_=confirm(client,proof)
    async def rpc(method,params=None):
        if method=='getGenesisHash': return m.GENESIS
        assert method=='getLatestBlockhash'
        return {'context':{'slot':321},'value':{'blockhash':'1'*32,'lastValidBlockHeight':100}}
    monkeypatch.setattr(m,'rpc',rpc)
    path=f"/comprovantes/{p['id']}/preparar-registro"
    r=client.post(path,json={})
    assert r.status_code==200
    stored=m.read_proof(p['id'])
    assert stored['registration_attempt']['last_valid_block_height']==100
    assert stored['registration_attempt']['id']==r.json()['attempt_id']
    assert stored['payload']==p['payload'] and stored['confirmation']==p['confirmation']
    assert client.post(path,json={}).status_code==409

@pytest.mark.parametrize('height',[99,100])
def test_recovery_waits_at_expiry_boundary(client,proof,monkeypatch,height):
    p=recovery_proof(client,proof)
    async def rpc(method,params=None):
        if method=='getGenesisHash': return m.GENESIS
        assert method=='getBlockHeight'
        return height
    monkeypatch.setattr(m,'rpc',rpc)
    r=client.post(f"/comprovantes/{p['id']}/recuperar-tentativa",json={})
    assert r.status_code==200 and not r.json()['retry_allowed']
    assert m.read_proof(p['id'])==p

def test_legacy_creates_frontier_without_claiming_expiry(client,proof,monkeypatch):
    p,_=confirm(client,proof)
    p['state']='aguardando_registro'
    with m.database() as con: m.save(con,p)
    async def rpc(method,params=None):
        if method=='getGenesisHash': return m.GENESIS
        assert method=='getLatestBlockhash' and params==[{'commitment':'processed'}]
        return {'context':{'slot':300},'value':{'blockhash':'1'*32,'lastValidBlockHeight':200}}
    monkeypatch.setattr(m,'rpc',rpc)
    r=client.post(f"/comprovantes/{p['id']}/recuperar-tentativa",json={})
    assert not r.json()['retry_allowed']
    stored=m.read_proof(p['id'])
    assert stored['recovery']['last_valid_block_height']==200
    assert stored['state']=='aguardando_registro'
    assert stored['payload']==p['payload'] and stored['confirmation']==p['confirmation']

@pytest.mark.parametrize('variant',['expired','valid_hash','rpc_error','pending_signature','found','missing_tx','race','wrong_network','full_page'])
def test_recovery_conditions(client,proof,monkeypatch,variant):
    p=recovery_proof(client,proof)
    signature=base58.b58encode(b'4'*64).decode()
    if variant=='pending_signature':
        p['pending_signature']=signature
        with m.database() as con: m.save(con,p)
    async def rpc(method,params=None):
        assert method!='sendTransaction'
        if method=='getGenesisHash': return 'mainnet' if variant=='wrong_network' else m.GENESIS
        if method=='getBlockHeight':
            if variant=='rpc_error': raise m.HTTPException(503,'RPC unavailable')
            return 101
        if method=='isBlockhashValid': return {'value':variant=='valid_hash'}
        if method=='getSignatureStatuses': return {'value':[{'err':None,'confirmationStatus':'processed'}]}
        if method=='getSignaturesForAddress':
            assert params[1]['commitment']=='finalized'
            if variant=='race':
                changed=m.read_proof(p['id']);changed['error']='Concurrent update'
                with m.database() as con: m.save(con,changed)
            if variant=='full_page':
                page=0 if 'before' not in params[1] else int(params[1]['before'])//100+1
                return [{'signature':str(page*100+i),'memo':'unrelated memo'} for i in range(100)]
            return [{'signature':signature,'memo':None}] if variant in ('found','missing_tx') else []
        if method=='getTransaction':
            assert params[1]['commitment']=='finalized'
            return None if variant=='missing_tx' else transaction(p,signature)
        raise AssertionError(method)
    monkeypatch.setattr(m,'rpc',rpc)
    r=client.post(f"/comprovantes/{p['id']}/recuperar-tentativa",json={})
    if variant=='expired':
        assert r.status_code==200 and r.json()['retry_allowed']
        stored=m.read_proof(p['id'])
        assert stored['state']=='confirmado_por_carteira'
        assert stored['payload']==p['payload'] and stored['confirmation']==p['confirmation']
        assert stored['registration_history'][0]['attempt']==p['registration_attempt']
        assert stored['registration_history'][0]['evidence']['finalized_block_height']==101
        again=client.post(f"/comprovantes/{p['id']}/recuperar-tentativa",json={})
        assert again.status_code==200 and again.json()['retry_allowed']
        assert m.read_proof(p['id'])==stored
    elif variant=='found':
        assert r.status_code==200 and r.json()['registered'] and not r.json()['retry_allowed']
        assert m.read_proof(p['id'])['transaction']['signature']==signature
    else:
        assert r.status_code in (400,409,503)
        assert m.read_proof(p['id'])['state']=='aguardando_registro'
        assert m.read_proof(p['id'])['registration_attempt']==p['registration_attempt']
