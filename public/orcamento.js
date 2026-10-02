/* Aba Orçamento: chama flowhub/quote.py pelo servidor e mostra a proposta resumida (ORC-12). */
import { $, brl, button, copyText, cxLabel, el, post, stateBox, toNumber } from './dom.js';

let quoteSeq = 0;

function proposalLine(label, value, why, extra = '') {
  const box = el('div', 'line');
  box.append(el('dt', '', label), el('dd', extra, value));
  if (why) box.append(el('p', 'why', why));
  return box;
}

function quoteInput() {
  const saving = toNumber($('#saving').value);
  const week = toNumber($('#clientWeek').value);
  const cost = toNumber($('#clientCost').value);
  let client = {};
  if (saving) client = { clientSaving: saving };
  else if (week || cost) client = { clientHoursWeek: week, clientHourlyCost: cost };
  return {
    complexity: $('#complexity').value,
    hours: Number($('#hours').value),
    adaptHours: toNumber($('#adaptHours').value) ?? 0,
    ...client,
  };
}

function inputProblem(input) {
  if (!(input.hours > 0)) return 'Informe um número de horas maior que zero.';
  if (input.adaptHours > input.hours) return 'As horas de adaptação não podem passar do total de horas.';
  if ((input.clientHoursWeek || input.clientHourlyCost) && !(input.clientHoursWeek && input.clientHourlyCost)) {
    return 'Para calcular a economia do cliente, preencha as horas por semana e o custo da hora (ou a economia mensal direta).';
  }
  return '';
}

function explanation(quote, input) {
  const notes = [`Base: complexidade ${cxLabel(input.complexity)}, ${input.hours} h de entrega, sendo ${input.adaptHours} h de adaptação de fluxo pronto (só essas recebem o desconto de reaproveitamento).`];
  notes.push(`Equivale a ${brl(quote.setup / input.hours)} por hora entregue.`);
  if (!quote.client_saving) notes.push('Sem a economia mensal do cliente, o payback e o teto de ROI não são calculados.');
  notes.push(`Parâmetros: versão ${quote.params_version} (arquivo flowhub/parametros.json). Proposta válida por ${quote.valid_days} dias.`);
  return notes;
}

function roiLines(quote) {
  if (!quote.client_saving) return [];
  const payback = quote.payback_days === null
    ? proposalLine('Payback líquido', 'não se paga', 'A mensalidade consome toda a economia do cliente.')
    : proposalLine('Payback líquido', `${quote.payback_days} dias`, `Já descontada a mensalidade. Bruto, sem descontá-la: ${quote.payback_gross_days} dias.`);
  return [
    proposalLine('Economia mensal do cliente', brl(quote.client_saving), 'Horas por semana x 4 x custo da hora, calculado pelo script.', 'money'),
    payback,
    ...(quote.annual_net_saving === null ? [] : [proposalLine('Economia líquida no 1º ano', brl(quote.annual_net_saving), 'Economia de 12 meses menos setup e 12 mensalidades.', 'money')]),
  ];
}

function summaryText(quote, input) {
  const lines = [
    `Setup (único): ${brl(quote.setup)}`, `Entrada na aprovação: ${brl(quote.down_payment)}`,
    `Saldo na entrega: ${brl(quote.setup - quote.down_payment)}`, `Suporte mensal: ${brl(quote.monthly)}`,
  ];
  if (quote.payback_days != null) lines.push(`Payback líquido: ${quote.payback_days} dias`);
  return `${lines.join('\n')}\n(${input.complexity}, ${input.hours} h)`;
}

function renderProposal(quote, input) {
  const sheet = el('article', 'proposal');
  const head = el('div', 'proposal-head');
  const total = el('div');
  total.append(el('small', '', 'Setup (pagamento único)'), el('strong', '', brl(quote.setup)));
  head.append(total, el('span', '', `Proposta resumida · ${cxLabel(input.complexity)} · ${input.hours} h`));

  const share = Math.round((quote.down_payment / quote.setup) * 100);
  const lines = el('dl', 'lines');
  lines.append(
    proposalLine('Entrada', brl(quote.down_payment), `${share}% do setup, paga na aprovação.`, 'money'),
    proposalLine('Saldo na entrega', brl(quote.setup - quote.down_payment), 'Restante do setup, na entrega validada.', 'money'),
    proposalLine('Suporte mensal', brl(quote.monthly), 'Recorrência após a entrega.', 'money'),
    ...roiLines(quote),
  );

  const how = el('div', 'how');
  const list = el('ul');
  explanation(quote, input).forEach(text => list.append(el('li', '', text)));
  how.append(...quote.warnings.map(text => el('p', 'note', text)), el('h2', '', 'Como o número foi formado'), list);

  const actions = el('div', 'proposal-actions');
  actions.append(button('ghost', 'Copiar resumo', () => copyText(summaryText(quote, input), 'Resumo copiado')));
  sheet.append(head, lines, how, actions);
  return sheet;
}

export async function calculateQuote(event) {
  if (event) event.preventDefault();
  const seq = ++quoteSeq;
  const input = quoteInput();
  const box = $('#quote-result');
  const problem = inputProblem(input);
  if (problem) {
    box.replaceChildren(stateBox('error', 'Confira os dados', problem));
    return;
  }
  try {
    const quote = await post('/api/quote', input);
    if (seq === quoteSeq) box.replaceChildren(renderProposal(quote, input));
  } catch (error) {
    if (seq === quoteSeq) box.replaceChildren(stateBox('error', 'Não consegui calcular o orçamento', error.message));
  }
}

export function initOrcamento() {
  $('#quote-form').addEventListener('submit', calculateQuote);
}
