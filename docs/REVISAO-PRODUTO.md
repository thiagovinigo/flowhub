# Revisão de produto do Flow Hub

**Data:** 2026-10-01 · **Escopo:** auditoria do backlog contra o que existe, lacunas e riscos, priorização até o primeiro cliente pagante, preço e dúvidas abertas.
**Arquivo ligado:** `docs/BACKLOG.md` (estados, histórias novas, critérios de aceite e respostas sugeridas às dúvidas já aplicados lá).
**Como foi feito:** leitura do código, agentes, skills, vault e material do cliente; discovery e refinamento das 5 lacunas principais em paralelo; validação de dependências e pontos do backlog revisado por um terceiro agente (que achou e fez corrigir a soma de pontos, o conflito ORC-01 x ORC-12 e a ordem ENT-02 x ENT-08).

Convenção: **[Fato]** foi verificado no repositório nesta data. **[Hipótese]** é suposição a validar. Não há afirmação de mercado com fonte neste documento; onde falta fonte, está escrito como hipótese e com um teste.

---

## A. Auditoria produto x backlog

### O que existe de fato
| Peça | Evidência [Fato] |
|---|---|
| Catálogo | `flowhub/indexer.py` grava `flows` + FTS5; coluna `source` = pasta `src1..src9`; deduplicação por SHA1 guarda só a primeira cópia |
| Busca | `flowhub/search.py` com filtros de integração, IA e complexidade máxima |
| Orçamento | `flowhub/quote.py`: constantes no código, desconto `--adapted` sobre todas as horas, teto de ROI aplicado depois do piso |
| Agentes e skills | 6 agentes em `.claude/agents/`, 5 skills em `.claude/skills/` |
| Cofre | `vault/` com modelos de pedido e cliente, parâmetros de preço, aprendizados vazios, `PED-001` de exemplo |
| Painel | `server/server.js` só em `127.0.0.1`, checagem de `Host`, rotas health, search, quote, chat, pedidos, status |
| Kanban | `server/lib/pedidos.js`: 8 estados, só troca `status:`, aceita qualquer transição, não cria pedido |
| Testes | 15 testes Node: 6 de validação, 9 do kanban. Nenhum de `indexer.py`, `search.py`, `quote.py` |

### Placar
Das 71 histórias originais: **nenhuma Feita por completo**, **24 Parciais**, o resto A fazer. O "Feito" ganhou 4 entregas que já existiam sem registro (FND-06 a FND-09). Entraram 9 histórias novas (INT-06, INT-07, ORC-12, ORC-13, ENT-08, ENT-09, PLT-09, PLT-10, PLT-11) e ENT-05 foi reescrita e promovida.

### Correções feitas no backlog
| Item | Problema | Correção |
|---|---|---|
| AGT-01 | Texto com 6 itens, critério com "5 seções" | 5 seções; "lacunas" dentro da seção 1, como no prompt do agente |
| ENT-01 | Lista com 7 estados; o código tem 8 (falta "Features") | Lista dos 8 estados; restante da história = travas de transição |
| INT-04 | Citava `feature-discovery` (agente genérico de desenvolvimento) | O `analista-de-pedido` já gera a CSD |
| FND-03 | "Ancorada na proposta-exemplo" sem ressalva | A âncora é exemplo didático; 20 h médio dá R$ 3.750, não R$ 3.500 |
| PLT-02 | Dependia de PLT-01 (Git) e misturava 3 alvos | Sem dependência; testes de `quote.py` em ORC-12, do scanner em CAT-03, do indexador em CAT-08; fica a busca (P1) |
| AGT-03, AGT-09, PLT-04 | Dependiam de PLT-03 (Supabase) sem necessidade | AGT-03 passa a depender de AGT-07, PLT-04, PLT-05 e PLT-07 |
| ORC-01 | Dependia de FEA-02 (tela, P1) e duplicava "parâmetros editáveis" | Depende de FEA-01 e ORC-12; parâmetros só em ORC-12; critério sem conflito piso x teto |
| ORC-09 | Dependia de pagamento online | Depende do regime fiscal (dúvida 2) |
| FEA-02 | Critério "muda na hora" é de tela, numa release "sem telas" | Critério separado para R1 (arquivo + agente) e para tela |
| R1 | "Sem criar telas", mas o painel já existe; sem definição de fim | "Sem telas para o cliente"; termina com entrada paga e primeira entrega aceita |
| ORC-02 | "No modelo Flowgrammers" | Identidade visual própria (o modelo é material de terceiro) |
| ENT-05 / ORC-11 | Calibrar preço "após as 3 primeiras vendas" dependia de história R2/R3 | Registro de horas reais sobe para R1 (2 pts) |
| Trava de "Entregue" | Estava em CAT-03 e ENT-02 | Só em ENT-02, que agora depende também de ENT-08 |
| `CLAUDE.md` | Diz "ainda não tem testes" | Fora do escopo desta revisão editar; precisa ser corrigido |

### Conflitos entre artefatos
1. **Desconto de reaproveitamento:** a skill `quebra-de-features` diz que vale só para features `adaptar`; `quote.py --adapted` desconta 20% de todas as horas. Resolvido em ORC-12.
2. **Piso x teto:** o `CLAUDE.md` exige "acima do piso e abaixo do teto"; `quote.py` aplica o teto depois do piso e pode devolver valor abaixo do piso (ex.: médio, economia R$ 300/mês → setup R$ 1.800 < piso R$ 2.200). ORC-12: o piso vence e sai aviso de inviabilidade.
3. **Promessa de alerta:** o 1-pager e a skill `entrega-checklist` prometem "alertas de falha por e-mail"; nenhuma história da R1 garantia isso. ENT-08.
4. **Gate de entrega:** a skill diz "só vai para Entregue com o checklist"; o kanban aceita qualquer salto. ENT-01 (mecanismo) + ENT-02 (trava).
5. **PED-001:** diz 20 h e R$ 3.500; a calculadora dá R$ 3.750 para 20 h. Mostra que o exemplo não saiu da fórmula.
6. **Estados repetidos** em `pedidos.js`, `CLAUDE.md`, modelo e skills. PLT-11 (R2).

---

## B. Lacunas e os 5 maiores riscos

### Lacunas que o backlog original não cobria
| Lacuna | Situação [Fato] | Onde ficou |
|---|---|---|
| Como o pedido nasce | Só via agente (`analista-de-pedido`) ou arquivo; o chat custa ~US$ 0,30 e 15 a 35 s por mensagem | INT-06 |
| Dados que proposta e contrato exigem | Modelo sem CPF/CNPJ, endereço, representante, validade, origem/licença do fluxo, aceite, horas reais | INT-07 |
| Evidência de aceite e condição de início | Nenhum campo nem anexo; nada impede construir sem entrada paga | ORC-13 + ENT-01 |
| Backup do vault | Disco local, sem Git, sem cópia | PLT-09 |
| LGPD no vault e no chat | Modelos não dizem o que pode ser gravado; o chat lê o projeto e envia o conteúdo à API | PLT-10 |
| Falha do fluxo no n8n do cliente | Nada monitora | ENT-08 (R1), ENT-04 (R2) |
| Suporte pós-venda, propriedade do fluxo, cancelamento, responsabilidade | Mensalidade sem escopo nem regras | ENT-09 |
| Horas reais | Modelo sem campo; calibração impossível | ENT-05 |

### Os 5 maiores riscos
| # | Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|---|
| 1 | **Licença dos acervos de terceiros** (SuperPackIA, curso do Ric Neves, Flowgrammers): entregar ou revender fluxo sem direito. O modelo de proposta e o contrato também vêm desse material | Alta (nenhuma licença registrada) | Alto (jurídico e reputação) | Dúvida 1 respondida por escrito pelo fornecedor antes da primeira proposta; CAT-01 com "sem resposta = não revendável"; proposta com marca própria; para fluxo sem licença, usar como referência e construir |
| 2 | **Vazamento de credencial ou dado entre clientes**: fluxos do acervo trazem IDs, e-mails e webhooks de terceiros; hoje só o LLM procura | Alta | Alto | CAT-03 determinístico, testado com segredos plantados e saída mascarada; trava de "Entregue" (ENT-02) |
| 3 | **Mensalidade sem entrega definida**: sem alerta de falha, sem prazo de resposta, sem regra para API de terceiro que muda; falha descoberta pelo cliente | Média | Alto (cancelamento e desgaste) | ENT-08 e ENT-09 na R1; cláusulas de propriedade, cancelamento e limite de responsabilidade revisadas por advogado |
| 4 | **Preço sem validação**: âncora é um exemplo de curso, constantes sem fonte, payback otimista, possibilidade de vender abaixo do piso | Alta | Médio (prejuízo ou proposta recusada) | ORC-12 já; ENT-05 desde o primeiro pedido; teste de 3 propostas (seção E) |
| 5 | **Dados de cliente só no disco local, sem regra de LGPD**: perda do disco apaga pedidos; dados pessoais gravados sem critério e enviados ao chat | Média | Alto | PLT-09 (backup criptografado com restauração testada) e PLT-10 (dados mínimos, aviso na proposta e no contrato); n8n no ambiente do cliente (dúvida 3) reduz o que você guarda |

Outros riscos acompanhados: escopo aprovado sem prova e trabalho iniciado sem entrada (ORC-13 + travas); custo do chat se aberto ao cliente sem limite (AGT-07 e PLT-07 antes de AGT-03); agente recomendar fluxo errado (ensaio e 5 perguntas de referência na R1).

---

## C. Priorização até o primeiro cliente pagante

### Observação de partida
O caminho mínimo absoluto **não exige código**: com o que existe, o Thiago já consegue abrir pedido pelo agente, orçar, montar a proposta à mão e cobrar por Pix. O que falta para vender **com segurança** é: licença (risco 1), credenciais (risco 2), prova de aceite com entrada paga antes de construir, e um preço que não fique abaixo do piso. A sequência abaixo cobre isso e todos os P0 da R1, e nada além.

### RICE (curto)
Alcance = pedidos afetados nos 3 primeiros meses [Hipótese: 5 propostas, 3 vendas]. Impacto 1 a 3. Confiança de 0 a 1. Esforço em pontos (restante, se Parcial). Nota = A x I x C / E.

| ID | A | I | C | E | Nota | MoSCoW |
|---|---|---|---|---|---|---|
| PLT-09 backup | 5 | 2 | 0,9 | 1 | 9,0 | Must |
| PLT-10 dados mínimos | 5 | 2 | 0,8 | 1 | 8,0 | Must |
| INT-07 modelo de pedido | 5 | 2 | 0,8 | 1 | 8,0 | Must |
| ENT-09 anexo de suporte | 3 | 2 | 0,8 | 1 | 4,8 | Must |
| Ensaio ponta a ponta | 5 | 2 | 0,8 | 2 | 4,0 | Must |
| ORC-12 fórmula | 5 | 2 | 0,9 | 3 | 3,0 | Must |
| CAT-01 licença | 3 | 3 | 0,7 | 2 | 3,2 | Must |
| ORC-13 aceite | 3 | 2 | 0,8 | 2 | 2,4 | Must |
| ENT-08 alerta | 3 | 2 | 0,7 | 2 | 2,1 | Must |
| ENT-01 travas | 3 | 2 | 0,8 | 2 | 2,4 | Must |
| ORC-02 PDF | 5 | 2 | 0,8 | 5 | 1,6 | Must |
| CAT-03 scanner | 3 | 3 | 0,9 | 5 | 1,6 | Must |
| ENT-05 horas reais | 3 | 1 | 1,0 | 2 | 1,5 | Must |
| INT-06 pedido pela tela | 5 | 1 | 0,8 | 3 | 1,3 | Should |
| ORC-03 contrato automático | 3 | 1 | 0,6 | 5 | 0,4 | Could (à mão no 1º cliente) |
| ORC-04 pagamento por link | 3 | 1 | 0,5 | 8 | 0,2 | Won't na R1 |
| AGT-03 chat para cliente | 2 | 1 | 0,3 | 8 | 0,1 | Won't na R1 |

ENT-02 (3 pts) não entra no ranking: é a trava que dá efeito a CAT-03 e ENT-08. A ordem final segue as dependências, não só a nota.

### Sequência
| Ordem | Entrega | Pts | Depende de | Marco |
|---|---|---|---|---|
| 0 | Thiago responde as dúvidas 1, 2 e 3 | 0 | | |
| 1 | PLT-10, PLT-09, ENT-09, INT-07 | 4 | | |
| 2 | ORC-12 com testes (fecha INT-03) | 3 | | |
| 3 | CAT-01 | 2 | Dúvida 1 | |
| 4 | Ensaio ponta a ponta com pedido fictício (fecha AGT-01/02, INT-01/02, FEA-01, ORC-01) | 2 | 1, 2 | |
| 5 | ENT-01 travas, ORC-02, ORC-13 | 9 | 4 | **Primeira proposta** (contrato à mão, Pix manual) |
| 6 | CAT-03, ENT-08 | 7 | Dúvida 3 | |
| 7 | ENT-02, ENT-05 | 5 | 5, 6 | **Primeira entrega** |
| 8 | INT-06, PLT-02 (busca) | 5 | 1, 4 | depois da primeira venda |
| 9 | ORC-03, FEA-03, PLT-01 | 12 | 5, Dúvida 2 | depois da primeira venda |

**Até a primeira proposta: 20 pontos. Até a primeira entrega: 32 pontos.**

### O que cortar ou adiar
- **Adiar para depois da primeira venda:** ORC-03 automático (preencher no Word com a lista de campos do `orcamentista`), FEA-03, PLT-01 Git, INT-06, PLT-02.
- **Adiar para R2:** ORC-04/05 (Pix manual), ORC-06 (assinatura online), AGT-03 e tudo que abre o chat ao cliente, PLT-03 Supabase, CAT-04 a CAT-09, FEA-02 em tela, AGT-06 com 30 perguntas.
- **Reduzir:** CAT-02 só para o fluxo base de cada pedido; AGT-01/02 validados no ensaio e com 5 perguntas conferidas à mão.
- **R3 sem mudança:** vitrine, parceiros, nota fiscal automática, painel financeiro.

### Pontos ainda abertos para o refinamento (vindos do discovery e do refinamento)
- O contrato `.docx` não foi lido campo a campo; antes de ORC-03, inventariar os campos e a fonte de cada um. Placeholders do Word podem estar quebrados em vários trechos internos, o que afeta a substituição automática.
- INT-06: o formulário só cria o esqueleto do pedido ou também aciona o `analista-de-pedido`? Recomendação: só o esqueleto (custo zero de IA); o agente completa quando o Thiago pedir.
- CAT-03: rodar uma amostra do acervo antes de fechar a lista de padrões, para medir falsos positivos.
- ENT-05: granularidade por pedido com atividade/feature em texto livre; sem cronômetro na R1.
- Quantas vendas antes de mexer nos parâmetros: 3, como já estava no backlog; antes disso, só observar.

---

## D. Histórias novas e refinadas
Texto completo, com critérios dado/quando/então, está em `docs/BACKLOG.md`. Resumo:

| ID | História | Pts |
|---|---|---|
| INT-06 | Como operador, quero criar um pedido pela aba Pedidos, para não depender do chat nem editar arquivo | 3 |
| INT-07 | Como operador, quero o modelo de pedido com os dados que proposta e contrato exigem, para ter uma fonte única | 1 |
| CAT-03 (refinada) | Scanner com nó, campo e trecho mascarado; código de saída; JSON inválido não trava o lote; teste com 10 segredos plantados | 5 |
| ORC-02 (refinada) | PDF de 1 página, números vindos do pedido, versão e validade, sem ROI inventado, com anexo de suporte e aviso de IA | 5 |
| ORC-03 (refinada) | Contrato com todos os colchetes preenchidos e modelo intacto; se faltar dado, avisa qual e não gera | 5 |
| ENT-05 (reescrita) | Horas reais por pedido e por mês de suporte; ao entregar, linha no histórico de vendas com desvio % | 2 |
| ORC-12 | Economia calculada no script, piso respeitado com teto de ROI, payback líquido, desconto só nas horas `adaptar`, parâmetros em arquivo, com testes | 3 |
| ORC-13 | Aceite com versão, data, canal e evidência; sem aceite não vai para "Aprovado"; sem entrada paga não vai para "Em construção" | 2 |
| ENT-01 (restante) | Mecanismo de travas de transição, recusando com mensagem; voltar estado sempre permitido | 2 |
| ENT-08 | Fluxo de erro do n8n avisa o Thiago por e-mail; testado na entrega | 2 |
| ENT-09 | Anexo de suporte e entrega: cobertura, prazo, alteração, atraso, propriedade do fluxo, cancelamento, limite de responsabilidade | 1 |
| PLT-09 | Backup diário criptografado de `vault/` e `projetos/` fora da máquina, restauração testada | 1 |
| PLT-10 | Regra de dados mínimos nos modelos; aviso de processamento por IA de terceiro | 1 |
| PLT-11 | Estados e campos do pedido definidos num só lugar (R2) | 1 |

---

## E. Preço

### Conta da fórmula atual [Fato]
- Hora efetiva: R$ 150 x 1,25 = **R$ 187,50/h**; com `--adapted`, R$ 150/h.
- Para chegar a R$ 3.500 em complexidade média são **~18,7 h**. Com 20 h (o que diz o PED-001) a fórmula dá **R$ 3.750** e mensalidade ~R$ 520.
- Mensalidade: 3.500 x 14% = R$ 490 (o exemplo usa R$ 497).
- Payback na fórmula: 3.500 / 3.000 x 30 = 35 dias. **Ignora a mensalidade**: o líquido é 3.500 / (3.000 − 497) x 30 ≈ **42 dias**.
- O próprio exemplo tem erro de conta: "economia anual líquida R$ 36.000 − R$ 10.464". O custo do primeiro ano é 3.500 + 12 x 497 = **R$ 9.464**; a economia líquida seria R$ 26.536. Não copiar esse número.
- Teto aplicado depois do piso permite setup abaixo do piso (seção A).

### Avaliação crítica
1. **A âncora não é dado de mercado.** O PNG é um exemplo de curso (marcado "EXEMPLO", responsável Ric Neves/Flowgrammers). Serve de formato, não de prova de preço. Não tenho fonte para dizer se R$ 3.500 + R$ 497 é caro ou barato no Brasil: é **hipótese**.
2. **Mensalidade como % do setup** liga o suporte ao tamanho da construção, não ao trabalho do suporte. Pela própria hora de R$ 150, R$ 497 compram cerca de 3,3 h por mês. A pergunta certa é: o suporte de um fluxo consome menos de ~3 h/mês? Só as horas reais (ENT-05) respondem. Se o n8n rodar no seu servidor, falta somar infraestrutura.
3. **Teto de 50% da economia anual** é uma regra de bom senso para o cliente ter payback curto, não uma regra de mercado. Só conta horas economizadas; ganhos de receita (no exemplo, 30% dos leads perdidos) ficam fora e deixam o teto conservador.
4. **R$ 150/h, 25% de risco e 20% de desconto** não têm fonte. O desconto de 20% sobre todas as horas subvaloriza o trabalho de construir.
5. **Custo do chat:** a US$ 0,30 por mensagem, um pedido com 50 mensagens [Hipótese] custa ~US$ 15, pequeno perto do setup enquanto só o Thiago usa. Vira problema se o cliente usar o chat sem limite.

### Como validar (sem inventar benchmark)
1. **Teste de 3 propostas:** nos 3 a 5 primeiros prospects com escopo parecido, variar o setup (por exemplo R$ 2.500, R$ 3.500, R$ 4.500, mantendo a mensalidade) ou oferecer 3 pacotes na mesma proposta (ORC-07 feito à mão). Registrar aceite, recusa e o motivo dito. Com essa amostra é sinal, não conclusão.
2. **Horas reais (ENT-05):** depois de 3 entregas, recalcular a hora efetiva (setup / horas reais) e as horas de suporte por mês. Se a hora efetiva ficar abaixo de R$ 150, subir margem ou preço.
3. **Referências coletadas por você:** pedir 3 orçamentos reais de prestadores de automação para um escopo igual ao do exemplo, ou registrar preços públicos encontrados, sempre com fonte e data em `vault/Precos/Parametros-de-Preco.md`.
4. **Pergunta ao cliente perdido:** "O que faria você fechar?", registrada no pedido.

---

## F. Dúvidas abertas
As respostas sugeridas, com o que muda se a resposta for outra, estão no fim de `docs/BACKLOG.md`.

## Decisões que dependem do Thiago
1. **Licenças dos acervos** (dúvida 1): pedir por escrito a cada fornecedor; até lá, nada do acervo é revendido.
2. **Onde roda o n8n e o que a mensalidade cobre** (dúvida 3 + ENT-09): define preço da mensalidade, alerta e responsabilidade.
3. **Regime fiscal e forma de receber** (dúvidas 2 e 5): sem isso o contrato não fecha e a entrada não entra.
