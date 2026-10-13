# Diagnóstico de registro — 11/10/2026

Comprovante: `31ea2c22-13e5-43be-bd3b-0405a65bcb18`.
PR: https://github.com/joselysilva-dev/devproof/pull/1.

## Evidências da investigação

- O banco foi lido em modo somente leitura. O comprovante tinha confirmação assinada, estado `aguardando_registro`, `error: null`, sem `pending_signature` e sem transação registrada.
- O tratamento antigo descartava o erro original e interpretava qualquer objeto com `code` como recusa da carteira. Portanto, a mensagem relatada não permite determinar retrospectivamente a causa exata.
- A consulta pública conferiu o genesis da devnet e encontrou três transações recentes da carteira. Nenhuma foi validada como registro compatível do hash `cbb26c0fcecde158002656ac1d640911ef020e0e4bff20d48899c7728fd85eaf`.
- O saldo público na consulta era 1.49992 SOL de teste (1.499.920.000 lamports). Não há evidência de saldo insuficiente nessa consulta; isso não determina o saldo ou a rede selecionada no momento da falha.
- Não se afirma que nenhum envio ocorreu: a pesquisa é limitada a transações confirmadas e não inclui referências que existam apenas no navegador ou na Phantom. Não foram acessadas credenciais da carteira.

## Correção

O diagnóstico conserva etapa, código e mensagem originais. Somente `4001` significa rejeição explícita do usuário. Erros internos ou de transporte não são apresentados como recusa. A referência de uma transação retornada ou recuperada é consultada antes de outro envio; ela não é apagada por falha de verificação. O backend guarda a assinatura antes da consulta RPC e bloqueia preparação de novo envio enquanto houver assinatura pendente.

Se a operação da Phantom exceder 90 segundos, a tela mostra timeout, sem afirmar ausência de envio. A operação pode terminar depois; sua resposta tardia ainda preserva a assinatura. Uma tentativa inconclusiva sem referência mantém bloqueio local de reenvio.

## Recuperacao da tentativa inconclusiva

Carteira publica: `DcJdi6TM12GxDdao9DBF6B64GMoDnXKdWyjz8tH5Js68`.
A tentativa antiga nao guardou blockhash ou limite de validade. Nao foi possivel consultar diretamente a expiracao desse hash perdido. O historico vazio da Phantom nao foi considerado prova de ausencia.

O fluxo usa transacao legacy com blockhash recente, sem durable nonce. Criamos um marco posterior a tentativa antiga. A consulta publica verificou altura finalizada **497250025**, superior ao limite **497249676** do marco, blockhash do marco invalido e historico finalizado completo com **3 transacoes**, sem registro compativel. A expiracao do marco posterior limita a validade da transacao preparada antes dele neste fluxo. Essa conclusao depende do RPC consultado, nao de uma pesquisa independente em todos os validadores.

As evidencias foram arquivadas e o estado voltou a `confirmado_por_carteira`. Isso permite nova preparacao, mas NAO significa registro concluido. Declaracao, hash e assinatura foram comparados com uma copia anterior e continuam iguais. As duas declaracoes permanecem no banco. O original e a copia `backend/devproof.before-recovery.sqlite3` estao ignorados pelo Git.

Novas preparacoes persistem identificador, carteira, hash, blockhash, slot e ultima altura valida. RPC indisponivel, historico incompleto, transacao pendente, assinatura bem-sucedida incompat?vel ou atualizacao concorrente mantem o bloqueio. A recuperacao exige expiracao e consulta finalizada. Respostas tardias de tentativas recuperadas nao substituem a referencia atual. Recuperar novamente reutiliza a decisao arquivada.

## Resultado manual posterior

O usuário informou que a recuperação e o novo envio passaram: **“Integridade válida. Assinatura de carteira: válida. Registro na devnet: verificado novamente.”**
Transação: [Solana devnet](https://explorer.solana.com/tx/31NMaA79orBcMgYaawXsrzM17m7uSSPtPa8GEuguy3PagVoNDVBB3Bzsn85Y9Lj3nCUPzWbxCSv2Vk5hgHRpwk1Y?cluster=devnet).
É um resultado manual separado dos testes controlados. As instruções abaixo documentam a recuperação realizada; não solicitam outro envio de um comprovante já registrado.

## Procedimento de recuperação pela Phantom

1. Feche solicitacoes antigas pendentes e reinicie API e frontend com os comandos do README.
2. Abra `http://127.0.0.1:5173/?comprovante=31ea2c22-13e5-43be-bd3b-0405a65bcb18`. Preserve a declaracao e sua assinatura.
3. Se tiver assinatura publica de transacao, informe-a antes de novo envio. Conecte a conta indicada acima e selecione devnet na Phantom.
4. Use o botao de recuperar tentativa verificando expiracao. A decisao arquivada deve liberar o bloqueio local. Nao apague banco ou armazenamento.
5. Solicite registro e aprove a nova transacao. O aplicativo prepara outro blockhash e so mostra sucesso depois da verificacao real.
6. Se falhar, guarde categoria, etapa, codigo, mensagem original e assinatura publica. Timeout nao prova ausencia de envio. Nao inicie aprovacoes simultaneas.
7. Depois do registro, verifique integridade e registro. Nunca compartilhe seed phrase, chave privada ou arquivos `.env`.

## Testes

Na atualização do PR #1, **42 testes backend e 7 testes frontend passaram**, além de lint e build. Cobertura: expiração, marco legado, recuperação idempotente, RPC indisponível, rede errada, transação pendente, histórico incompleto, registro encontrado, concorrência, erros originais e respostas tardias. Os testes controlados são separados das consultas públicas e do teste manual pela Phantom. Há um aviso de depreciação TestClient/httpx, sem falha.

A ferramenta de navegador não disponibilizou sessões na investigação. O agente não enviou transações nem acessou credenciais da carteira. O usuário posteriormente concluiu o envio manual descrito acima.

Referencias oficiais consultadas:

- https://docs.phantom.com/solana/errors
- https://docs.phantom.com/solana/sending-a-transaction
- https://solana.com/docs/rpc/http/getlatestblockhash
- https://solana.com/docs/rpc/http/getblockheight
- https://solana.com/docs/rpc/http/isblockhashvalid
- https://solana.com/docs/rpc/http/getsignaturestatuses
- https://solana.com/docs/rpc/http/getsignaturesforaddress
