# DevProof

Protótipo de hackathon: consulta entregas públicas no GitHub, guarda uma declaração, recebe confirmação assinada pelo titular de uma carteira Phantom e registra SHA-256 no programa Memo da Solana **devnet**.

**Situação:** o fluxo técnico local foi validado manualmente pelo usuário: integridade do comprovante, assinatura de carteira e registro na Solana devnet verificado novamente. Os testes automatizados são evidências separadas desse teste manual. Ainda há pendências de apresentação, inscrição e validações adicionais descritas no checklist; isso não representa uma publicação em produção.

## Teste manual com carteira — 10/10/2026

O usuário informou o resultado exibido pelo DevProof: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**

- [Transação do teste na Solana devnet](https://explorer.solana.com/tx/2icba75wX1daENqJYfFA21YxreaRZE9odPJKubAVjChKKWubuw2srSJ2GXaELgHr21mX6fQF95ZsxL4EgntEwmzC?cluster=devnet).
- Comprovante local: `b31eea34-26c2-4574-ad2d-117ecebac682`, encontrado em estado `registrado` mediante leitura do banco em modo somente leitura.
- PR utilizado nesse teste manual: [vitejs/vite#21015](https://github.com/vitejs/vite/pull/21015). **O PR pertence a terceiros e foi usado exclusivamente como teste técnico da integração. Não se alega autoria do PR, participação no projeto Vite ou colaboração real nessa entrega.** A confirmação de carteira nesse contexto é uma evidência do funcionamento técnico do protótipo.

Esse relato manual não é um teste automatizado nem uma nova consulta independente ao RPC nesta etapa de preparação. A consulta técnica anterior a `vitejs/vite#23718` foi outro teste, separado do comprovante manual acima. O banco utilizado no teste manual foi preservado e permanece ignorado pelo Git; ele é necessário para recuperar o conteúdo cujo hash está na rede.

O usuário também confirmou manualmente a persistência após reiniciar a API: integridade, assinatura de carteira e registro na devnet continuam válidos. Essa evidência é separada dos testes automatizados com bancos temporários.

## Executar no Windows / PowerShell

Requisitos: Python 3.11+ e Node.js compatível com o Vite instalado (22.12+ ou 24+), npm e extensão Phantom para as etapas de carteira.

A partir da raiz do repositório:

```powershell
# Somente se o ambiente virtual ainda não existir
python -m venv backend/.venv
# Use o Python do ambiente virtual, sem precisar ativá-lo
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
backend/.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
cd frontend
npm.cmd ci
Copy-Item .env.example .env
npm.cmd run dev -- --host 127.0.0.1
```

Abra http://127.0.0.1:5173. API e documentação: http://127.0.0.1:8000/docs. Não copie os arquivos de exemplo por cima de configurações próprias existentes. O aplicativo funciona com os valores padrão mesmo sem `.env`.

## Fluxo manual com carteira

1. Consulte um PR público real. Confira título, autor, repositório, número, estado, URL e SHA do **head** da entrega (não o SHA do merge).
2. Escreva a declaração e crie o rascunho. A criação consulta novamente o GitHub; os dados podem ter mudado desde a primeira consulta. O conteúdo mostrado no comprovante é o snapshot final.
3. Compartilhe o link `?comprovante=ID` com o colaborador. Em execução local, use outro perfil/navegador no mesmo computador. `localhost` não permite acesso de outra máquina; disponibilizar o protótipo exige configuração de hospedagem, URL da API e CORS.
4. O colaborador conecta Phantom e revisa a declaração antes de clicar em **Assinar confirmação**. A mensagem mostra carteira, URL da entrega, ID, hash, intenção, nonce e expiração. Essa etapa não gasta SOL.
5. Na Phantom, habilite redes de teste e selecione **Solana devnet**. Use https://faucet.solana.com para obter SOL de teste. Nunca forneça seed phrase ou chave privada ao aplicativo.
6. Com a **mesma carteira**, clique em **Registrar hash na devnet**. Revise a transação Memo e aceite a taxa em SOL de teste. Nenhuma transferência de SOL é construída pelo aplicativo.
7. Se a transação ainda não estiver confirmada, use **Verificar transação enviada**. A referência fica no navegador e, após tentativa de validação, no banco. Se você rejeitar a carteira antes do envio, tente registrar novamente.
8. Abra o explorador pelo link do comprovante (com `cluster=devnet`) e clique em **Verificar integridade e registro**. Recarregue a página e reinicie a API para conferir persistência.
9. Para uma transação comprovadamente incompatível, o estado fica `falha`; o botão de nova tentativa libera novo envio. Para RPC indisponível ou transação não encontrada, preserve a referência e aguarde: não reenvie sem conferir primeiro no explorador.

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
