---
id: PED-000
cliente:
status: Pedido   # Pedido | Discovery | Features | Orçado | Aprovado | Em construção | Entregue | Suporte
fluxo_base:      # path do catálogo, ou "construir do zero"
fluxo_origem:    # proprio | curso | terceiros
fluxo_licenca:   # texto da licença ou "sem resposta" (sem resposta = não revendável)
fluxo_qualidade: # testado | precisa ajuste | quebrado
complexidade:    # simples | medio | complexo
urgencia:        # baixa | media | alta
faixa_orcamento:
horas_estimadas:
horas_reais:
economia_mensal:
setup:
mensal:
validade_proposta:  # AAAA-MM-DD
prazo_dias:
versao_proposta:    # ex.: PED-001-v1
aceite_em:          # AAAA-MM-DD
aceite_canal:       # email | whatsapp | reuniao
aceite_evidencia:   # nome do arquivo em vault/Pedidos/anexos/
entrada_paga: false
comprovante:        # nome do arquivo em vault/Pedidos/anexos/
criado:             # AAAA-MM-DD
---

<!--
DADOS MÍNIMOS (LGPD): grave aqui só dado comercial do contratante e do projeto.
NÃO grave dado pessoal dos clientes finais do cliente (nomes, telefones, CPFs de leads),
senhas, tokens ou chaves de API. Dados cadastrais do contratante ficam em vault/Clientes/.
O chat envia à Anthropic o que ele lê: o que está neste arquivo pode sair da sua máquina.
-->

# PED-000 · Cliente

## Briefing
- Problema hoje:
- Impacto (horas por semana, custo):
- Ferramentas que usa:
- Gatilho:
- Precisa de IA:
- Quem opera depois:

## Matriz CSD
| Certezas | Suposições | Dúvidas |
|---|---|---|
| | | |

## ROI do cliente
- Horas por semana:
- Custo da hora:
- Economia mensal:
- Payback estimado:

## Features
| # | Feature | Origem | Critério de aceite | Horas | Fase |
|---|---|---|---|---|---|

## Orçamento
- Setup:
- Mensalidade:
- Entrada (50%):
- Premissas:

## Checklist de entrega
- [ ] Todos os critérios de aceite atendidos (qa-fluxos)
- [ ] Scanner de credenciais limpo em projetos/<cliente>/
- [ ] Testado com dados de exemplo e resultado conferido
- [ ] Tratamento de erro nas chamadas externas
- [ ] LEIA-ME com credenciais, variáveis e como testar
- [ ] Alerta de falha por e-mail ativo e testado
- [ ] Vídeo de handoff de 5 minutos gravado
- [ ] Treinamento de 30 minutos feito ou agendado
- [ ] Segunda parcela combinada
- [ ] Aprendizados registrados

## Horas reais
| Data | Horas | Feature ou atividade |
|---|---|---|

## Decisões e pedidos de alteração
-

## Histórico
-
