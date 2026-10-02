---
name: roteamento
description: Decide qual agente, skill e modelo usar para um pedido do Flow Hub. Use no começo de qualquer tarefa que não seja uma pergunta simples.
---

# Roteamento

Antes de executar, decida o que usar. Objetivo: qualidade máxima com o menor custo de token e tempo.

## 1. Classificar pelo sinal no pedido
| Sinais | Agente ou skill |
|---|---|
| "tenho um cliente", "ele quer", problema descrito | `analista-de-pedido` |
| "tem algum fluxo para", "existe pronto" | `flow-consultant` |
| "quebra em features", "o que precisa fazer" | `quebra-de-features` (skill `quebra-de-features`) |
| "quanto cobrar", "proposta", "contrato" | `orcamentista` (skill `orcamento-proposta`) |
| "adapta", "monta o fluxo", "constrói" | `construtor-n8n` |
| "pode entregar", "revisa o fluxo" | `qa-fluxos` (skill `entrega-checklist`) |

## 2. Escolher o modelo
- Pedido novo, vago, caro (acima de R$ 6.000) ou com IA e dado sensível: Opus.
- Quebrar, construir, revisar: Sonnet.
- Preencher modelo, formatar, calcular com script: Haiku.

## 3. Usar agente só quando compensa
Pedido simples de busca: responda direto com `python flowhub/search.py`. Acione agentes quando há várias etapas ou quando o resultado vai para o vault ou para o cliente. Dispare em paralelo o que for independente.

## 4. Carregar contexto
Leia `vault/Agora/Contexto-Ativo.md` e, se o pedido já existe, `vault/Pedidos/PED-NNN-*.md`. Procure no catálogo antes de construir do zero.
