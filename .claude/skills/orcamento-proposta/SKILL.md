---
name: orcamento-proposta
description: Como orçar um pedido de automação e montar proposta 1-pager e contrato. Use quando o pedido tem horas estimadas e o Thiago pergunta quanto cobrar.
---

# Orçamento e proposta

## Cálculo
Sempre pelo script, nunca de cabeça:
`python flowhub/quote.py --complexity <simples|medio|complexo> --hours <total> [--adapt-hours <n>] [--client-hours-week <h> --client-hourly-cost <R$>]`

Como o preço é formado: horas x valor da hora x (1 + margem de risco), com desconto de reaproveitamento só nas horas de adaptação (`--adapt-hours`), piso por complexidade (o piso sempre vence) e teto de 50% da economia anual do cliente. A mensalidade é uma fração do setup, com mínimo. O payback é líquido da mensalidade. Todos os parâmetros estão em `flowhub/parametros.json`.

## Condições padrão
- Entrada de 50%, restante na entrega.
- Escopo fechado, 2 rodadas de ajuste, mudanças cobradas por hora.
- Licenças e APIs de terceiros por conta do cliente.
- Mensalidade cobre monitoramento, correções e relatório mensal.

## Gerar o PDF
Pelo painel (Pedidos > Detalhes > Gerar proposta) ou `python flowhub/proposta.py vault/Pedidos/PED-NNN-*.md --out proposta.pdf`. Ele recusa se faltar `setup` ou `mensal`, nunca inventa ROI e guarda uma cópia versionada em `vault/Pedidos/anexos/`. O PDF tem identidade própria; os modelos da Flowgrammers servem de referência, não de arquivo final.

## Estrutura da proposta 1-pager
Problema (hoje, impacto, efeito colateral) → Solução (automação, entrega, segurança) → Escopo e entregáveis → Diferenciais → Prazo (3, 7 e 21 dias) → Investimento (setup, mensalidade) → ROI (economia mensal, payback, economia anual líquida) → Próximos passos.

Modelo visual em `_raw/docs/proposta-1pager/`.

## Contrato
Modelo em `_raw/docs/Cópia de TEMPLATE - Modelo de Contrato .docx`. Liste os campos entre colchetes que faltam preencher; não invente dados do cliente.

## Antes de enviar
O Thiago aprova preço e texto. Nada é enviado ao cliente sem o OK dele.
