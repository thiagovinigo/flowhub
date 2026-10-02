/* Utilitários compartilhados pelos módulos do painel. Nada aqui conhece telas específicas. */
export const STATUSES = ['Pedido', 'Discovery', 'Features', 'Orçado', 'Aprovado', 'Em construção', 'Entregue', 'Suporte'];
export const PEDIDO_ID_RE = /^PED-\d{3,}$/;
const TOAST_MS = 3500;

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

export const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

export const button = (className, text, onClick) => {
  const node = el('button', className, text);
  node.type = 'button';
  if (onClick) node.addEventListener('click', onClick);
  return node;
};

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
export const toNumber = value => (value === '' || value == null || Number.isNaN(Number(value)) ? null : Number(value));
export const brl = value => (toNumber(value) === null ? '—' : money.format(Number(value)));
export const splitList = text => String(text || '').split(',').map(part => part.trim()).filter(Boolean);

export async function api(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error('Não consegui falar com o servidor do Flow Hub. Confira se ele está ligado (Ligar-FlowHub.bat) e tente de novo.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `O servidor respondeu com erro ${response.status}.`);
    error.field = data.field; // qual campo do formulario corrigir, quando o servidor sabe
    throw error;
  }
  return data;
}

export const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

/** Aviso curto. Usa popover para ficar acima das janelas de dialogo (que cobrem o resto da pagina). */
export function toast(message) {
  const box = $('#toast');
  const usesPopover = typeof box.showPopover === 'function';
  box.textContent = message;
  if (usesPopover) {
    if (!box.matches(':popover-open')) box.showPopover();
  } else {
    box.hidden = false;
  }
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    if (usesPopover) { if (box.matches(':popover-open')) box.hidePopover(); } else box.hidden = true;
  }, TOAST_MS);
}

export const cxLabel = value => (value === 'medio' ? 'médio' : value);

export function stateBox(kind, title, text, action) {
  const box = el('div', `state ${kind}`);
  box.append(el('h3', '', title), el('p', '', text));
  if (action) box.append(action);
  return box;
}

/** Campo de formulario com rotulo, controle e area de erro ligados por aria-describedby. */
export function formField({ id, label, type = 'text', options = [], value = '', placeholder = '' }) {
  const wrap = el('div', 'field');
  const labelNode = el('label', '', label);
  labelNode.htmlFor = id;
  let input;
  if (type === 'select') {
    input = el('select');
    options.forEach(([optionValue, text]) => input.append(new Option(text, optionValue)));
    // Valor digitado a mao que nao esta na lista continua visivel (e nao vira "—" nem some ao salvar).
    if (value && !options.some(([optionValue]) => optionValue === value)) input.append(new Option(`${value} (valor antigo)`, value));
  } else if (type === 'textarea') {
    input = el('textarea');
    input.rows = 3;
  } else {
    input = el('input');
    input.type = type;
    if (type === 'number') { input.step = 'any'; input.min = '0'; }
  }
  input.id = id;
  input.value = value ?? '';
  if (placeholder) input.placeholder = placeholder;
  const message = el('p', 'field-error');
  message.id = `${id}-error`;
  message.hidden = true;
  input.setAttribute('aria-describedby', message.id);
  wrap.append(labelNode, input, message);
  return { wrap, input, message };
}

export function showFieldError(field, text) {
  field.message.textContent = text;
  field.message.hidden = false;
  field.input.setAttribute('aria-invalid', 'true');
  field.input.focus();
}

export function clearFieldErrors(fields) {
  fields.forEach(field => {
    field.message.hidden = true;
    field.input.removeAttribute('aria-invalid');
  });
}

let sheetCount = 0;

/** Abre uma janela de dialogo modal (Esc fecha) e a remove do DOM ao fechar. */
export function openSheet(title, ...children) {
  const dialog = el('dialog', 'sheet');
  const headingId = `sheet-title-${++sheetCount}`;
  dialog.setAttribute('aria-labelledby', headingId);
  const head = el('div', 'sheet-head');
  const heading = el('h2', '', title);
  heading.id = headingId;
  head.append(heading, button('ghost small', 'Fechar', () => dialog.close()));
  dialog.append(head, ...children);
  dialog.addEventListener('close', () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}

export async function copyText(text, okMessage = 'Copiado') {
  try {
    await navigator.clipboard.writeText(text);
    toast(okMessage);
  } catch {
    toast('Não foi possível copiar. Selecione o texto e use Ctrl+C.');
  }
}
