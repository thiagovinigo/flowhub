# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# FLOW HUB: escritório de automações n8n

Braço direito do Thiago para vender automações. O ciclo inteiro: o cliente descreve o problema, eu acho o melhor fluxo pronto (ou entrevisto para montar um), quebro o pedido em features, calculo a cobrança, construo no Claude Code, entrego e mantenho. Projeto em português. É um repositório git local com `origin` em `thiagovinigo/flowhub` (público): nunca versione `_raw/`, `projetos/`, dados reais do `vault/`, `.env` nem o catálogo gerado (o `.gitignore` já cobre). Testes: `npm run test:all` (65 em Node e 58 em Python); faltam testes de `indexer.py` e `search.py`.

## Como cada pedido é executado

| Nível | Quando | Padrão |
|---|---|---|
| BALCÃO | Dúvida rápida ou busca de fluxo | `flow-consultant` responde direto |
| PEDIDO | Cliente com problema claro | `analista-de-pedido` → `quebra-de-features` → `orcamentista` |
| ESTRATÉGICO | Pedido vago, acima de R$ 6.000, ou IA com dado sensível | pedido completo + `security-reviewer` antes de orçar; usar Opus |
| PROJETO | Construir e entregar um fluxo aprovado | `construtor-n8n` → `qa-fluxos` → `security-reviewer` → checklist de entrega |

Estados de um pedido (kanban, campo `status` em `vault/Pedidos/`):
`Pedido → Discovery → Features → Orçado → Aprovado → Em construção → Entregue → Suporte`

### Quem faz o quê
| Agente | Faz | Modelo |
|---|---|---|
| `flow-consultant` | Busca no catálogo ou entrevista; recomenda fluxo | sonnet |
| `analista-de-pedido` | Briefing, matriz CSD, ROI do cliente; abre o pedido no vault | sonnet |
| `quebra-de-features` | Features com critério de aceite, horas e fases | sonnet |
| `orcamentista` | Orçamento via `quote.py`, texto da proposta e dados do contrato | haiku |
| `construtor-n8n` | Copia o fluxo para `projetos/<cliente>/`, sanitiza e adapta | sonnet |
| `qa-fluxos` | Valida o fluxo adaptado contra os critérios de aceite | sonnet |

Regra de modelo: Opus só em pedido estratégico; Sonnet pensa e valida; Haiku executa o mecânico (formatar, preencher modelo). Dispare em paralelo o que não depende um do outro (por exemplo, `analista-de-pedido` e uma segunda busca de fluxo).

Atalhos de despacho:
```
"Tenho um cliente que..."     → analista-de-pedido (+ flow-consultant em paralelo)
"Quanto cobrar?"              → orcamentista
"Quebra isso em features"     → quebra-de-features
"Adapta esse fluxo"           → construtor-n8n → qa-fluxos
"Pode entregar?"              → qa-fluxos + checklist (skill entrega-checklist)
```

## Memória (vault/)
- `vault/Agora/Contexto-Ativo.md`: pedido em andamento e próximos passos.
- `vault/Pedidos/PED-NNN-<cliente>.md`: um arquivo por pedido (modelo em `_modelo-pedido.md`). É a fonte de verdade do estado, do escopo e do preço.
- `vault/Clientes/`: um arquivo por cliente (modelo em `_modelo-cliente.md`).
- `vault/Precos/Parametros-de-Preco.md`: como calibrar o preço e o histórico de vendas reais.
- `vault/Memoria/Aprendizados.md`: depois de cada entrega, registrar o que funcionou, o que evitar e horas reais contra as orçadas.

Nunca apagar arquivos do vault. Atualize o pedido a cada mudança de estado.

## Portões de qualidade
| Portão | Pergunta | Nível |
|---|---|---|
| Aderência | Cada critério de aceite do pedido foi atendido? | todos |
| Segurança | Há token, e-mail, ID de credencial ou webhook de outro cliente no JSON? | PROJETO |
| Teste | Rodou com dados de exemplo e o resultado foi conferido? | PROJETO |
| Preço | Está acima do piso e abaixo do teto de 50% da economia anual do cliente? | PEDIDO+ |
| Escopo | O escopo aprovado está congelado e mudanças viraram pedido de alteração? | Aprovado+ |

## Regras de operação
1. Português. Direto, sem preâmbulo.
2. Nunca invente fluxo: cite sempre o `path` do catálogo. Se nada serve, diga e proponha construir do zero.
3. Nunca edite `_raw/`. O trabalho do cliente vive em `projetos/<cliente>/`.
4. Ações que atingem terceiros exigem o OK do Thiago antes: enviar proposta ou mensagem a cliente, gerar cobrança, instalar no n8n do cliente.
5. Credenciais nunca vão para arquivo versionado nem para o vault.
6. Antes de construir do zero, procure no catálogo.
7. Ao fechar uma entrega, atualize `vault/Memoria/Aprendizados.md`.

Fim de cada entrega, neste formato:
```
ENTREGUE:  o que foi feito
VALIDADO:  o que foi conferido e como
PRÓXIMO:   passo lógico seguinte
APRENDIDO: o que foi salvo na memória
```

## Comandos
- Reindexar (recria `flowhub/catalog.db`): `python flowhub/indexer.py`
- Buscar: `python flowhub/search.py "whatsapp imobiliaria" --limit 5 [--integration gmail] [--ai] [--max-complexity medio] [--json]`
- Orçar: `python flowhub/quote.py --complexity medio --hours 20 [--adapt-hours 10] [--client-hours-week 15 --client-hourly-cost 50]` (parâmetros em `flowhub/parametros.json`)
- Procurar segredo em fluxos: `python flowhub/scan.py projetos/<cliente>` (código 0 = limpo; saída sempre mascarada)
- Proposta em PDF: `python flowhub/proposta.py vault/Pedidos/PED-NNN-*.md --out proposta.pdf` (ou botão em Pedidos > Detalhes)
- Pacote de desenvolvimento: `python flowhub/pacote.py PED-NNN` (ou botão em Detalhes) grava `projetos/<cliente>/pacote/` com `BACKLOG-DEV.md` (épicos > features > histórias > tasks com prompt por agente), `tarefas.json`, a explicação nó a nó dos fluxos de referência e os modelos de `templates/` (fluxos n8n anotados e modelos de entrega). Explicar qualquer fluxo: `python flowhub/explicar.py fluxo.json`. Os modelos não foram executados num n8n real.

- Painel web local: `Ligar-FlowHub.bat` (ou `npm start`), abre em `http://127.0.0.1:3100`
- Testes: `npm test` (Node `node:test`), `npm run test:py` (Python `unittest`), `npm run test:all` (os dois). Nenhuma dependência além do PyMuPDF (`fitz`) usado na proposta

Python só usa stdlib (3.12); o servidor Node também não tem dependências.

## Painel (server/ e public/)
- `server/server.js` ouve só em `127.0.0.1` e recusa `Host` diferente de `127.0.0.1`/`localhost`. Rotas: `/api/health`, `/api/search`, `/api/quote`, `/api/chat`, `GET|POST /api/pedidos`, `GET /api/pedidos/:id`, `POST /api/pedidos/:id/{status,campos,checklist,horas}` e `GET /api/pedidos/:id/proposta` (PDF). Arquivos estáticos: qualquer `*.js|css|html` solto na raiz de `public/` (sem barras no nome).
- Pedidos (`server/lib/`): `frontmatter.js` e `secoes.js` leem e trocam só o cabeçalho e as seções (Histórico, Checklist de entrega, Horas reais) sem tocar no resto do arquivo; `transicoes.js` guarda as travas (Aprovado exige aceite completo, Em construção exige entrada paga com comprovante, Entregue exige checklist inteiro, e valem também para quem pula estados; voltar é sempre livre); `pedidos.js` aplica as regras, congela preço e escopo depois do aceite e registra no Histórico; `pedido-novo.js` cria o arquivo a partir de `vault/Pedidos/_modelo-pedido.md` reservando o número com um arquivo `.reserva` (só o nome do arquivo não impede dois pedidos simultâneos de pegarem o mesmo número). Um teste confere que o pedido criado tem os mesmos campos e seções do modelo: ao mudar o modelo, rode `npm test`.
- Front (`public/`): `app.js` (abas, chat, catálogo, kanban), `dom.js` (utilitários, formulários, janela de diálogo, aviso em popover para ficar acima dos diálogos), `novo-pedido.js`, `detalhes.js`, `orcamento.js`. `dialog.close()` não dispara o evento `close` em aba em segundo plano; é do navegador, não do painel.
- `/api/search` e `/api/quote` chamam `flowhub/search.py` e `flowhub/quote.py` (com `--json`) por `spawn` sem shell; os argumentos são montados e validados em `server/lib/validate.js` (o `--` antes do texto impede que ele vire opção).
- `/api/chat` chama o `claude.exe` em modo `-p` na raiz do projeto, com `--output-format json` e `--resume <session_id>` para manter a conversa. No Windows `claude` é um `.cmd`, que o Node não executa sem shell, por isso `findClaude` (`server/lib/run.js`) acha o `.exe` dentro do pacote npm; use `FLOWHUB_CLAUDE` para forçar o caminho.
- Chat (`chatArgs` em `server/server.js`): `--setting-sources project` (não herda permissões, hooks nem modelo globais do usuário), `--tools` limitado a Read/Grep/Glob/Write/Edit/Bash (sem PowerShell), `--model` fixo em `sonnet` (`FLOWHUB_MODEL` muda). Sem o `--model`, o CLI cai no modelo padrão, que custou cerca de 9 vezes mais por mensagem. Gravação só em `vault/Pedidos`, `Clientes`, `Agora` e `Memoria` (nunca `Precos`); leitura do projeto é livre, inclusive `_raw/`, porque o consultor abre o JSON do fluxo. As regras só casam com o comando limpo (`python flowhub/search.py "..."`); `cd ... &&` ou variáveis de ambiente são negados, por isso o `CHAT_HINT`. Uma conversa por vez (429 se houver outra).
- Defesas do servidor: `Host` com porta exata; todo POST exige `Content-Type: application/json` e `Origin` do próprio painel (`checkPostRequest`), o que impede que outro site aberto no navegador dispare o chat ou mude pedidos; erros inesperados vão para o log e o cliente recebe mensagem genérica. Lições das auditorias, cobertas por testes: (1) o nome do campo vem do cliente, então `FIELD_RULES` é consultado com `Object.hasOwn` (a chave `constructor` já burlou todas as travas) e valores do cabeçalho não aceitam quebra de linha, inclusive Unicode (U+2028, U+0085), nem `#`; (2) `String.replace` com texto do usuário usa função, nunca string (`$'` no nome do cliente duplicava o arquivo); (3) toda gravação de pedido passa por `withPedidoLock` + escrita atômica (arquivo `.tmp` + rename); (4) o preço fica congelado enquanto existir `aceite_em`, e o aceite não pode ser apagado a partir de Aprovado; (5) `GET /proposta` grava arquivo, então exige `Sec-Fetch-Site` same-origin ou none e gera um arquivo novo a cada vez (a cópia enviada ao cliente nunca é sobrescrita); (6) a regex de e-mail do scanner só roda se houver `@` e em no máximo 20 mil caracteres por texto; (7) o scanner lê lista de fluxos e vários fluxos por arquivo, e JSON sem fluxo conta como inválido, nunca como limpo; (8) para escrever caractere Unicode especial em regex, monte com `String.fromCharCode`: a ferramenta de edição converte ` ` no caractere de verdade e quebra a sintaxe.
- O kanban lê o cabeçalho de `vault/Pedidos/PED-NNN-*.md` (`server/lib/pedidos.js`) e só reescreve a linha `status:`, preservando o comentário. `vault/Pedidos/PED-001-agencia-vitrine-digital.md` é um exemplo (`exemplo: true`): apague quando entrar um pedido real.
- Para testar a API com acentos, use Node/`fetch`; `curl` no Git Bash corrompe os caracteres.

## Arquitetura do catálogo
1. `_raw/src1..src9/`: zips extraídos de `C:\Users\User\Downloads`. `_raw/docs/` guarda o modelo de contrato `.docx` e a proposta 1-pager (PNG).
2. `flowhub/indexer.py` lê todo `.json` de `_raw/src*`, extrai gatilhos, integrações, credenciais, uso de IA (nodes `langchain`) e notas (`stickyNote`), e grava em `flows` + FTS5 `flows_fts`. Duplicatas saem por SHA1 do esqueleto `(type, name, parameters)`; `copies` conta as cópias. `src1`≡`src5` e `src2`≡`src3`.
3. `flowhub/search.py` consulta o FTS5 (bm25: nome 6, integrações 3, categoria 2, notas 1) e filtra em Python.

Cada fluxo indexado ganha um **perfil** (`flowhub/perfil.py`, coluna `profile` em JSON): `tem` (o que o fluxo já tem), `por_que` (por que usar: o "O que faz" das notas do autor, a categoria) e `falta` (o que criar para entregar, com `tipo` `cliente` fornece, `limpar`, `criar` ou `adaptar`), mais `esforco` (baixo, medio, alto). É calculado sem IA a partir de nós, credenciais, gatilhos e notas; cada item de `falta` aponta para algo que existe ou não existe no JSON. O `search.py --json` devolve `profile` e o painel mostra os três blocos em cada cartão. Mudou `perfil.py`? Rode `python flowhub/indexer.py` (o catálogo guarda o perfil pronto).

A complexidade (`simples`/`medio`/`complexo`) é heurística: nº de nodes + 8 se usa IA. As constantes de preço de `quote.py` são hipóteses calibradas no exemplo de proposta (R$ 3.500 setup + R$ 497/mês).

## Armadilhas do Windows e dos dados
- Caminhos de `_raw` passam de 260 caracteres e têm nomes Unicode decompostos: toda leitura usa o prefixo `\\?\` (`read_documents` em `indexer.py`).
- Extraia zips com Python `zipfile`; `Expand-Archive` falha nos nomes com emoji.
- Alguns JSONs têm vários workflows ou lixo depois do primeiro; o indexador usa `raw_decode` em laço.
- Para imprimir emoji no terminal, use `PYTHONIOENCODING=utf-8`.

## Documentos
- `docs/BACKLOG.md`: backlog completo (7 épicos, 3 releases).
- `docs/guia-repositorios.html`: guia dos 8 repositórios de skills e agentes.
