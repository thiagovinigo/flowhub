/* Formulário "Novo pedido" (INT-06): cria vault/Pedidos/PED-NNN-<cliente>.md sem chamar o chat (custo zero de IA). */
import { clearFieldErrors, el, formField, openSheet, post, showFieldError, toast } from './dom.js';

const URGENCIES = [['baixa', 'Baixa'], ['media', 'Média'], ['alta', 'Alta']];

function buildFields() {
  return {
    cliente: formField({ id: 'np-cliente', label: 'Cliente (contratante)', placeholder: 'Nome da empresa' }),
    problema: formField({ id: 'np-problema', label: 'Problema hoje', type: 'textarea', placeholder: 'O que é feito à mão e como atrapalha' }),
    horasSemana: formField({ id: 'np-horas', label: 'Horas por semana gastas nisso', type: 'number', placeholder: '15' }),
    custoHora: formField({ id: 'np-custo', label: 'Custo da hora do cliente (R$)', type: 'number', placeholder: '50' }),
    ferramentas: formField({ id: 'np-ferramentas', label: 'Ferramentas que usa', placeholder: 'Instagram, Google Sheets, WhatsApp' }),
    gatilho: formField({ id: 'np-gatilho', label: 'O que dispara a automação', placeholder: 'Formulário, mensagem, horário…' }),
    urgencia: formField({ id: 'np-urgencia', label: 'Urgência', type: 'select', options: URGENCIES, value: 'media' }),
    faixaOrcamento: formField({ id: 'np-faixa', label: 'Faixa de orçamento (opcional)', placeholder: 'R$ 3 a 5 mil' }),
    quemOpera: formField({ id: 'np-opera', label: 'Quem opera depois', placeholder: 'Analista de marketing' }),
  };
}

function readForm(fields) {
  const text = key => fields[key].input.value;
  return {
    cliente: text('cliente'), problema: text('problema'), horasSemana: Number(text('horasSemana')),
    custoHora: Number(text('custoHora')), ferramentas: text('ferramentas'), gatilho: text('gatilho'),
    urgencia: text('urgencia'), faixaOrcamento: text('faixaOrcamento'), quemOpera: text('quemOpera'),
  };
}

async function submit(fields, dialog, saveButton, onCreated) {
  clearFieldErrors(Object.values(fields));
  saveButton.disabled = true;
  try {
    const created = await post('/api/pedidos', readForm(fields));
    dialog.close();
    toast(`${created.id} criado em Pedido. Abra “Detalhes” para completar.`);
    onCreated(created.id);
  } catch (error) {
    if (error.field && fields[error.field]) showFieldError(fields[error.field], error.message);
    else toast(error.message);
  } finally {
    saveButton.disabled = false;
  }
}

export function openNovoPedido(onCreated) {
  const fields = buildFields();
  const form = el('form', 'sheet-form');
  form.noValidate = true;
  Object.values(fields).forEach(field => form.append(field.wrap));
  const saveButton = el('button', 'primary', 'Criar pedido');
  saveButton.type = 'submit';
  const actions = el('div', 'sheet-actions');
  actions.append(saveButton);
  form.append(actions);
  const dialog = openSheet('Novo pedido', el('p', 'sheet-note', 'Grave só dado comercial do contratante. Nada de dado pessoal dos clientes finais dele, senhas ou chaves.'), form);
  form.addEventListener('submit', event => {
    event.preventDefault();
    submit(fields, dialog, saveButton, onCreated);
  });
  fields.cliente.input.focus();
}
