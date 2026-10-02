# Backlog do Flow Hub

Sistema para vender automações n8n: o cliente descreve o problema, um agente acha o melhor fluxo pronto (ou entrevista para montar um), o pedido vira features, sai o orçamento e a cobrança, e a construção segue no Claude Code.

> Revisão de produto em 2026-10-01: estados auditados contra o código, dependências corrigidas, histórias novas da R1 e respostas sugeridas às dúvidas. Análise completa (riscos, preço, RICE) em `docs/REVISAO-PRODUTO.md`.

## Visão ponta a ponta

```
Cliente descreve o problema
        |
        v
[Agente consultor] --acha--> fluxo do acervo (1.433 indexados)
        |  --entrevista (até 5 perguntas)--> briefing
        v
[Quebra em features] critérios de aceite + horas
        |
        v
[Orçamento] setup + mensalidade + ROI do cliente
        |
        v
[Proposta PDF + contrato] --> [aceite registrado] --> [Pagamento da entrada 50%]
        |                                             (R1: Pix manual; R2: link)
        v
[Projeto no kanban] --> Claude Code adapta o fluxo --> scanner + checklist de entrega
        |
        v
[Mensalidade] alerta de falha + horas reais + relatório mensal
```

## Quem usa
- **Operador (Thiago):** recebe pedidos, aprova escopo e preço, constrói e entrega.
- **Cliente final:** descreve o problema, aprova a proposta, paga, acompanha.
- **Parceiro (futuro):** revende ou opera projetos usando o mesmo catálogo.

## Legenda de estado
- **Feito:** existe no repositório e atende os critérios de aceite.
- **Parcial:** existe uma parte (indicada); não declarar pronto.
- **A fazer:** não existe.

## Estado atual (Feito, verificado no repositório)
| ID | Entrega | Evidência |
|---|---|---|
| FND-01 | Indexador do acervo: 1.433 fluxos únicos, sem duplicatas exatas, em SQLite | `flowhub/indexer.py`; coluna `source` guarda a pasta `src1..src9` |
| FND-02 | Busca full-text com filtros (integração, IA, complexidade) | `flowhub/search.py` (FTS5, bm25) |
| FND-03 | Calculadora de orçamento | `flowhub/quote.py`. Atenção: a âncora (R$ 3.500 + R$ 497) é um **exemplo didático** da Flowgrammers, não uma venda; com 20 h e complexidade média a fórmula dá setup R$ 3.750, não R$ 3.500 (ver ORC-12) |
| FND-04 | Agente `flow-consultant` (modo busca e modo entrevista) no Claude Code | `.claude/agents/flow-consultant.md` |
| FND-05 | Guia dos 8 repositórios de skills e agentes | `docs/guia-repositorios.html` |
| FND-06 | Painel web local em `127.0.0.1:3100` com abas Consultor (chat), Catálogo, Pedidos e Orçamento; só aceita `Host` local | `server/server.js`, `public/` |
| FND-07 | 6 agentes de pipeline (`flow-consultant`, `analista-de-pedido`, `quebra-de-features`, `orcamentista`, `construtor-n8n`, `qa-fluxos`) e 5 skills | `.claude/agents/`, `.claude/skills/` |
| FND-08 | Cofre `vault/` com modelos de pedido e cliente, parâmetros de preço, aprendizados e contexto ativo | `vault/` |
| FND-09 | Testes do painel e dos scripts: 65 em Node e 41 em Python, 106 no total, incluindo regressões das falhas achadas nas auditorias de segurança e de código | `tests/*.test.js`, `tests/test_*.py`; rode `npm run test:all` |
| FND-10 | Calculadora corrigida (ORC-12): piso vence o teto de ROI, desconto só nas horas de adaptação, economia calculada pelo script, payback líquido da mensalidade, parâmetros em arquivo versionado | `flowhub/quote.py`, `flowhub/parametros.json`, `tests/test_quote.py` (12) |
| FND-11 | Criar pedido pela tela (INT-06): formulário, validação que aponta o campo, número livre sem colisão, gerado a partir do modelo | `server/lib/pedido-novo.js`, `public/novo-pedido.js`, `tests/pedido-novo.test.js` |
| FND-12 | Travas do kanban (ORC-13, ENT-01, parte de ENT-02): Aprovado exige aceite completo, Em construção exige entrada paga com comprovante, Entregue exige checklist inteiro; voltar é livre; histórico no pedido; preço congelado depois do aceite | `server/lib/transicoes.js`, `server/lib/pedidos.js`, `public/detalhes.js`, `tests/secoes.test.js`, `tests/pedidos-regras.test.js` |
| FND-13 | Scanner de credenciais (CAT-03): chaves, tokens, e-mails, IDs de credencial e de webhook, URLs; gravidade alta ou média; saída sempre mascarada; o catálogo mostra “segredo real” (31 dos 1.433 fluxos) | `flowhub/scan.py`, `flowhub/indexer.py`, `tests/test_scan.py` (9) |
| FND-14 | Proposta comercial em PDF de 1 página (ORC-02), com identidade própria, versão, validade, ROI só quando há economia e cópia versionada em `vault/Pedidos/anexos` | `flowhub/proposta.py`, `tests/test_proposta.py` (11) |
| FND-15 | Horas reais por pedido (parte de ENT-05): registro na tabela e soma no cabeçalho | `server/lib/pedidos.js` (`addHoras`), `public/detalhes.js` |
| FND-18 | Pacote de desenvolvimento por pedido (parte de ENT-02 e ENT-08): a partir da tabela de Features do pedido gera épicos, features, histórias e tasks para os agentes (id, agente, depende de, pronto quando, prompt), com a explicação nó a nó dos fluxos de referência, 3 fluxos-modelo anotados (captação de leads, lembrete diário por data ou km, alerta de falha) e modelos de entrega (LEIA-ME, roteiro do vídeo). Botão em Detalhes e rota `POST /api/pedidos/:id/pacote`. Limites: os modelos foram validados na estrutura (JSON, conexões, scanner), não executados num n8n real; a explicação é por regra, sem IA; o formato de mensagem da Meta deve ser conferido na versão em uso; as tasks seguem um esqueleto padrão, não leem o critério de aceite para criar tasks sob medida | `flowhub/explicar.py`, `flowhub/pacote.py`, `templates/`, `server/server.js`, `public/detalhes.js`, `tests/test_explicar.py` (10), `tests/test_pacote.py` (15) |
| FND-17 | Perfil de cada fluxo no catálogo (partes de CAT-04 e CAT-07): “o que tem”, “por que usar” e “o que falta criar” (cliente fornece, limpar, criar, adaptar) com esforço de adaptação, gerados dos dados do JSON, sem IA, e mostrados nos cartões. Limites: o “por que usar” vem das notas do autor e da categoria, não de uma descrição revisada à mão; o esforço é heurístico; não há custo mensal estimado de APIs nem pré-requisitos de conta paga por fluxo | `flowhub/perfil.py`, `public/perfil.js`, `tests/test_perfil.py` (17) |
| FND-16 | Modelos de pedido e cliente com os dados de proposta e contrato e a regra de dados mínimos (INT-07, PLT-10) | `vault/Pedidos/_modelo-pedido.md`, `vault/Clientes/_modelo-cliente.md` |

Fatos medidos e não resolvidos: o chat custa cerca de US$ 0,30 por mensagem com o modelo `sonnet` fixo (cerca de US$ 2,7 sem fixar) e leva 15 a 35 s. Das 71 histórias originais, as acima fecham ou avançam: ORC-12, INT-06, INT-07, ORC-02, ORC-13, ENT-01, CAT-03 (feitas); ENT-02, ENT-05, PLT-10, ENT-09 (parciais, ver cada linha). Ainda faltam, entre as P0 da R1: CAT-01 (licença por pasta, depende da dúvida 1), ENT-08 (alerta de falha no n8n do cliente), PLT-09 (backup) e o ensaio ponta a ponta.

## Releases

| Release | Objetivo | Como o Thiago opera |
|---|---|---|
| **R1 Primeira venda** | Receber a entrada e entregar o primeiro cliente pagante com segurança (licença, credenciais, aceite, alerta de falha) | Claude Code + painel local que já existe; telas novas só quando forem mais baratas que o passo manual; pagamento por Pix manual |
| **R2 Funil automatizado** | Cliente faz o pedido sozinho e paga online | Chat do agente aberto ao cliente (com limite de custo), pagamento por link, banco em nuvem |
| **R3 Escala e vitrine** | Vender sem você no meio e atrair clientes | Vitrine pública, parceiros, monitoramento |

Correção: a R1 dizia "sem criar telas", mas o painel local já existe. A regra passa a ser "sem telas para o cliente na R1". A R1 termina quando a **entrada do primeiro cliente foi paga e a primeira entrega foi aceita**.

Prioridade: **P0** obrigatório na release, **P1** deveria entrar, **P2** desejável, **P3** depois. Pontos em escala 1, 2, 3, 5, 8. Em história Parcial, "restante" indica os pontos que faltam.

---

## Épico CAT: Catálogo de fluxos
Transformar o acervo bruto em produto vendável e seguro de entregar.

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| CAT-01 | Como operador, quero marcar a origem e a licença de cada pasta do acervo (próprio, curso, pacote de terceiros), para saber o que posso revender. | 2 | P0 | R1 | Dúvida 1 | Parcial: `flows.source` já guarda a pasta; falta a tabela pasta → licença e o filtro. Pontos reduzidos de 3 para 2 por isso. Cuidado: na deduplicação só a primeira cópia guarda `source`; um fluxo presente em duas pastas herda só uma licença (usar a mais restritiva) |
| CAT-02 | Como operador, quero um status de qualidade por fluxo (testado, precisa ajuste, quebrado), para não oferecer o que não funciona. | 3 | P1 | R1 | | A fazer. Rebaixado de P0 para P1: na R1 basta registrar o status do fluxo base de cada pedido (INT-07), não dos 1.433 |
| CAT-03 | Como operador, quero um scanner que acusa tokens, e-mails, IDs de credencial e URLs de webhook dentro do JSON, para não vazar dado de um cliente para outro. | 5 | P0 | R1 | | **Feito** (FND-13; tarefa seguinte: ligar o scanner como porta de `Entregue`, em ENT-02). Antes, a checagem era feita pelo LLM (`construtor-n8n` passo 3, `qa-fluxos` passo 3), sem garantia determinística. Inclui os próprios testes. Critérios refinados abaixo |
| CAT-04 | Como operador, quero uma descrição em português por fluxo (o que faz, para quem, pré-requisitos), gerada por IA e revisada por mim. | 5 | P1 | R2 | CAT-02 | A fazer |
| CAT-05 | Como operador, quero tags de nicho (imobiliária, clínica, e-commerce, agência) e de problema (leads, atendimento, relatórios), para filtrar. | 5 | P1 | R2 | | A fazer |
| CAT-06 | Como operador, quero agrupar quase-duplicatas e eleger a versão canônica de cada fluxo. | 3 | P1 | R2 | | A fazer (duplicata exata já sai por SHA1 em FND-01) |
| CAT-07 | Como operador, quero a lista de pré-requisitos e custo mensal estimado de API por fluxo, para orçar corretamente. | 5 | P1 | R2 | | Parcial: o indexador extrai `credentials` e `integrations` por fluxo; falta custo |
| CAT-08 | Como operador, quero importar um fluxo novo por upload, com extração e deduplicação automáticas, e testes do indexador. | 5 | P1 | R2 | CAT-03, CAT-01 | A fazer. Os testes do indexador saíram de PLT-02 para cá, onde o indexador muda |
| CAT-09 | Como agente, quero busca semântica (embeddings), para achar “captar lead do Instagram” mesmo sem as palavras do título. | 8 | P2 | R2 | PLT-03 | A fazer |
| CAT-10 | Como operador, quero fluxos “produtizados” (README, vídeo curto, preço de tabela), para vender o pronto. | 8 | P2 | R3 | CAT-04, CAT-01 | A fazer. Só para fluxos com licença de revenda |
| CAT-11 | Como operador, quero versionar cada fluxo e ver o histórico de mudanças. | 5 | P3 | R3 | PLT-01 | A fazer |

## Épico AGT: Agente consultor
O “faço a pergunta e ele acha ou entrevista”.

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| AGT-01 | Como operador, quero que o agente responda sempre no mesmo formato: (1) fluxo recomendado e lacunas, (2) features, (3) orçamento, (4) riscos e pendências, (5) prompt para o Claude Code. | 3 | P0 | R1 | FND-04 | Parcial (restante 1, no ensaio): o formato de 5 seções está no prompt do `flow-consultant`; nunca foi medido. Correção: o texto antigo listava 6 itens e o critério dizia 5 seções; "lacunas" fica dentro da seção 1 |
| AGT-02 | Como operador, quero que o agente nunca invente fluxo e sempre cite o caminho do arquivo. | 3 | P0 | R1 | | Parcial (restante: junto com AGT-01): regra no prompt e no `CLAUDE.md`; sem teste |
| AGT-03 | Como cliente, quero conversar com o agente numa página web, sem instalar nada. | 8 | P1 | R2 | AGT-07, PLT-04, PLT-05, PLT-07 | Parcial: o chat existe só para o operador, em `127.0.0.1`. Correção: depende de limite e medição de custo, login e política de dados antes de abrir a cliente; não depende de PLT-03 |
| AGT-04 | Como cliente, quero que a entrevista faça no máximo 5 perguntas e salve as respostas no briefing. | 5 | P1 | R2 | INT-01 | Parcial: regra de 5 perguntas nos prompts do `flow-consultant` e `analista-de-pedido`, para o operador |
| AGT-05 | Como agente, quero um plano “construir do zero” quando nenhum fluxo serve, partindo dos 2 ou 3 mais próximos. | 3 | P1 | R2 | | Parcial: o prompt manda dizer que não achou e propor construir; sem o plano a partir dos mais próximos |
| AGT-06 | Como operador, quero uma bateria de 30 perguntas de teste com a resposta esperada, para medir se o agente piorou depois de mudar o prompt ou o catálogo. | 5 | P1 | R2 | | A fazer. Na R1, versão mínima: 5 perguntas conferidas à mão (ver AGT-01/02) |
| AGT-07 | Como operador, quero limite de custo e de tamanho por sessão do agente. | 3 | P1 | R2 | PLT-07 | Parcial: só há limite de 4.000 caracteres por mensagem e 300 s por chamada; sem limite de custo. Pré-requisito de AGT-03 |
| AGT-08 | Como cliente, quero falar com o agente pelo WhatsApp ou Telegram, via n8n. | 8 | P2 | R3 | AGT-03 | A fazer |
| AGT-09 | Como operador, quero que a conversa seja retomada depois de dias. | 5 | P2 | R3 | | Parcial: o painel usa `--resume <session_id>`; não verificado após dias nem após reiniciar o navegador. Correção: não depende de PLT-03 |
| AGT-10 | Como operador, quero marcar “esse fluxo serviu / não serviu” para melhorar o ranking. | 5 | P2 | R3 | | A fazer |

## Épico INT: Pedido do cliente (intake)

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| INT-01 | Como operador, quero um formulário de briefing (problema, volume, ferramentas, urgência, faixa de orçamento, quem opera depois). | 5 | P0 | R1 | INT-07 | Parcial (restante: no ensaio): perguntas no `analista-de-pedido` e na skill `intake-briefing`; seções no `_modelo-pedido.md`. Os campos que faltam no modelo entram em INT-07; a tela entra em INT-06 |
| INT-02 | Como operador, quero registrar cada pedido com número, cliente, data e status. | 3 | P0 | R1 | | Parcial (restante: no ensaio): modelo com `id`, `cliente`, `criado`, `status`; o `analista-de-pedido` numera o próximo PED livre. Nunca exercitado com pedido real (só o exemplo PED-001) |
| INT-03 | Como operador, quero calcular o ROI do cliente (horas por semana x custo por hora = economia mensal), para sustentar o preço. | 3 | P0 | R1 | ORC-12 | Parcial: `quote.py` calcula o payback a partir da economia informada; a economia (h/semana x 4 x custo/h) é calculada pelo LLM, contra a regra "nunca de cabeça". Fecha com ORC-12 |
| INT-04 | Como operador, quero a matriz de certezas, suposições e dúvidas gerada do briefing. | 3 | P1 | R2 | INT-01 | Parcial: o `analista-de-pedido` já gera a CSD. Correção: o texto citava `feature-discovery`, que é agente genérico de desenvolvimento, não do Flow Hub |
| INT-05 | Como cliente, quero anexar prints, planilhas e áudios, com transcrição automática dos áudios. | 5 | P2 | R3 | PLT-10 | A fazer |
| INT-06 | Como operador, quero criar um pedido pela aba Pedidos do painel, para não depender do chat (US$ 0,30 e até 35 s por mensagem) nem editar arquivo. | 3 | P1 | R1 | INT-01, INT-02, INT-07 | **Feito** (FND-11). Nova, critérios abaixo |
| INT-07 | Como operador, quero que o modelo de pedido tenha os dados que a proposta e o contrato exigem (contratante com CPF/CNPJ, endereço e representante; urgência; faixa de orçamento; validade e prazo da proposta; fluxo base com origem, licença e status de qualidade; aceite; entrada paga com comprovante; horas reais), para ter uma fonte única. | 1 | P0 | R1 | PLT-10 | **Feito** (FND-16). Nova; só modelo `.md`, sem código. Dados cadastrais do contratante ficam em `vault/Clientes/`, não no pedido |

## Épico FEA: Quebra em features

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| FEA-01 | Como operador, quero que o briefing e o fluxo escolhido virem uma lista de features, cada uma com critério de aceite e horas. | 5 | P0 | R1 | INT-01, AGT-01 | Parcial (restante: no ensaio): agente e skill `quebra-de-features` com tabela padrão; nunca exercitado com pedido real |
| FEA-02 | Como operador, quero editar, reordenar e remover features, com o total de horas recalculado. | 3 | P1 | R1 | FEA-01 | A fazer. Rebaixado para P1: na R1 o operador edita a tabela no `.md` e pede ao agente para somar. Correção do critério: "muda na hora" vale só quando houver tela |
| FEA-03 | Como operador, quero exportar o projeto para o Claude Code: `CLAUDE.md` do projeto, JSON do fluxo base e o prompt da primeira feature. | 5 | P1 | R1 | FEA-01, PLT-10 | Parcial: `construtor-n8n` cria `projetos/<cliente>/fluxo.json` e `LEIA-ME.md`; `quebra-de-features` devolve o prompt; falta o `CLAUDE.md` do projeto. Rebaixado para P1 |
| FEA-04 | Como operador, quero marcar cada feature como “adaptar do acervo” ou “construir”, para o orçamento refletir o desconto de reaproveitamento. | 3 | P1 | R2 | FEA-01, ORC-12 | Parcial: coluna `Origem` existe; o cálculo separado entra em ORC-12. **Conflito resolvido em ORC-12:** a skill diz que o desconto vale só para `adaptar`, mas `quote.py --adapted` desconta 20% de todas as horas |
| FEA-05 | Como operador, quero fases com datas (diagnóstico 3 dias, PoC 7, go-live 21), como no 1-pager. | 3 | P1 | R2 | | Parcial: fases na skill, sem datas |
| FEA-06 | Como operador, quero congelar a versão aprovada do escopo; qualquer mudança vira um pedido de alteração cobrável. | 5 | P1 | R2 | ORC-13 | Parcial: regra escrita e seção "Decisões e pedidos de alteração" no modelo; o congelamento real vem do aceite registrado (ORC-13) |

## Épico ORC: Orçamento e cobrança
O ponto que você disse não saber fazer.

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| ORC-01 | Como operador, quero calcular setup, mensalidade e entrada a partir das horas das features. | 5 | P0 | R1 | FEA-01, FND-03, ORC-12 | Parcial (restante: no ensaio): `quote.py` + aba Orçamento calculam; horas digitadas à mão, não somadas das features. Correção: dependia de FEA-02, passa a depender de FEA-01; "parâmetros e pisos editáveis" saiu daqui para ORC-12, para não haver duas histórias para a mesma coisa |
| ORC-02 | Como operador, quero gerar a proposta 1-pager em PDF (problema, solução, escopo, prazo, investimento, ROI). | 5 | P0 | R1 | ORC-01, INT-03, INT-07, ORC-12, ENT-09, PLT-10 | **Feito** (FND-14), menos o anexo de suporte como arquivo próprio (ENT-09): as condições de suporte já saem dentro da proposta. Antes: o `orcamentista` só preparava os textos. Pontos de 8 para 5 com HTML + "imprimir como PDF". Correção: identidade visual própria, não "modelo Flowgrammers" (marca de terceiro) |
| ORC-03 | Como operador, quero gerar o contrato em Word preenchido com dados do cliente e escopo, a partir do modelo que você já tem. | 5 | P1 | R1 | ORC-13, INT-07, Dúvida 2 | Parcial: o `orcamentista` lista os campos entre colchetes que faltam. Rebaixado para P1: no primeiro cliente, preencher à mão com essa lista. Antes de codar, inventariar os campos do `.docx` (placeholders podem estar quebrados em vários trechos internos do Word) |
| ORC-04 | Como cliente, quero pagar a entrada de 50% por link (Pix ou cartão) e o sistema confirmar o pagamento sozinho. | 8 | P1 | R2 | ORC-02, Dúvida 5 | A fazer. R1: Pix manual, `entrada_paga` e comprovante (INT-07, ENT-01) |
| ORC-05 | Como operador, quero cobrança mensal recorrente da manutenção, com lembrete, aviso de atraso e suspensão combinada em contrato. | 8 | P1 | R2 | ORC-04, ENT-09 | A fazer |
| ORC-06 | Como cliente, quero assinar o contrato online. | 5 | P2 | R2 | ORC-03 | A fazer |
| ORC-07 | Como operador, quero opções de pacote (Essencial, Padrão, Completo) na proposta. | 5 | P2 | R2 | ORC-02 | A fazer. Pode servir de teste de preço (ver `REVISAO-PRODUTO.md`, seção E) |
| ORC-08 | Como operador, quero cobrar extras por hora a partir de um pedido de alteração. | 3 | P2 | R2 | FEA-06 | A fazer |
| ORC-09 | Como operador, quero emitir nota fiscal ou recibo conforme o meu regime. | 5 | P2 | R3 | Dúvida 2 | A fazer. Correção: não depende de ORC-04; depende do regime fiscal |
| ORC-10 | Como operador, quero um painel financeiro: a receber, recebido, receita recorrente mensal e margem por projeto. | 8 | P2 | R3 | ORC-05, ENT-05 | A fazer |
| ORC-11 | Como operador, quero comparar horas orçadas com horas reais e receber sugestão de ajuste nos parâmetros de preço. | 5 | P3 | R3 | ENT-05 | A fazer. A comparação simples entra na R1 via ENT-05; aqui fica só a sugestão automática |
| ORC-12 | Como operador, quero que a calculadora calcule a economia do cliente, respeite o piso mesmo com teto de ROI, calcule o payback líquido da mensalidade, desconte só as horas `adaptar` e leia os parâmetros de um arquivo, para não fechar abaixo do custo nem prometer payback errado. | 3 | P0 | R1 | | **Feito** (FND-10). Nova; inclui os testes de `quote.py`. Parâmetros em `flowhub/parametros.json` (configuração), separados do histórico de vendas em `vault/Precos/Parametros-de-Preco.md` (dados) |
| ORC-13 | Como operador, quero registrar o aceite do cliente (versão da proposta, data, canal e evidência), para ter prova do escopo e do preço aprovados. | 2 | P0 | R1 | ORC-02, ENT-01 | **Feito** (FND-12): campos de aceite no pedido, trava de Aprovado e de Em construção e congelamento de preço. Pendente: guardar o arquivo da evidência pela tela (hoje só o nome; o arquivo vai à mão para `vault/Pedidos/anexos`). Nova |

## Épico ENT: Projetos e entrega

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| ENT-01 | Como operador, quero um kanban de projetos (Pedido, Discovery, Features, Orçado, Aprovado, Em construção, Entregue, Suporte) que só deixa avançar quando o pré-requisito do estado existe. | 5 | P0 | R1 | INT-02, INT-07 | **Feito** (FND-12): as travas existem e são cumulativas (quem pula estado também passa pelas travas dos estados pulados); voltar é livre e fica registrado no Histórico. Antes: kanban com os 8 estados que trocava só a linha `status:` e aceitava qualquer salto. A trava de Entregue só cobra o checklist; falta ligar o scanner (ENT-02). Texto original: o restante é o mecanismo de travas; cada trava é definida pela história dona (ORC-13, ENT-02). Correção: a lista antiga omitia "Features" |
| ENT-02 | Como operador, quero um checklist de entrega: credenciais do cliente anterior removidas (scanner limpo), teste com dados de exemplo, alerta de falha testado, documentação, vídeo de 5 min, treino de 30 min. | 3 | P0 | R1 | CAT-03, ENT-01, ENT-08 | Parcial: o checklist agora vive no pedido e o kanban só deixa ir para "Entregue" com todos os itens marcados (FND-12). Falta o scanner (CAT-03) limpo em `projetos/<cliente>/` e o alerta de falha testado (ENT-08) virarem portas automáticas: hoje são itens do checklist marcados à mão. Esta história é a única dona da trava de "Entregue" |
| ENT-03 | Como operador, quero guardar as credenciais do cliente num cofre, nunca em arquivo do projeto. | 5 | P1 | R2 | Dúvida 3 | Parcial: regra escrita (credenciais só no cofre do n8n); sem ferramenta |
| ENT-04 | Como operador, quero alerta quando uma execução falha no n8n do cliente e um relatório mensal enviado a ele, o que justifica a mensalidade. | 8 | P1 | R2 | ENT-08, Dúvida 3 | A fazer. A parte mínima (alerta) sobe para a R1 em ENT-08 |
| ENT-05 | Como operador, quero registrar horas reais por pedido e por mês de suporte, para calibrar o preço depois de cada entrega. | 2 | P0 | R1 | INT-07 | Parcial (FND-15): a tela registra horas reais por pedido e soma em `horas_reais`. Falta: horas de suporte por mês e, ao entregar, acrescentar a linha em "Histórico de vendas reais" de `vault/Precos/Parametros-de-Preco.md` com o desvio em %. Subiu de P2/R2 para P0/R1 e de cronômetro para registro simples: sem horas reais a calibração prometida nos Riscos não acontece. Critérios abaixo |
| ENT-06 | Como operador, quero instalar o fluxo na instância n8n do cliente pela API, sem importar à mão. | 8 | P2 | R3 | ENT-03 | A fazer |
| ENT-07 | Como cliente, quero abrir um chamado de suporte e ver o prazo de resposta. | 5 | P3 | R3 | ENT-09 | A fazer |
| ENT-08 | Como operador, quero que todo fluxo entregue tenha um fluxo de erro (Error Trigger do n8n) que me avisa por e-mail, para saber da falha antes do cliente. | 2 | P0 | R1 | Dúvida 3 | Parcial (FND-18): existe o modelo `templates/n8n/alerta-de-falha.json` e toda geração de pacote cria a task E4-S1-T1 para ligá-lo; falta testar numa instância n8n real. Nova: o 1-pager e a skill prometem "alertas de falha por e-mail" e nada garante isso |
| ENT-09 | Como operador, quero um anexo de suporte e entrega padrão (o que a mensalidade cobre, prazo de resposta, o que é pedido de alteração, atraso de pagamento, propriedade do fluxo entregue, o que acontece se a mensalidade for cancelada, limite de responsabilidade quando uma API de terceiro ou o n8n do cliente muda), para vender a mensalidade sem promessa vaga. | 1 | P0 | R1 | | Parcial: o resumo das condições (cobertura, alteração, propriedade do fluxo, cancelamento, responsabilidade) já sai dentro da proposta em PDF; falta o anexo completo como documento próprio, com revisão jurídica. Nova; texto, sem código. Revisão jurídica recomendada antes do primeiro contrato |

## Épico VIT: Vitrine

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| VIT-01 | Como visitante, quero ver os fluxos vendáveis com filtro por nicho e problema. | 8 | P2 | R3 | CAT-01, CAT-05, CAT-10 | A fazer |
| VIT-02 | Como visitante, quero uma página por fluxo com preço de tabela e botão “pedir orçamento” que abre o chat do agente. | 5 | P2 | R3 | VIT-01, AGT-03 | A fazer |
| VIT-03 | Como operador, quero publicar a vitrine dentro do portal agile-coach-ai. | 3 | P3 | R3 | VIT-01, Dúvida 6 | A fazer |
| VIT-04 | Como visitante, quero ver casos e depoimentos de clientes. | 2 | P3 | R3 | | A fazer. Pedir autorização de uso no contrato do primeiro cliente |

## Épico PLT: Plataforma e qualidade

| ID | História | Pts | Prio | Release | Depende de | Estado |
|---|---|---|---|---|---|---|
| PLT-01 | Como operador, quero o projeto no Git, com histórico e CI rodando os testes. | 2 | P1 | R1 | PLT-10 | A fazer. Rebaixado para P1. Antes, decidir o que fica fora do Git: `vault/Pedidos`, `vault/Clientes`, `projetos/` e `_raw/` (dados de cliente e acervo de terceiros) |
| PLT-02 | Como operador, quero testes automatizados da busca e do orçamento. | 2 | P1 | R1 | | Parcial: há 15 testes do painel, nenhum de `search.py` ou `quote.py`. Correção: não depende de PLT-01. Os testes de `quote.py` passaram para ORC-12, os do scanner para CAT-03 e os do indexador para CAT-08; aqui fica a busca |
| PLT-03 | Como operador, quero um banco único em nuvem (Supabase, que você já usa no portal) com Postgres e pgvector. | 5 | P1 | R2 | PLT-05 | A fazer |
| PLT-04 | Como operador, quero login, para que só eu acesse o painel. | 3 | P1 | R2 | | A fazer. Hoje compensado por servir só em `127.0.0.1` com checagem de `Host`; vira obrigatório quando o painel sair da máquina. Correção: não depende de PLT-03 |
| PLT-05 | Como operador, quero termo de uso e política de dados dos clientes, com retenção e exclusão (LGPD). | 3 | P1 | R2 | PLT-10 | A fazer. A parte mínima sobe para a R1 em PLT-10 |
| PLT-06 | Como operador, quero backup automático do banco. | 2 | P1 | R2 | PLT-03 | A fazer. O backup do vault local entra na R1 em PLT-09 |
| PLT-07 | Como operador, quero ver o custo de IA por sessão e por projeto. | 3 | P2 | R2 | | A fazer. Pré-requisito de AGT-07 e AGT-03 |
| PLT-08 | Como operador, quero papéis (admin, operador, cliente) para entrar parceiros. | 5 | P3 | R3 | PLT-04 | A fazer |
| PLT-09 | Como operador, quero backup diário e criptografado do `vault/` e de `projetos/` para um destino fora da máquina que só eu acesso, com teste de restauração, para não perder pedidos e entregas. | 1 | P0 | R1 | PLT-10 | A fazer. Nova |
| PLT-10 | Como operador, quero uma regra de dados mínimos no vault (só dados comerciais do contratante, nada de dado pessoal dos clientes finais do cliente) e um aviso de que o chat envia o conteúdo lido à Anthropic, para reduzir exposição sob a LGPD. | 1 | P0 | R1 | | Parcial: os dois modelos já dizem o que pode e o que não pode ser gravado, e a proposta traz o aviso de processamento com IA de terceiro. Falta o mesmo aviso no contrato. Nova; texto e modelo, sem código |
| PLT-11 | Como operador, quero os 8 estados e os campos do pedido definidos num só lugar, com skills e agentes apontando para ele, para não divergirem. | 1 | P2 | R2 | INT-07 | A fazer. Nova: hoje os estados estão repetidos em `pedidos.js`, `CLAUDE.md`, modelo e skills |

---

## Critérios de aceite das histórias da R1

**Ensaio ponta a ponta (fecha AGT-01, AGT-02, INT-01, INT-02, FEA-01, ORC-01)**
- Dado um pedido fictício realista (não o PED-001), quando ele passa por `analista-de-pedido` → `flow-consultant` → `quebra-de-features` → `orcamentista`, então o pedido sai em "Orçado" com briefing, CSD, ROI, features com horas, orçamento do script e nenhum `path` inexistente. Cada história fecha se o seu critério abaixo passar; falhas viram correção de prompt.

**CAT-01**
- Dado cada uma das pastas de origem do acervo (`src1..src9`), quando eu classifico, então todo fluxo herda “próprio”, “curso” ou “terceiros” e o texto da licença ou "sem resposta".
- Dado um fluxo que existe em mais de uma pasta, então ele herda a licença mais restritiva.
- Quando busco, então posso filtrar apenas fluxos revendáveis; "sem resposta" conta como não revendável.

**CAT-03** (refinado)
- Dado um JSON com token, chave de API, e-mail, ID de credencial, URL de webhook ou ID de planilha/pasta do Google, quando rodo o scanner, então ele lista cada ocorrência com nome do nó, campo e trecho mascarado (nunca o valor inteiro), e sai com código diferente de 0.
- Dado um JSON limpo ou só com placeholders (`{{...}}`, `SEU_TOKEN`), então diz “limpo”, lista os padrões verificados e sai com código 0.
- Dado um JSON inválido num lote, então o scanner reporta o arquivo, segue com os demais e sai com código diferente de 0.
- Dado um JSON de teste com 10 segredos plantados, então o scanner acha os 10 e nenhum aparece inteiro na saída (teste automatizado).

**AGT-01 e AGT-02**
- Dada qualquer pergunta, a resposta traz as 5 seções na ordem combinada.
- Dada uma pergunta sem fluxo adequado, o agente diz que não achou e propõe construir, sem citar arquivo inexistente.
- Na R1: 5 perguntas de referência conferidas à mão depois de cada mudança de prompt; todo `path` citado existe no disco.

**INT-03**
- Dado “15 horas por semana a R$ 50 por hora”, então a economia mensal é R$ 3.000, calculada pelo script, e o payback é calculado sobre o setup e sobre a economia líquida da mensalidade.

**INT-06** (nova)
- Dado o formulário da aba Pedidos com contratante, problema, volume (horas por semana), custo da hora, ferramentas, gatilho, urgência, faixa de orçamento e quem opera depois, quando salvo, então nasce `vault/Pedidos/PED-NNN-<cliente>.md` a partir do `_modelo-pedido.md`, com o próximo número livre, `status: Pedido` e `criado` com a data do dia.
- Dado um campo obrigatório vazio ou um nome de cliente com caracteres de caminho (`/`, `\`, `..`), então nada é gravado e a tela diz qual campo corrigir; o arquivo só pode nascer dentro de `vault/Pedidos/`.
- Dado que já existe `PED-007`, quando dois pedidos são criados em seguida, então recebem `PED-008` e `PED-009`, sem sobrescrever arquivo.
- O pedido criado aparece no kanban sem reiniciar o servidor e não chama o chat (custo zero de IA).

**INT-07** (nova)
- O `_modelo-pedido.md` tem os campos listados na história; o `_modelo-cliente.md` tem CPF/CNPJ, endereço e representante do contratante.
- Dado um pedido criado pelo `analista-de-pedido` depois da mudança, então os campos novos aparecem (vazios quando não informados, nunca inventados).

**FEA-01 e FEA-02**
- Dado um briefing e um fluxo, então cada feature tem título, origem, critério de aceite e horas em número.
- Quando removo uma feature do pedido e peço o recálculo, então o total de horas e o orçamento do pedido são atualizados (instantâneo só quando houver tela).

**FEA-03**
- Quando exporto, então a pasta do projeto contém `CLAUDE.md`, o JSON do fluxo base e o prompt da primeira feature, e abre no Claude Code sem ajustes.

**ORC-01**
- Dado as features de um pedido somando 20 horas, complexidade média e economia de R$ 3.000 por mês, então o orçamento usa as 20 horas sem redigitação, respeita as regras de ORC-12 e a mensalidade nunca fica abaixo do mínimo.

**ORC-12** (nova)
- Dado complexidade média, 10 horas e economia de R$ 300 por mês (teto R$ 1.800, abaixo do piso R$ 2.200), então a calculadora devolve o piso e o aviso "inviável pelo ROI; rever escopo ou argumento", nunca um valor abaixo do piso.
- Dado setup R$ 3.500, mensalidade R$ 497 e economia R$ 3.000, então o payback líquido é cerca de 42 dias (3.500 / 2.503 x 30) e a economia anual líquida é R$ 26.536 (36.000 − 3.500 − 12 x 497).
- Dado 15 horas por semana e R$ 50 por hora, então a economia mensal sai do script: R$ 3.000.
- Dado `flowhub/parametros.json` alterado (ex.: valor da hora R$ 180), então o próximo orçamento usa o novo valor sem mudar código e registra a versão dos parâmetros usada.
- Dado horas `adaptar` e horas `construir` separadas, então o desconto de reaproveitamento incide só nas horas `adaptar`.
- Todos os casos acima são testes automatizados.

**ORC-02 e ORC-03**
- O PDF cabe em uma página, traz os números do orçamento sem digitação manual, abre em qualquer leitor, tem número de versão (`PED-NNN-v1`) e validade.
- Dado um pedido sem setup ou mensalidade, então recusa e aponta os campos faltantes. Dado um pedido sem economia mensal, então o PDF sai sem a seção ROI e com aviso ao operador, nunca com ROI inventado.
- A proposta inclui o anexo de suporte (ENT-09), "licenças e APIs de terceiros por conta do cliente" e o aviso de processamento com apoio de IA (PLT-10).
- O contrato sai com todos os campos entre colchetes preenchidos e o modelo original intacto; se faltar dado do cliente, o sistema avisa qual e não gera o arquivo.

**ORC-13** (nova)
- Dado uma proposta `PED-NNN-vX` enviada, quando o cliente aprova por e-mail ou WhatsApp, então o pedido guarda versão, data, canal e o print ou texto do aceite em `vault/Pedidos/anexos/`.
- Dado um pedido sem aceite registrado, quando tento mover para "Aprovado", então o kanban recusa e diz o motivo.
- Dado um pedido "Aprovado" com `entrada_paga: false` ou sem comprovante, quando tento mover para "Em construção", então o kanban recusa.
- Depois do aceite, escopo e preço do pedido ficam congelados; mudança vira pedido de alteração (FEA-06).

**ENT-01**
- Dado uma trava definida (ORC-13, ENT-02), quando o pré-requisito falta, então a mudança de estado é recusada com a mensagem da trava e o arquivo não muda.
- Voltar um estado é sempre permitido e fica registrado no Histórico do pedido.

**ENT-02**
- O projeto só pode ir para “Entregue” com todos os itens do checklist marcados, o scanner (CAT-03) limpo em `projetos/<cliente>/` e o alerta de falha (ENT-08) testado.

**ENT-05** (refinado)
- Dado um pedido, quando registro "data, horas, feature ou atividade", então a linha entra numa tabela "Horas reais" do pedido e o cabeçalho ganha `horas_reais` somado; horas negativas ou não numéricas são recusadas.
- Quando o pedido vai para "Entregue", então uma linha é acrescentada ao "Histórico de vendas reais" de `vault/Precos/Parametros-de-Preco.md` (horas orçadas, reais, setup, mensal) com o desvio em %.
- Horas de suporte do mês também são registradas, para testar se a mensalidade cobre o trabalho.

**ENT-08** (nova)
- Dado um fluxo entregue, então existe um fluxo de erro ligado a ele no n8n do cliente que envia e-mail ao Thiago com nome do fluxo, nó que falhou e horário.
- Dado uma falha forçada no teste de entrega, então o e-mail chega.

**ENT-09** (nova)
- O anexo cobre todos os itens listados na história e é anexado à proposta (ORC-02) e ao contrato.

**PLT-09** (nova)
- Dado o backup diário, então o destino guarda só cópias criptografadas e o acesso é só do Thiago.
- Quando apago uma cópia de teste do `vault/`, então consigo restaurar a partir do destino externo e o conteúdo bate.

**PLT-10** (nova)
- O `_modelo-cliente.md` e o `_modelo-pedido.md` dizem quais dados podem e quais não podem ser gravados.
- O contrato e a proposta informam que dados do pedido são processados com apoio de IA de terceiro.

## Definição de pronto
- Tem teste automatizado quando há regra de cálculo, de busca ou de segurança (scanner).
- Nenhuma credencial ou dado de cliente em arquivo versionado.
- O Thiago consegue executar a história sem ajuda do desenvolvedor.
- O `CLAUDE.md` do projeto continua correto.
- O estado da história nesta tabela foi atualizado.

## Sequência recomendada para o primeiro cliente pagante
Pontos de histórias Parciais contam só o restante. Detalhe e conta RICE em `docs/REVISAO-PRODUTO.md`.

| Ordem | Entrega | Pts | Depende de |
|---|---|---|---|
| 0 | Thiago responde as dúvidas 1, 2 e 3 | 0 | |
| 1 | PLT-10 dados mínimos, PLT-09 backup, ENT-09 anexo de suporte, INT-07 modelo de pedido | 4 | |
| 2 | ORC-12 fórmula corrigida com testes (fecha INT-03) | 3 | |
| 3 | CAT-01 licença por pasta | 2 | Dúvida 1 |
| 4 | Ensaio ponta a ponta com pedido fictício (fecha AGT-01, AGT-02, INT-01, INT-02, FEA-01, ORC-01) | 2 | 1, 2 |
| 5 | ENT-01 travas (restante), ORC-02 proposta PDF, ORC-13 aceite | 9 | 4 |
| — | **Primeira proposta pode sair aqui** (contrato preenchido à mão com a lista do `orcamentista`; Pix manual) | | |
| 6 | CAT-03 scanner, ENT-08 alerta de falha | 7 | Dúvida 3 |
| 7 | ENT-02 checklist com trava, ENT-05 horas reais | 5 | 5, 6 |
| — | **Primeira entrega pode sair aqui** | | |
| 8 | INT-06 criar pedido pela tela, PLT-02 testes da busca | 5 | 1, 4 |
| 9 | ORC-03 contrato automático, FEA-03 export, PLT-01 Git | 12 | 5, Dúvida 2 |

Até a primeira proposta: 20 pontos. **Até a primeira entrega: 32 pontos.** Todos os P0 da R1 estão cobertos até a ordem 7. Adiado para depois da primeira venda: ordens 8 e 9, tudo da R2 e R3, CAT-02 completo, FEA-02 em tela, AGT-06 com 30 perguntas.

## Riscos
| Risco | Efeito | Resposta |
|---|---|---|
| Parte do acervo é de terceiros (pacotes e cursos) | Vender fluxo sem direito de revenda | CAT-01 primeiro; sem resposta escrita, tratar como não revendável e usar o fluxo só como referência para construir |
| Vazar credencial de um cliente para outro | Quebra de confiança e LGPD | CAT-03 e ENT-02 obrigatórios, com trava no kanban |
| Preço calibrado errado | Trabalhar no prejuízo | ORC-12 já; ENT-05 desde o primeiro pedido; revisar após as 3 primeiras vendas |
| Agente recomenda fluxo inadequado | Retrabalho e atraso | Ensaio e 5 perguntas de referência na R1; AGT-06 antes de abrir ao cliente |
| Manutenção mensal sem entrega visível ou sem limite de responsabilidade | Cliente cancela ou cobra por falha de terceiro | ENT-08 e ENT-09 na R1; ENT-04 (relatório) na R2 |
| Dados de cliente só no disco local, sem backup | Perda de pedidos e exposição sob a LGPD | PLT-09 e PLT-10 na R1 |
| Escopo aprovado sem evidência; trabalho iniciado sem entrada | Disputa de escopo e calote | ORC-13 com travas de "Aprovado" e "Em construção" |
| Chat aberto ao cliente sem limite (US$ 0,30 por mensagem) | Custo sem receita | AGT-03 só depois de AGT-07 e PLT-07 |

## Dúvidas abertas (preciso da sua resposta)
Cada uma tem uma recomendação padrão: se você não responder, seguimos com ela.

1. **Qual a licença de uso dos acervos Flowgrammers, SuperPackIA e do curso do Ric Neves para revenda ou entrega a clientes?**
   Padrão: Posso revender
2. **Você é MEI, ME ou pessoa física?**
   Padrão: Ainda pessoa fisica abrindo mei
3. **O fluxo roda no n8n do cliente ou no seu?**
   Padrão: Decida o melhor
4. **Primeiro canal do cliente: chat no site, WhatsApp ou formulário?**
   Padrão: Depende do que o cliente quer .
5. **Qual meio de pagamento: Pix direto, Asaas, Mercado Pago ou Stripe?**
   Padrão: Pix e mercado pago
6. **A vitrine pública vai dentro do agile-coach-ai ou em domínio próprio?**
   Padrão: Qual voce me sugerir ser melhor 
   