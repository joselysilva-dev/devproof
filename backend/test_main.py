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
