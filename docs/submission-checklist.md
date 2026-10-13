# Checklist de inscrição — DevProof

O projeto foi desenvolvido durante a preparação para um hackathon, com auxílio de IA, mas não foi submetido no prazo. Não houve participação avaliada ou premiação. Este documento conserva o histórico de preparação e agora acompanha os materiais do portfólio. O edital e a plataforma não foram fornecidos; não se afirma que os itens abaixo sejam todos obrigatórios.

## Materiais preparados

- [x] Código frontend React/TypeScript e backend FastAPI/httpx.
- [x] SQLite real, configuração de exemplo sem segredos e dependências registradas.
- [x] README em português com execução no Windows, arquitetura, segurança e limitações.
- [x] Roteiro de demo de até três minutos: `docs/demo-script.md`.
- [x] Roteiro de apresentação de até dois minutos: `docs/presentation-script.md`.
- [x] Imagens `docs/assets/devproof.svg` e `docs/assets/devproof.png` (1200 × 630); PNG inspecionado visualmente.
- [x] Repositório remoto conferido: https://github.com/joselysilva-dev/devproof. Publicação do código autorizada pelo usuário na branch `feat/devproof-mvp`, com pull request para `main`, sem merge ou envio da inscrição.

## Evidências técnicas desta execução — 10/10/2026

- [x] Backend: **23 testes passaram**. Há um aviso de depreciação do TestClient/Starlette por usar httpx, sem falha de teste; a integração HTTP de produção segue usando httpx conforme solicitado. Casos externos de falha são respostas controladas; não representam integrações reais concluídas.
- [x] Frontend: `npm.cmd run build` e `npm.cmd run lint` passaram.
- [x] Auditoria npm após ajuste de dependências: **zero vulnerabilidades reportadas**. Override de `jayson` 5 mantém a API legacy de web3.js e evita dependências transitivas vulneráveis; serialização Memo testada após a alteração.
- [x] Consulta **real** ao GitHub: HTTP 200 para https://github.com/vitejs/vite/pull/23718, com título, autor, repositório e SHA retornados pela API. Caso inexistente também retornou HTTP 404 real.
- [x] RPC **real**: genesis hash conferido e correspondente à Solana devnet.
- [x] Transação Memo legacy construída, serializada e decodificada localmente: conteúdo e conta signatária conferidos. **Nenhuma transação foi enviada nesse teste.**
- [x] Teste com API em processo HTTP real: declaração criada com consulta GitHub real em banco temporário; processo encerrado e reiniciado; ID/hash preservados e integridade válida. O resultado era rascunho, sem assinatura e sem registro.
- [x] `.gitignore` verificado para `.venv`, `node_modules`, builds, bancos e `.env`; exemplos de configuração não são ignorados.
- [ ] Teste visual/interativo da interface no navegador: a ferramenta informou nenhuma sessão disponível e `Browser is not available: iab`. Build/lint não substituem teste de navegação.

## Teste manual informado pelo usuário — 10/10/2026

- [x] Resultado manual relatado: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**
- [x] Transação real informada: [explorador Solana devnet](https://explorer.solana.com/tx/2icba75wX1daENqJYfFA21YxreaRZE9odPJKubAVjChKKWubuw2srSJ2GXaELgHr21mX6fQF95ZsxL4EgntEwmzC?cluster=devnet).
- [x] Comprovante `b31eea34-26c2-4574-ad2d-117ecebac682` encontrado no SQLite local com estado `registrado` e a mesma assinatura de transação, mediante leitura somente leitura.
- [x] PR do teste manual identificado no comprovante: [vitejs/vite#21015](https://github.com/vitejs/vite/pull/21015). **PR de terceiros, usado somente como teste técnico; sem alegação de autoria, participação no Vite ou colaboração real nessa entrega.** É diferente do PR #23718 consultado no teste técnico anterior.
- [x] Banco do teste preservado; `.env`, ambientes virtuais, dependências, builds e bancos locais não fazem parte dos arquivos para commit. Exemplos `.env.example` podem ser versionados.
- [x] Persistência do registro real confirmada manualmente pelo usuário após reiniciar a API: integridade, assinatura de carteira e registro na devnet continuam válidos. Essa confirmação manual é distinta dos testes automatizados de persistência com bancos temporários.

O relato manual valida o fluxo técnico com carteira e registro devnet nesse caso. Ele é separado dos testes automatizados com fixtures. Nesta preparação, a evidência local foi conferida em modo somente leitura; não se afirma uma nova verificação independente no RPC ou uma inspeção visual do explorador.

## Teste manual do DevProof PR #1 — 11/10/2026

- [x] Usuário informou após a recuperação: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**
- [x] Comprovante: `31ea2c22-13e5-43be-bd3b-0405a65bcb18`; entrega consultada: [DevProof PR #1](https://github.com/joselysilva-dev/devproof/pull/1).
- [x] [Transação informada na Solana devnet](https://explorer.solana.com/tx/31NMaA79orBcMgYaawXsrzM17m7uSSPtPa8GEuguy3PagVoNDVBB3Bzsn85Y9Lj3nCUPzWbxCSv2Vk5hgHRpwk1Y?cluster=devnet).
- [x] Teste manual distinto dos testes automatizados e do exemplo anterior com PR de terceiros; sem inferir identidade GitHub da carteira.
- [x] Leitura local sem alteração do banco: estado `registrado`, integridade e assinatura da declaração válidas, transação igual à informada. Isso não é uma nova consulta ao RPC.
- [x] Persistência deste comprovante após reiniciar a API confirmada manualmente pela autora em **13/10/2026**: integridade, assinatura de carteira e registro devnet continuam válidos. Evidência distinta dos testes automatizados; não é uma nova consulta independente ao RPC pelo agente.

## Validações adicionais ainda pendentes

- [ ] Ensaiar abertura do link em outro perfil/navegador com outra pessoa (o relato não confirmou esse cenário).
- [ ] Testar rejeição da solicitação na carteira e nova tentativa sem duplicação na interface.
- [x] Reiniciar API e confirmar persistência desse registro real: usuário confirmou integridade, assinatura e registro devnet válidos após a reinicialização.
- [ ] Validar layout em celular, navegação por teclado e estados de erro no navegador.

O fluxo técnico local com carteira e Solana devnet foi validado manualmente no caso informado. As validações adicionais e os materiais de inscrição continuam pendentes. Uma carteira não é identidade GitHub verificada nem prova autoria do PR.

## Verificação repetida para o portfólio — 13/10/2026

- [x] `backend/.venv/Scripts/python.exe -m pytest backend -q`: **42 passaram**, com um aviso de depreciação do TestClient por usar httpx. Inclui expiração, recuperação idempotente, histórico incompleto e concorrência.
- [x] `npm.cmd run test`: **7 passaram**, cobrindo diagnóstico, referência pendente, falha de verificação e resposta tardia.
- [x] `npm.cmd run lint`: passou, sem erros.
- [x] `npm.cmd run build`: passou, gerando o build local ignorado pelo Git.
- [x] Nenhum `.env` real, ambiente virtual, `node_modules` ou banco local encontrado entre arquivos rastreados pelo Git. Regras de ignore conferidas; arquivos `.env.example` ficam disponíveis para commit.

## Arquivos revisados para publicação

### Revisão final do PR #1 — 13/10/2026

- [x] Correção na API: assinaturas de transação com Base58 inválido ou tamanho decodificado diferente de 64 bytes são rejeitadas antes de persistir uma referência pendente. Dois testes de regressão confirmam que o comprovante permanece intacto e o RPC não é chamado.
- [x] Verificação final: **44 testes backend e 7 frontend passaram**, lint e build passaram; `pip check` não encontrou dependências incompatíveis. Permanece o aviso de depreciação TestClient/httpx.
- [x] Vídeo final: MP4 H.264/AAC, 848 × 436, duração de 52,57 segundos; decodificação integral sem erros e inspeção de quadros da demonstração, incluindo a mensagem de verificação válida. Não representa um novo teste com carteira nesta revisão.
- [x] Todos os destinos locais do README existem. PRs GitHub, faucet e documentação externa responderam HTTP 200. Os dois links do explorador Solana preservam `cluster=devnet`, mas retornaram HTTP 429 nesta consulta; acesso visual e conteúdo das transações não foram confirmados independentemente.
- [x] Repositório público, sem arquivo de licença; README registra a decisão da autora de não conceder licença de reutilização. Instruções técnicas de execução preservadas.
- [x] PR aberto, sem conflitos com `main`, sem reviews ou threads pendentes e sem verificações de CI configuradas no commit consultado. Validação realizada localmente; nenhum merge autorizado nesta etapa.

Não foi identificado bloqueio técnico para incorporar o protótipo local à `main`. A conferência dos links do explorador foi limitada por HTTP 429. Celular, teclado e outro navegador continuam como validações manuais pendentes; os controles exigidos para hospedagem pública também permanecem fora do escopo deste MVP local.

O MVP já está no [PR #1](https://github.com/joselysilva-dev/devproof/pull/1), branch `feat/devproof-mvp`. Esta atualização inclui README, checklist, diagnóstico, backend e seus testes, frontend e seus testes e dependências registradas. A lista abaixo descreve os materiais do MVP original:

- Modificados: `.gitignore`, `README.md`.
- Backend novo: `backend/.env.example`, `backend/main.py`, `backend/requirements.txt`, `backend/test_main.py`.
- Documentação nova: `docs/demo-script.md`, `docs/presentation-script.md`, `docs/submission-checklist.md`.
- Imagens e gerador novos: `docs/assets/devproof.svg`, `docs/assets/devproof.png`, `docs/assets/render-image.ps1`.
- Frontend novo: `frontend/.env.example`, `frontend/.gitignore`, `frontend/README.md`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/eslint.config.js`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`.
- Código e recursos novos: `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/public/favicon.svg`, `frontend/public/icons.svg`, `frontend/src/assets/hero.png`, `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`. Recursos do scaffold existente foram preservados.

Não incluir no commit o banco `backend/devproof.sqlite3` nem seus arquivos auxiliares, `.env` reais, `.venv`, `node_modules`, `dist` ou caches. O banco manual continua no computador.

## Pendências atuais do portfólio

- [x] Vídeo final disponível em [docs/media/devproof-demo.mp4](media/devproof-demo.mp4), vinculado no README.
- [x] Decisão da autora: manter o repositório público para portfólio, sem adicionar licença de reutilização.
- [ ] Validar celular, teclado e outro navegador.
- [ ] Hospedar demo, se desejado, após preparar controles de acesso e abuso.
- [x] Bancos, credenciais e gravações brutas ficam fora do Git; somente o vídeo final de demonstração está versionado.

## Histórico de preparação da inscrição (prazo encerrado)

- [ ] Nome/categoria do hackathon, elegibilidade, prazo/fuso e regras sobre uso de IA.
- [ ] Nome de equipe, participantes, contatos e consentimentos solicitados.
- [ ] Título, descrição curta, problema, solução e tecnologias no formato exigido.
- [ ] Licença do projeto e exigência de código público; revisar conteúdo antes de eventual push autorizado.
- [ ] Vídeo real de demonstração, duração/formato e link de acesso exigidos.
- [ ] Dimensões/tamanho/formato de imagem exigidos; usar os arquivos preparados ou adaptar.
- [ ] URL hospedada, se exigida. O projeto está local; não houve deploy. Preparar controles de acesso e abuso antes de exposição pública.
- [ ] Conferir links finais de repositório e demo exigidos pelo edital; o link do explorador do teste manual já está disponível acima.
- [ ] Revisão de segredos, dados pessoais, alegações e limitações.
- [ ] Envio da inscrição feito pelo usuário. Nenhuma inscrição foi enviada nesta sessão.
