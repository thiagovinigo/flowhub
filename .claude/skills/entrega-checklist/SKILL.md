---
name: entrega-checklist
description: Checklist de entrega de um fluxo n8n ao cliente. Use antes de marcar um pedido como Entregue.
---

# Checklist de entrega

O pedido só vai para `Entregue` com todos os itens marcados. O kanban recusa a mudança se faltar algum: a mesma lista está na seção "Checklist de entrega" de cada pedido e pode ser marcada em Pedidos > Detalhes.

- [ ] Todos os critérios de aceite do pedido foram atendidos (`qa-fluxos`).
- [ ] `python flowhub/scan.py projetos/<cliente>` sai com código 0 (nenhum token, e-mail, ID de credencial, webhook ou ID de arquivo de outra pessoa) e o `LEIA-ME.md` foi relido à mão.
- [ ] Testado com dados de exemplo; resultado conferido.
- [ ] Tratamento de erro ou alerta nas chamadas externas.
- [ ] `projetos/<cliente>/LEIA-ME.md` com credenciais necessárias, variáveis e como testar.
- [ ] Vídeo de handoff de 5 minutos gravado.
- [ ] Treinamento de 30 minutos agendado ou feito.
- [ ] Alertas de falha por e-mail ativos.
- [ ] Segunda parcela do pagamento combinada.
- [ ] `vault/Memoria/Aprendizados.md` atualizado: horas reais contra orçadas, o que funcionou, o que evitar.

Instalar no n8n do cliente, enviar material ou cobrar são ações externas: só com o OK do Thiago.
