# DevProof

O DevProof consulta um pull request público do GitHub, permite declarar uma entrega e recebe uma confirmação assinada por carteira. O hash do comprovante é registrado na Solana **devnet** e pode ser verificado novamente pelo aplicativo.

Projeto de portfólio de uma estudante de Engenharia de Software, desenvolvido durante a preparação para um hackathon, com auxílio de IA. **Não foi submetido no prazo** e não é apresentado como participante avaliado ou premiado. É um protótipo local, sem publicação em produção.

## Demonstração

[Assista ao vídeo final do DevProof](docs/media/devproof-demo.mp4). O vídeo mostra um comprovante previamente registrado e sua verificação na Solana devnet. Há também um [roteiro de demo de até 3 minutos](docs/demo-script.md) e uma [imagem do projeto](docs/assets/devproof.png).

O fluxo com carteira foi testado manualmente: consulta do PR, assinatura da declaração, registro do hash e nova verificação na devnet. A persistência do comprovante do PR #1 após reiniciar a API foi confirmada manualmente pela autora em 13/10/2026. As evidências e transações estão documentadas abaixo, separadas dos testes automatizados.

## Tecnologias

- React, TypeScript e Vite na interface.
- Python, FastAPI e httpx na API.
- SQLite para persistência local; este MVP não usa PostgreSQL.
- Phantom, Ed25519, SHA-256 e programa Memo da Solana devnet.

## Instalação e execução

Requisitos: Git, Python 3.11+, Node.js 24+ (também usado pelos testes TypeScript), npm e extensão Phantom para as etapas de carteira.

```powershell
git clone --branch feat/devproof-mvp https://github.com/joselysilva-dev/devproof.git
cd devproof
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal, dentro da pasta `devproof`:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1
```

Abra http://127.0.0.1:5173; a documentação da API está em http://127.0.0.1:8000/docs. Os valores padrão permitem executar sem `.env`. Para personalizar, copie os exemplos somente se os arquivos de destino ainda não existirem:

```powershell
# Executar na raiz do projeto
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (!(Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
```

**Cada pessoa deve usar sua própria carteira na Solana devnet**, com SOL de teste. Quem confirma a declaração usa a mesma carteira para registrar o hash. Nunca forneça seed phrase ou chave privada ao aplicativo. O clone começa com um banco novo: os comprovantes locais da autora não são distribuídos, e o hash no explorador não substitui o conteúdo guardado no banco.

## Limitações e testes

A carteira confirma uma declaração, não identidade GitHub ou autoria do código. O protótipo usa somente devnet, depende das APIs do GitHub/Solana e ainda não possui os controles necessários para exposição pública. O banco guarda o conteúdo; a blockchain guarda apenas o hash. Não há demo hospedada.

```powershell
# Na raiz
backend/.venv/Scripts/python.exe -m pytest backend -q
cd frontend
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

Última validação: **42 testes backend e 7 frontend**, lint e build passaram. Os testes usam bancos temporários e respostas externas controladas; os testes manuais com Phantom são evidências separadas. Há um aviso de depreciação do TestClient/httpx. Layout móvel, teclado e uso em outro navegador ainda precisam de validação manual.

## Licença

Não há arquivo de licença nem licença própria declarada no projeto. Nenhuma licença foi adicionada ou alterada nesta revisão. A escolha permanece pendente; as licenças das dependências são separadas da licença deste código.

## Evidências dos testes manuais

### Teste manual com carteira — 10/10/2026

O usuário informou o resultado exibido pelo DevProof: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**

- [Transação do teste na Solana devnet](https://explorer.solana.com/tx/2icba75wX1daENqJYfFA21YxreaRZE9odPJKubAVjChKKWubuw2srSJ2GXaELgHr21mX6fQF95ZsxL4EgntEwmzC?cluster=devnet).
- Comprovante local: `b31eea34-26c2-4574-ad2d-117ecebac682`, encontrado em estado `registrado` mediante leitura do banco em modo somente leitura.
- PR utilizado nesse teste manual: [vitejs/vite#21015](https://github.com/vitejs/vite/pull/21015). **O PR pertence a terceiros e foi usado exclusivamente como teste técnico da integração. Não se alega autoria do PR, participação no projeto Vite ou colaboração real nessa entrega.** A confirmação de carteira nesse contexto é uma evidência do funcionamento técnico do protótipo.

Esse relato manual não é um teste automatizado nem uma nova consulta independente ao RPC nesta etapa de preparação. A consulta técnica anterior a `vitejs/vite#23718` foi outro teste, separado do comprovante manual acima. O banco utilizado no teste manual foi preservado e permanece ignorado pelo Git; ele é necessário para recuperar o conteúdo cujo hash está na rede.

O usuário também confirmou manualmente a persistência após reiniciar a API: integridade, assinatura de carteira e registro na devnet continuam válidos. Essa evidência é separada dos testes automatizados com bancos temporários.

### Teste manual do DevProof PR #1 — 11/10/2026

Após a recuperação da tentativa inconclusiva, o usuário informou: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**

- Comprovante: `31ea2c22-13e5-43be-bd3b-0405a65bcb18`.
- Entrega consultada: [DevProof PR #1](https://github.com/joselysilva-dev/devproof/pull/1).
- [Transação informada na devnet](https://explorer.solana.com/tx/31NMaA79orBcMgYaawXsrzM17m7uSSPtPa8GEuguy3PagVoNDVBB3Bzsn85Y9Lj3nCUPzWbxCSv2Vk5hgHRpwk1Y?cluster=devnet).

Esse resultado manual é separado dos testes automatizados com fixtures e do teste anterior com PR de terceiros. A carteira confirma a declaração como titular; não representa identidade GitHub verificada. Em **13/10/2026**, a autora confirmou manualmente a persistência deste comprovante após reiniciar a API: integridade, assinatura e registro na devnet continuam válidos. Não se alega nova consulta independente ao RPC nesta revisão. O banco e a cópia anterior à recuperação permanecem locais e fora do commit.

## Fluxo manual com carteira

1. Consulte um PR público real. Confira título, autor, repositório, número, estado, URL e SHA do **head** da entrega (não o SHA do merge).
2. Escreva a declaração e crie o rascunho. A criação consulta novamente o GitHub; os dados podem ter mudado desde a primeira consulta. O conteúdo mostrado no comprovante é o snapshot final.
3. Compartilhe o link `?comprovante=ID` com o colaborador. Em execução local, use outro perfil/navegador no mesmo computador. `localhost` não permite acesso de outra máquina; disponibilizar o protótipo exige configuração de hospedagem, URL da API e CORS.
4. O colaborador conecta Phantom e revisa a declaração antes de clicar em **Assinar confirmação**. A mensagem mostra carteira, URL da entrega, ID, hash, intenção, nonce e expiração. Essa etapa não gasta SOL.
5. Na Phantom, habilite redes de teste e selecione **Solana devnet**. Use https://faucet.solana.com para obter SOL de teste. Nunca forneça seed phrase ou chave privada ao aplicativo.
6. Com a **mesma carteira**, clique em **Registrar hash na devnet**. Revise a transação Memo e aceite a taxa em SOL de teste. Nenhuma transferência de SOL é construída pelo aplicativo.
7. Se a transação ainda não estiver confirmada, use **Verificar transação enviada**. A referência fica no navegador e, após tentativa de validação, no banco. Se rejeitar a solicitação antes do envio, use a recuperação com verificação de expiração antes de preparar outra tentativa.
8. Abra o explorador pelo link do comprovante (com `cluster=devnet`) e clique em **Verificar integridade e registro**. Recarregue a página e reinicie a API para conferir persistência.
9. Para uma transação incompatível, o estado fica `falha`, mas a assinatura é preservada. Uma assinatura pendente bloqueia novo envio na interface e na API. Para RPC indisponível ou transação não encontrada, consulte a mesma assinatura novamente; não reenvie sem resolver a tentativa anterior. O botão de apagar a referência e reenviar foi removido.

## Diagnóstico e recuperação de registro

Erros distinguem recusa explícita da Phantom (`4001`), falha de conexão/assinatura, falha de envio, timeout e falha de verificação. O painel **Diagnóstico técnico do erro** preserva etapa, categoria, código e mensagem originais, status HTTP quando disponível e assinatura pública recuperada. O aplicativo não interpreta todo erro com `code` como recusa do usuário.

A referência retornada pela Phantom é guardada antes da verificação. Se o erro trouxer assinatura (ou a transação tiver sido assinada), a interface tenta consultar o registro antes de permitir outro envio. Erros de atualização da tela não substituem o erro original. O timeout da solicitação à carteira é de 90 segundos e não cancela uma operação da Phantom: uma resposta tardia ainda guarda a assinatura. Não abra outra solicitação enquanto a carteira tiver uma aprovação pendente.

Na API, a assinatura é persistida antes da consulta RPC. Erros RPC preservam código e mensagem; timeout responde HTTP 504 e mantém `aguardando_registro`. **Buscar registro na devnet** procura até 100 transações confirmadas da carteira e só retorna assinaturas depois da validação real de rede, memo e signatário. A busca não marca sucesso nem considera a ausência de resultados prova de ausência de envio. Também é possível colar a assinatura pública do histórico da Phantom em **Consultar esta assinatura sem reenviar**.

Uma tentativa inconclusiva permanece bloqueada até consultar sua referência ou usar **Recuperar tentativa verificando expiração**. Novas preparações guardam blockhash e última altura válida no backend. A recuperação exige altura finalizada acima do limite, blockhash inválido e consulta completa do histórico finalizado da carteira. RPC indisponível, histórico incompleto ou transação pendente mantêm o bloqueio. Tentativas antigas sem blockhash usam um marco posterior e aguardam sua expiração; o hash perdido não é inventado. Isso depende do RPC e do fluxo com blockhash recente, sem durable nonce. Não limpe o armazenamento nem apague o banco para contornar o bloqueio. Evidências e próximo teste: [docs/registration-diagnostics.md](docs/registration-diagnostics.md).

## Arquitetura e persistência

- React + TypeScript + Vite, visual escuro com destaque verde, formulários rotulados, foco visível, feedback acessível e bloqueio de ações duplicadas no navegador.
- FastAPI + httpx: consulta a API oficial do GitHub e RPC Solana no servidor. Token GitHub opcional apenas em `backend/.env`; nunca no frontend.
- **SQLite real**, arquivo padrão `backend/devproof.sqlite3`. Não há PostgreSQL configurado ou utilizado neste MVP. `DEVPROOF_DB` pode indicar outro caminho; caminhos relativos são resolvidos a partir do terminal. Faça cópia segura do arquivo para backup. A API guarda payload, hash, estado, assinatura, mensagem, desafio, expiração e metadados da transação.
- Transações SQLite com bloqueio de escrita tornam consumo de nonce e confirmação atômicos. A confirmação invalida os outros desafios do mesmo comprovante.
- Não existe contrato próprio: o programa Memo já disponível recebe `devproof:v1:<hash hexadecimal>` e a conta do confirmador como signatário requerido.

Estados: `rascunho` → `confirmado_por_carteira` → `aguardando_registro` → `registrado`. Rejeição de transação incompatível produz `falha`; falhas temporárias de RPC/pendência mantêm `aguardando_registro`. Registro concluído não pode ser substituído.

## Serialização e verificação

Versão `devproof/1`: objeto com `version`, `id`, `created_at` (segundos Unix inteiros), `delivery` (snapshot GitHub) e `statement`. A representação canônica é JSON com chaves ordenadas recursivamente, separadores `,` e `:` sem espaços, Unicode preservado (`ensure_ascii=False`), codificação UTF-8 sem BOM. Não usa números de ponto flutuante nem normaliza Unicode; a declaração é aparada nas extremidades antes da criação. SHA-256 é calculado sobre esses bytes. Esta é uma convenção própria versionada, não uma alegação de conformidade com RFC 8785.

A confirmação Ed25519 assina uma mensagem JSON canônica que vincula domínio DevProof, versão, devnet, intenção `confirm_delivery`, carteira, ID, URL da entrega, hash, nonce aleatório de 256 bits e expiração de dez minutos. A API valida a chave pública e os bytes da assinatura, prazo e consumo único do desafio. O hash corresponde ao payload da entrega; a mensagem e a assinatura ficam armazenadas separadamente.

A verificação recalcula o hash, valida a assinatura de carteira e confere a vinculação da mensagem ao comprovante. Para um registro, consulta novamente `getGenesisHash` e `getTransaction` com commitment `confirmed`; exige genesis de devnet, sucesso da execução, memo exato, programa correto, carteira entre signatários da transação **e entre contas da instrução Memo**, além da assinatura da transação consultada. Uma string enviada pelo navegador nunca basta para marcar registro como concluído. O servidor confia no RPC configurado; use um provedor confiável.

O memo contém somente prefixo/versionamento e hash. Nenhum título, declaração, segredo ou dado pessoal é escrito pelo aplicativo no memo. O endereço público do signatário aparece naturalmente na transação Solana. A API local retorna dados do comprovante a quem possui seu ID: não coloque informações sensíveis na declaração.

## Limites honestos

A carteira confirma uma afirmação; não prova vínculo com uma conta GitHub, relação de trabalho, autoria efetiva do código, qualidade, aceite comercial ou participação como colaborador. Qualquer titular de carteira com acesso ao rascunho pode confirmá-lo. O MVP não possui convite restrito, login, moderação, rate limit próprio ou proteção completa contra abuso; mantenha a API local até preparar esses controles para publicação.

O snapshot não acompanha futuras mudanças no PR. O banco continua necessário para recuperar o conteúdo: a blockchain armazena somente o hash. Devnet é rede de teste, sujeita a reset e sem garantia permanente. Commitment `confirmed` oferece confirmação, não finalização absoluta. Sem RPC, a verificação on-chain fica indisponível e não simula sucesso. Há suporte direto à extensão **Phantom** com `signMessage` e transação legacy; não se alega compatibilidade universal ou com todos os dispositivos móveis.

## Testes

```powershell
backend/.venv/Scripts/python.exe -m pytest backend -q
cd frontend
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

A suíte usa fixtures claramente identificadas e respostas externas controladas para reproduzir: URL inválida, 404, consulta válida, 403/429, 500/timeout, assinatura inválida/reutilizada/expirada, desafio de outro comprovante, adulteração com e sem novo hash, memo incorreto, signatário/contas ausentes, execução falha, rede errada, pendência, registro idempotente e persistência ao carregar nova instância da API. **Fixtures não são sucesso real de integração.** Resultados desta execução e pendências: [docs/submission-checklist.md](docs/submission-checklist.md).

Na preparação da entrega, os testes do backend, lint e build são executados novamente. Os testes do backend usam bancos temporários isolados, sem apagar ou alterar o banco do comprovante manual.

## Materiais de apresentação

- [Roteiro de demonstração (até 3 min)](docs/demo-script.md)
- [Roteiro de apresentação (até 2 min)](docs/presentation-script.md)
- [Checklist](docs/submission-checklist.md)
- [Imagem SVG](docs/assets/devproof.svg) e PNG, quando gerado, na mesma pasta.

## Documentação oficial consultada

- GitHub Pull Requests: https://docs.github.com/en/rest/pulls/pulls
- Solana getTransaction: https://solana.com/docs/rpc/http/gettransaction
- Solana getGenesisHash: https://solana.com/docs/rpc/http/getgenesishash
- Programa Memo: https://www.solana-program.com/docs/memo
- Phantom signMessage: https://docs.phantom.com/solana/signing-a-message
- Phantom transação legacy: https://docs.phantom.com/solana/sending-a-transaction
