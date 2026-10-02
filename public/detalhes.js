/* Detalhes de um pedido: preço, aceite, entrada, checklist de entrega, horas reais e proposta em PDF. */
import { $$, api, button, clearFieldErrors, el, formField, openSheet, post, toast } from './dom.js';

const CHANNELS = [['', '—'], ['email', 'E-mail'], ['whatsapp', 'WhatsApp'], ['reuniao', 'Reunião']];
const COMPLEXITIES = [['', '—'], ['simples', 'Simples'], ['medio', 'Médio'], ['complexo', 'Complexo']];

/** Grupos de campos editáveis. A trava de cada estado exige parte deles (veja o servidor). */
const GROUPS = [
  { title: 'Preço e escopo', note: 'Depois do aceite ficam congelados: mudança vira pedido de alteração.', defs: [
    { key: 'complexidade', label: 'Complexidade', type: 'select', options: COMPLEXITIES },
    { key: 'horas_estimadas', label: 'Horas estimadas', type: 'number' },
    { key: 'economia_mensal', label: 'Economia mensal do cliente (R$)', type: 'number' },
    { key: 'setup', label: 'Setup (R$)', type: 'number' },
    { key: 'mensal', label: 'Mensalidade (R$)', type: 'number' },
    { key: 'prazo_dias', label: 'Prazo total (dias)', type: 'number' },
    { key: 'validade_proposta', label: 'Validade da proposta', type: 'date' },
  ] },
  { title: 'Aceite do cliente', note: 'Obrigatório para mover para Aprovado.', defs: [
    { key: 'versao_proposta', label: 'Versão da proposta', placeholder: 'PED-001-v1' },
    { key: 'aceite_em', label: 'Data do aceite', type: 'date' },
    { key: 'aceite_canal', label: 'Canal', type: 'select', options: CHANNELS },
    { key: 'aceite_evidencia', label: 'Arquivo da evidência', placeholder: 'aceite.png (em vault/Pedidos/anexos)' },
  ] },
  { title: 'Entrada', note: 'Obrigatória para mover para Em construção.', defs: [
    { key: 'entrada_paga', label: 'Entrada paga', type: 'checkbox' },
    { key: 'comprovante', label: 'Arquivo do comprovante', placeholder: 'pix.png (em vault/Pedidos/anexos)' },
  ] },
];

function checkboxField(id, label, checked) {
  const wrap = el('label', 'check');
  const input = el('input');
  input.type = 'checkbox';
  input.id = id;
  input.checked = checked;
  wrap.append(input, document.createTextNode(` ${label}`));
  return { wrap, input, isCheckbox: true };
}

function groupField(def, pedidoId, campos) {
  const id = `det-${pedidoId}-${def.key}`;
  if (def.type === 'checkbox') return checkboxField(id, def.label, campos[def.key] === 'true');
  return formField({ id, label: def.label, type: def.type, options: def.options, value: campos[def.key] ?? '', placeholder: def.placeholder });
}

const fieldValue = field => (field.isCheckbox ? String(field.input.checked) : field.input.value);

/** So o que mudou em relacao ao pedido: campo intocado nao e reenviado, entao valor antigo nao trava nem apaga. */
function changedFields(group, fields, campos) {
  const changed = {};
  fields.forEach(([key, field], index) => {
    const baseline = group.defs[index].type === 'checkbox' ? String(campos[key] === 'true') : (campos[key] ?? '');
    if (fieldValue(field) !== baseline) changed[key] = fieldValue(field);
  });
  return changed;
}

const localToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

function buildGroup(group, pedidoId, campos, refresh) {
  const section = el('section', 'group');
  const form = el('form', 'sheet-form');
  const fields = group.defs.map(def => [def.key, groupField(def, pedidoId, campos)]);
  fields.forEach(([, field]) => form.append(field.wrap));
  const save = el('button', 'ghost', 'Salvar');
  save.type = 'submit';
  form.append(save);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const changed = changedFields(group, fields, campos);
    if (Object.keys(changed).length === 0) {
      toast(`${group.title}: nada mudou.`);
      return;
    }
    clearFieldErrors(fields.map(([, field]) => field).filter(field => !field.isCheckbox));
    save.disabled = true;
    try {
      await post(`/api/pedidos/${pedidoId}/campos`, { campos: changed });
      toast(`${group.title}: salvo`);
      await refresh();
    } catch (error) {
      toast(error.message);
      save.disabled = false;
    }
  });
  section.append(el('h3', '', group.title), el('p', 'sheet-note', group.note), form);
  return section;
}

/** Marcar um item atualiza so o contador: redesenhar a janela inteira faria perder foco e rolagem. */
function buildChecklist(pedido) {
  const section = el('section', 'group');
  const heading = el('h3');
  const syncCount = () => {
    const boxes = $$('input[type=checkbox]', section);
    heading.textContent = `Checklist de entrega (${boxes.filter(box => box.checked).length}/${boxes.length})`;
  };
  section.append(heading, el('p', 'sheet-note', 'Todos os itens marcados são exigidos para mover para Entregue.'));
  if (!pedido.checklistItens.length) section.append(el('p', 'muted', 'Este pedido não tem checklist (modelo antigo).'));
  pedido.checklistItens.forEach(item => {
    const field = checkboxField(`chk-${item.index}`, item.label, item.done);
    field.input.addEventListener('change', async () => {
      try {
        await post(`/api/pedidos/${pedido.id}/checklist`, { index: item.index, done: field.input.checked });
      } catch (error) {
        field.input.checked = !field.input.checked;
        toast(error.message);
      }
      syncCount();
    });
    section.append(field.wrap);
  });
  syncCount();
  return section;
}

function hoursTable(rows) {
  const table = el('table', 'hours-table');
  const head = el('tr');
  ['Data', 'Horas', 'Atividade'].forEach(label => head.append(el('th', '', label)));
  table.append(head);
  rows.forEach(row => {
    const line = el('tr');
    [row.data, row.horas, row.atividade].forEach(value => line.append(el('td', '', value)));
    table.append(line);
  });
  return table;
}

function buildHours(pedido, refresh) {
  const section = el('section', 'group');
  const total = pedido.campos.horas_reais || '0';
  section.append(el('h3', '', `Horas reais (total ${total} h, orçadas ${pedido.horas || '—'} h)`),
    el('p', 'sheet-note', 'Serve para calibrar o preço depois das primeiras entregas.'));
  if (pedido.horasLinhas.length) section.append(hoursTable(pedido.horasLinhas));
  const form = el('form', 'sheet-form inline');
  const date = formField({ id: 'hr-data', label: 'Data', type: 'date', value: localToday() });
  const hours = formField({ id: 'hr-horas', label: 'Horas', type: 'number', placeholder: '2' });
  const activity = formField({ id: 'hr-atividade', label: 'Feature ou atividade', placeholder: 'Montar o fluxo de captura' });
  const add = el('button', 'ghost', 'Registrar');
  add.type = 'submit';
  form.append(date.wrap, hours.wrap, activity.wrap, add);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    add.disabled = true; // dois cliques nao podem gravar a mesma linha duas vezes
    try {
      await post(`/api/pedidos/${pedido.id}/horas`, { data: date.input.value, horas: hours.input.value, atividade: activity.input.value });
      toast('Horas registradas');
      await refresh();
    } catch (error) {
      toast(error.message);
      add.disabled = false;
    }
  });
  section.append(form);
  return section;
}

/** Gera a proposta no servidor e abre o PDF em outra aba; mostra o motivo se faltar dado. */
async function openProposta(pedidoId) {
  let response;
  try {
    response = await fetch(`/api/pedidos/${pedidoId}/proposta`);
  } catch {
    throw new Error('Não consegui falar com o servidor do Flow Hub.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `Não consegui gerar a proposta (erro ${response.status}).`);
  }
  const warnings = decodeURIComponent(response.headers.get('X-Proposta-Avisos') || '');
  const link = el('a');
  link.href = URL.createObjectURL(await response.blob());
  link.target = '_blank';
  link.rel = 'noopener';
  link.click();
  toast(warnings ? `Proposta aberta. Aviso: ${warnings}` : 'Proposta aberta em outra aba. Uma cópia ficou em vault/Pedidos/anexos.');
}

function buildHeader(pedido) {
  const bar = el('div', 'sheet-bar');
  bar.append(el('span', 'badge', pedido.status || 'sem estado'), el('strong', '', pedido.cliente || '(sem cliente)'));
  const proposta = button('primary', 'Gerar proposta (PDF)', async () => {
    proposta.disabled = true;
    try { await openProposta(pedido.id); } catch (error) { toast(error.message); } finally { proposta.disabled = false; }
  });
  const pacote = button('', 'Gerar pacote de desenvolvimento', async () => {
    pacote.disabled = true;
    try {
      const result = await post(`/api/pedidos/${pedido.id}/pacote`, {});
      toast(`Pacote gerado: ${result.features} features, ${result.tasks} tasks em ${result.pasta}`);
    } catch (error) {
      toast(error.message);
    } finally {
      pacote.disabled = false;
    }
  });
  bar.append(proposta, pacote);
  return bar;
}

export async function openDetalhes(pedidoId, onChange) {
  const body = el('div', 'sheet-body');
  const dialog = openSheet(`Pedido ${pedidoId}`, body);
  dialog.addEventListener('close', onChange);
  let renderSeq = 0;
  async function render() {
    const seq = ++renderSeq;
    try {
      const pedido = await api(`/api/pedidos/${pedidoId}`);
      if (seq !== renderSeq) return; // resposta antiga nao sobrescreve a mais nova
      body.replaceChildren(buildHeader(pedido), ...GROUPS.map(group => buildGroup(group, pedido.id, pedido.campos, render)),
        buildChecklist(pedido), buildHours(pedido, render));
    } catch (error) {
      body.replaceChildren(el('p', 'error-msg', error.message));
    }
  }
  await render();
}
