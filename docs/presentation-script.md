# Apresentação — até 2 minutos

**0:00–0:25**
“Sou estudante de Engenharia de Software. Estou desenvolvendo o DevProof como protótipo para este hackathon. Quem está começando precisa de formas claras de mostrar o trabalho que entregou.”

**0:25–0:55**
“O DevProof consulta um pull request público na API do GitHub, guarda um snapshot da entrega e permite criar uma declaração. Um colaborador confirma essa declaração assinando com sua carteira. Essa confirmação vem do titular da carteira; não equivale à verificação de identidade GitHub.”

**0:55–1:25**
“O conteúdo recebe um hash SHA-256 calculado de uma representação versionada. Usamos o programa Memo já existente na Solana devnet para registrar esse hash. A API verifica a assinatura, impede reutilização do desafio e confere a transação na rede: sucesso, memo correto e signatário esperado.”

**1:25–1:50**
“A interface permite consultar e verificar o comprovante. O protótipo usa React e TypeScript, FastAPI e SQLite local. Não escrevemos a declaração no memo, apenas o hash. Os testes cobrem erros das APIs, assinaturas inválidas, adulteração e transações incompatíveis.”

**1:50–2:00**
“Nos próximos passos quero validar a experiência com usuários, preparar controles para publicação e estudar a vinculação opcional da carteira ao GitHub.”

Antes de apresentar, ajuste somente informações verdadeiras: se o fluxo real da carteira ainda estiver pendente, diga isso explicitamente. Não invente experiência profissional, usuários, parcerias, métricas ou registros reais.
