---
name: intake-briefing
description: Entrevista curta para abrir um pedido de automação e montar briefing, matriz CSD e ROI. Use quando o Thiago relatar um cliente ou problema novo.
---

# Intake e briefing

## Perguntas (no máximo 5, uma rodada)
1. Que processo manual existe hoje e quantas horas por semana consome?
2. O que dispara a automação?
3. Quais ferramentas o cliente já usa?
4. Precisa de IA ou só mover dados?
5. Quem opera depois e o que acontece se falhar?

Se o relato já responde alguma, não repita.

## Saídas
- **Briefing:** problema, impacto, ferramentas, gatilho, quem opera.
- **Matriz CSD:** o que é certeza, o que é suposição, o que é dúvida.
- **ROI:** economia mensal = horas por semana x 4 x custo da hora. Payback = setup / economia mensal x 30 dias.
- Arquivo `vault/Pedidos/PED-NNN-<cliente>.md` com `status: Discovery`.

## Exemplo do material da Flowgrammers
Hoje: leads do Instagram copiados à mão, 15 horas por semana a R$ 50 por hora = R$ 3.000 por mês perdidos, 30% dos leads não entram no CRM. Solução com setup de R$ 3.500 e suporte de R$ 497 por mês, payback de cerca de 35 dias.
