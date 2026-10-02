---
name: quebra-de-features
description: Método para dividir um pedido de automação em features com critério de aceite, horas e fases. Use ao transformar briefing em lista de trabalho.
---

# Quebra em features

## Regras
1. Cada feature é "verbo + objeto" e entrega algo observável.
2. Critério de aceite em uma frase testável: dado, quando, então.
3. Horas em 1, 2, 3, 5 ou 8. Mais que 8 deve ser dividida.
4. Origem: `adaptar` (existe no fluxo base) ou `construir`. O desconto de reaproveitamento só vale para `adaptar`.
5. Fases: Diagnóstico (3 dias), PoC (7 dias), Go-live (21 dias). A PoC deve provar o fluxo principal com dados reais ou de exemplo.
6. Toda dependência do cliente (acesso, conta, dado) vira uma linha própria, com dono.

## Formato da tabela
| # | Feature | Origem | Critério de aceite | Horas | Fase |
|---|---|---|---|---|---|

## Exemplo
| 1 | Capturar lead do formulário | adaptar | Dado um envio, quando o fluxo roda, então o lead aparece na planilha em até 1 minuto | 2 | PoC |
| 2 | Enviar mensagem de boas-vindas no WhatsApp | construir | Dado um lead novo, então ele recebe a mensagem em até 2 minutos | 5 | PoC |

## Escopo fechado
O que não está na tabela não será entregue. Pedido extra vira pedido de alteração, cobrado por hora.
