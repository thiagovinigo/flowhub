import { $, $$, STATUSES, PEDIDO_ID_RE, api, brl, button, copyText, cxLabel, el, post, splitList, stateBox, toNumber, toast } from './dom.js';
import { openDetalhes } from './detalhes.js';
import { openNovoPedido } from './novo-pedido.js';
import { profileBlocks } from './perfil.js';
import { calculateQuote, initOrcamento } from './orcamento.js';

const CLOSED_STATUSES = ['Entregue', 'Suporte'];
const STARTERS = [
  'Tenho um cliente de imobiliária que perde leads que chegam pelo WhatsApp fora do horário.',
  'Existe fluxo pronto para gerar proposta comercial a partir de um formulário?',
  'Quanto cobrar por um fluxo médio de 20 horas que parte de um fluxo pronto?',
];
const SEARCH_LIMIT = 20;
const KEY_INTEGRATIONS = 5;
const COMPLEXITY_ORDER = { simples: 0, medio: 1, complexo: 2 };
const VIEW_KEY = 'flowhub-view';
const THEME_KEY = 'flowhub-theme';
const THEMES = ['system', 'light', 'dark'];
/* Nós utilitários do n8n: não ajudam a decidir qual fluxo usar. */
const GENERIC_NODES = new Set([
  'limit', 'sort', 'set', 'if', 'switch', 'merge', 'code', 'function', 'functionitem', 'noop', 'wait', 'filter',
  'splitinbatches', 'aggregate', 'convertotfile', 'converttofile', 'extractfromfile', 'httprequest', 'executeworkflow',
  'executeworkflowtrigger', 'respondtowebhook', 'datetime', 'stickynote', 'summarize', 'removeduplicates', 'splitout',
]);
const AI_NODE_PREFIXES = ['lmchat', 'embeddings', 'textsplitter', 'memory', 'tool', 'vectorstore', 'documentdefault', 'outputparser', 'retriever'];

/* ---------- tema ---------- */
function applyTheme(choice) {
  const root = document.documentElement;
  if (choice === 'system') delete root.dataset.theme;
  else root.dataset.theme = choice;
  $$('[data-theme-choice]').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.themeChoice === choice)));
}

function chooseTheme(choice) {
  applyTheme(choice);
  try {
    if (choice === 'system') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch { /* armazenamento indisponível: vale só nesta sessão */ }
}

function initTheme() {
  let saved = 'system';
  try { saved = localStorage.getItem(THEME_KEY) || 'system'; } catch { /* segue o sistema */ }
  applyTheme(THEMES.includes(saved) ? saved : 'system');
  $$('[data-theme-choice]').forEach(item => item.addEventListener('click', () => chooseTheme(item.dataset.themeChoice)));
}

/* ---------- markdown mínimo e seguro: só cria nós DOM, nunca innerHTML ---------- */
const INLINE_RE = /`([^`]+)`|\*\*(.+?)\*\*|\*([^\s*][^*]*?)\*/g;
const SEPARATOR_RE = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;
const ITEM_RE = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const HEADING_RE = /^(#{1,4})\s+(.*)$/;
const RULE_RE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/;

function looksLikePath(text) {
  return /^_raw[\\/]/.test(text) || (/[\\/]/.test(text) && /\.(json|md|py|js)$/i.test(text));
}

function copyButton(text, label = 'Copiar', ariaLabel = 'Copiar') {
  const copy = button('md-copy', label, () => copyText(text, 'Copiado'));
  copy.setAttribute('aria-label', ariaLabel);
  return copy;
}

function codeNode(text) {
  if (!looksLikePath(text)) return el('code', '', text);
  const wrap = el('span', 'md-path');
  wrap.append(el('code', '', text), copyButton(text, 'copiar', 'Copiar caminho do fluxo'));
  return wrap;
}

function inlineNode(match) {
  if (match[1] !== undefined) return codeNode(match[1]);
  const node = el(match[2] !== undefined ? 'strong' : 'em');
  node.append(renderInline(match[2] ?? match[3]));
  return node;
}

function renderInline(text) {
  const fragment = document.createDocumentFragment();
  let last = 0;
  for (const match of text.matchAll(INLINE_RE)) {
    if (match.index > last) fragment.append(text.slice(last, match.index));
    fragment.append(inlineNode(match));
    last = match.index + match[0].length;
  }
  if (last < text.length) fragment.append(text.slice(last));
  return fragment;
}

function splitRow(line) {
  return line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
}

function cellAlign(spec) {
  const left = spec.startsWith(':');
  const right = spec.endsWith(':');
  if (left && right) return 'ctr';
  return right ? 'num' : '';
}

function tableCell(tag, text, align) {
  const cell = el(tag, align);
  cell.append(renderInline(text));
  return cell;
}

function readFence(lines, start) {
  const lang = lines[start].trim().slice(3).trim();
  const body = [];
  let i = start + 1;
  while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++]);
  const code = body.join('\n');
  const wrap = el('div', 'md-pre');
  const head = el('div', 'md-pre-head');
  head.append(el('span', '', lang || 'código'), copyButton(code, 'copiar', 'Copiar bloco de código'));
  const pre = el('pre');
  pre.append(el('code', '', code));
  wrap.append(head, pre);
  return [wrap, i + 1];
}

function readHeading(lines, start) {
  const [, hashes, text] = HEADING_RE.exec(lines[start]);
  const node = el(`h${Math.min(hashes.length + 1, 4)}`);
  node.append(renderInline(text));
  return [node, start + 1];
}

function readRule(lines, start) {
  return [el('hr'), start + 1];
}

function readTable(lines, start) {
  const aligns = splitRow(lines[start + 1]).map(cellAlign);
  const table = el('table');
  const headRow = el('tr');
  splitRow(lines[start]).forEach((text, index) => headRow.append(tableCell('th', text, aligns[index])));
  const thead = el('thead');
  thead.append(headRow);
  const tbody = el('tbody');
  let i = start + 2;
  while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
    const row = el('tr');
    splitRow(lines[i]).forEach((text, index) => row.append(tableCell('td', text, aligns[index])));
    tbody.append(row);
    i++;
  }
  table.append(thead, tbody);
  const wrap = el('div', 'md-table-wrap');
  wrap.append(table);
  return [wrap, i];
}

function readList(lines, start) {
  const ordered = /\d/.test(ITEM_RE.exec(lines[start])[2]);
  const list = el(ordered ? 'ol' : 'ul');
  let i = start;
  while (i < lines.length && ITEM_RE.test(lines[i])) {
    const [, indent, , text] = ITEM_RE.exec(lines[i]);
    const item = el('li', indent.length >= 2 ? 'sub' : '');
    item.append(renderInline(text));
    list.append(item);
    i++;
  }
  return [list, i];
}

function readQuote(lines, start) {
  const inner = [];
  let i = start;
  while (i < lines.length && /^\s*>/.test(lines[i])) inner.push(lines[i++].replace(/^\s*>\s?/, ''));
  const quote = el('blockquote');
  quote.append(...parseBlocks(inner));
  return [quote, i];
}

function readParagraph(lines, start) {
  const paragraph = el('p');
  let i = start;
  while (i < lines.length && lines[i].trim() && (i === start || !startsBlock(lines, i))) {
    if (i > start) paragraph.append(el('br'));
    paragraph.append(renderInline(lines[i].trim()));
    i++;
  }
  return [paragraph, i];
}

const BLOCKS = [
  { test: (lines, i) => /^\s*```/.test(lines[i]), read: readFence },
  { test: (lines, i) => HEADING_RE.test(lines[i]), read: readHeading },
  { test: (lines, i) => RULE_RE.test(lines[i]), read: readRule },
  { test: (lines, i) => lines[i].includes('|') && i + 1 < lines.length && SEPARATOR_RE.test(lines[i + 1]) && lines[i + 1].includes('-'), read: readTable },
  { test: (lines, i) => ITEM_RE.test(lines[i]), read: readList },
  { test: (lines, i) => /^\s*>/.test(lines[i]), read: readQuote },
];

const startsBlock = (lines, i) => BLOCKS.some(block => block.test(lines, i));

function parseBlocks(lines) {
  const nodes = [];
  let i = 0;
  while (i < lines.length) {
    if (!lines[i].trim()) { i++; continue; }
    const block = BLOCKS.find(candidate => candidate.test(lines, i));
    const [node, next] = (block ? block.read : readParagraph)(lines, i);
    nodes.push(node);
    i = next;
  }
  return nodes;
}

function renderMarkdown(text) {
  const root = el('div', 'md');
  try {
    root.append(...parseBlocks(String(text).replace(/\r\n?/g, '\n').split('\n')));
  } catch {
    root.replaceChildren(el('p', '', String(text)));
  }
  return root;
}

/* ---------- abas ---------- */
const tabs = () => $$('.tab');

function showView(name, { focusTab = false } = {}) {
  $$('.view').forEach(view => { view.hidden = view.id !== `view-${name}`; });
  tabs().forEach(tab => {
    const selected = tab.dataset.view === name;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (selected && focusTab) tab.focus();
  });
  try { localStorage.setItem(VIEW_KEY, name); } catch { /* armazenamento indisponível */ }
  if (name === 'pedidos') loadBoard();
  if (name === 'orcamento' && !$('#quote-result').hasChildNodes()) calculateQuote();
}

function onTabKey(event) {
  const list = tabs();
  const current = list.findIndex(tab => tab.getAttribute('aria-selected') === 'true');
  const moves = { ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: list.length - 1 };
  if (!(event.key in moves)) return;
  event.preventDefault();
  const next = (moves[event.key] + list.length) % list.length;
  showView(list[next].dataset.view, { focusTab: true });
}

/* ---------- consultor (chat) ---------- */
const chat = { sessionId: null, busy: false, timer: null };

function turn(role, label) {
  const wrap = el('div', `turn ${role}`);
  wrap.append(el('div', 'turn-label', label));
  $('#log').append(wrap);
  return wrap;
}

function addUserMessage(text) {
  const wrap = turn('user', 'Você');
  wrap.append(el('div', 'bubble user', text));
  wrap.scrollIntoView({ block: 'end' });
}

function pendingBubble() {
  const wrap = turn('bot', 'Consultor');
  const bubble = el('div', 'bubble bot pending');
  const dots = el('span', 'pending-dots');
  dots.setAttribute('aria-hidden', 'true');
  dots.append(el('i'), el('i'), el('i'));
  const label = el('span', '', 'Consultando o catálogo… 0 s');
  bubble.append(dots, label);
  wrap.append(bubble);
  wrap.scrollIntoView({ block: 'end' });
  const startedAt = Date.now();
  chat.timer = setInterval(() => { label.textContent = `Consultando o catálogo… ${Math.round((Date.now() - startedAt) / 1000)} s`; }, 1000);
  return { wrap, bubble };
}

function showReply({ wrap, bubble }, reply) {
  const text = reply || '(O consultor não devolveu texto. Tente reformular o pedido.)';
  bubble.classList.remove('pending');
  bubble.replaceChildren(renderMarkdown(text));
  wrap.firstChild.append(copyButton(text, 'copiar resposta', 'Copiar resposta inteira'));
}

function showChatError({ bubble }, error) {
  bubble.classList.remove('pending');
  bubble.classList.add('error');
  bubble.replaceChildren(document.createTextNode(error.message));
}

async function sendChat(message) {
  const text = message.trim();
  if (chat.busy || !text) return;
  chat.busy = true;
  $('#send').disabled = true;
  $('#reset').disabled = true;
  $('#starters').hidden = true;
  addUserMessage(text);
  const pending = pendingBubble();
  try {
    const data = await post('/api/chat', { message: text, sessionId: chat.sessionId });
    chat.sessionId = data.sessionId;
    showReply(pending, data.reply);
  } catch (error) {
    showChatError(pending, error);
    if (!$('#message').value) $('#message').value = text;
  } finally {
    clearInterval(chat.timer);
    chat.busy = false;
    $('#send').disabled = false;
    $('#reset').disabled = false;
    pending.wrap.scrollIntoView({ block: 'end' });
  }
}

function resetChat() {
  chat.sessionId = null;
  $('#log').replaceChildren();
  $('#starters').hidden = false;
}

function askAbout(flow) {
  showView('chat');
  $('#message').value = `Quero usar o fluxo "${flow.name}" (${flow.path}). O que preciso adaptar e quanto cobrar?`;
  $('#message').focus();
}

/* ---------- catálogo ---------- */
const catalog = { items: [], query: '', integration: '' };

function isKeyIntegration(name) {
  const key = name.toLowerCase();
  return !GENERIC_NODES.has(key) && !AI_NODE_PREFIXES.some(prefix => key.startsWith(prefix));
}

function fact(label, value, wide = false) {
  const box = el('div', wide ? 'wide' : '');
  const term = el('dt', '', label);
  const description = el('dd');
  if (value instanceof Node) description.append(value);
  else description.textContent = value;
  box.append(term, description);
  return box;
}

function integrationChips(flow, filter) {
  const all = splitList(flow.integrations);
  const key = all.filter(isKeyIntegration);
  const shown = (key.length ? key : all).slice(0, KEY_INTEGRATIONS);
  const chips = el('div', 'chips');
  shown.forEach(name => chips.append(el('span', filter && name.toLowerCase().includes(filter) ? 'chip hit' : 'chip', name)));
  const hidden = all.length - shown.length;
  if (hidden > 0) chips.append(el('span', 'chip', `+${hidden}`));
  if (!all.length) chips.textContent = 'nenhuma integração externa';
  return chips;
}

function flowFacts(flow, filter) {
  const facts = el('dl', 'facts');
  const credentials = splitList(flow.credentials).length;
  facts.append(
    fact('Gatilho', splitList(flow.triggers).join(', ') || '—'),
    fact('Tamanho', `${flow.nodes} nós`),
    fact('Credenciais', credentials ? `${credentials} a configurar` : 'nenhuma'),
    fact('Integrações', integrationChips(flow, filter), true),
  );
  return facts;
}

function flowActions(flow) {
  const actions = el('div', 'actions');
  actions.append(
    button('primary', 'Perguntar ao consultor', () => askAbout(flow)),
    button('ghost', 'Copiar caminho', () => copyText(flow.path, 'Caminho copiado')),
  );
  return actions;
}

function flowCard(flow, filter) {
  const card = el('article', 'flow');
  card.dataset.complexity = flow.complexity;
  const head = el('div', 'flow-head');
  const badges = el('div', 'flow-badges');
  badges.append(el('span', 'badge', cxLabel(flow.complexity)));
  if (flow.uses_ai) badges.append(el('span', 'badge ai', 'IA'));
  if (flow.secrets_high > 0) {
    const risk = el('span', 'badge risk', `segredo real: ${flow.secrets_high}`);
    risk.title = 'Chave, token ou segredo de terceiro dentro do JSON. Rode flowhub/scan.py e limpe antes de entregar.';
    badges.append(risk);
  }
  head.append(el('h3', '', flow.name), badges);
  card.append(head, el('div', 'cat', flow.category), profileBlocks(flow) ?? flowFacts(flow, filter));
  if (flow.notes) {
    const details = el('details');
    details.append(el('summary', '', 'Notas do autor'), el('p', '', flow.notes));
    card.append(details);
  }
  const pathRow = el('div', 'pathrow');
  pathRow.append(el('span', 'path', flow.path));
  card.append(pathRow, flowActions(flow));
  return card;
}

function sortedItems(items, mode) {
  const sorters = {
    'nodes-asc': (a, b) => a.nodes - b.nodes,
    'nodes-desc': (a, b) => b.nodes - a.nodes,
    complexity: (a, b) => (COMPLEXITY_ORDER[a.complexity] ?? 9) - (COMPLEXITY_ORDER[b.complexity] ?? 9) || a.nodes - b.nodes,
  };
  return sorters[mode] ? [...items].sort(sorters[mode]) : items;
}

function renderResults() {
  const box = $('#results');
  const items = sortedItems(catalog.items, $('#sort').value);
  const filter = catalog.integration.toLowerCase();
  $('#results-count').textContent = `${items.length} ${items.length === 1 ? 'fluxo' : 'fluxos'} para “${catalog.query}”`;
  if (items.length) {
    box.replaceChildren(...items.map(flow => flowCard(flow, filter)));
    return;
  }
  box.replaceChildren(stateBox('empty', 'Nenhum fluxo encontrado', 'Use menos termos, troque por sinônimos ou tire os filtros de integração e complexidade. Se nada servir, o consultor pode propor construir do zero.',
    button('ghost', 'Falar com o consultor', () => { showView('chat'); $('#message').focus(); })));
}

function searchParams() {
  const params = new URLSearchParams({ q: $('#q').value.trim(), limit: String(SEARCH_LIMIT) });
  const integration = $('#integration').value.trim();
  if (integration) params.set('integration', integration);
  if ($('#onlyAi').checked) params.set('ai', '1');
  if ($('#maxComplexity').value) params.set('max', $('#maxComplexity').value);
  return params;
}

let searchSeq = 0;

async function searchCatalog(event) {
  event.preventDefault();
  const params = searchParams();
  if (!params.get('q')) return;
  const seq = ++searchSeq;
  const box = $('#results');
  $('#results-bar').hidden = true;
  box.replaceChildren(el('p', 'muted', 'Buscando no catálogo…'));
  try {
    const { items } = await api(`/api/search?${params}`);
    if (seq !== searchSeq) return;
    catalog.items = items;
    catalog.query = params.get('q');
    catalog.integration = params.get('integration') || '';
    $('#results-bar').hidden = false;
    renderResults();
  } catch (error) {
    if (seq !== searchSeq) return;
    box.replaceChildren(stateBox('error', 'A busca falhou', error.message, button('ghost', 'Tentar de novo', () => $('#search-form').requestSubmit())));
  }
}

/* ---------- pedidos (kanban) ---------- */
async function moveTo(id, status) {
  try {
    await post(`/api/pedidos/${encodeURIComponent(id)}/status`, { status });
    toast(`${id} movido para ${status}`);
  } catch (error) {
    toast(error.message);
  }
  loadBoard(id);
}

function pedidoMeta(pedido) {
  const meta = el('div', 'meta');
  if (pedido.complexidade) {
    const cx = el('span', 'cx', cxLabel(pedido.complexidade));
    cx.dataset.complexity = pedido.complexidade;
    meta.append(cx);
  }
  if (toNumber(pedido.horas) !== null) meta.append(el('span', 'hours', `${pedido.horas} h`));
  return meta;
}

function pedidoMoney(pedido) {
  const list = el('dl', 'money');
  [['Setup', pedido.setup], ['Mensal', pedido.mensal]].forEach(([label, value]) => {
    const box = el('div');
    box.append(el('dt', '', label), el('dd', '', brl(value)));
    list.append(box);
  });
  return list;
}

function moveSelect(pedido) {
  const select = el('select');
  select.setAttribute('aria-label', `Mover ${pedido.id} para outro estado`);
  select.append(new Option('Mover para…', ''));
  STATUSES.filter(status => status !== pedido.status).forEach(status => select.append(new Option(status, status)));
  select.addEventListener('change', () => { if (select.value) moveTo(pedido.id, select.value); });
  return select;
}

const flag = (label, on) => el('span', on ? 'flag on' : 'flag', `${label} ${on ? 'ok' : 'pendente'}`);

function pedidoFlags(pedido) {
  const flags = el('div', 'flags');
  flags.append(flag('aceite', pedido.aceite), flag('entrada', pedido.entradaPaga));
  const { done, total } = pedido.checklist;
  if (total) flags.append(el('span', done === total ? 'flag on' : 'flag', `checklist ${done}/${total}`));
  return flags;
}

function endDrag(card) {
  card.classList.remove('dragging');
  $('#board').classList.remove('dragging');
}

function pedidoCard(pedido) {
  const card = el('article', 'card');
  card.dataset.pedido = pedido.id;
  card.draggable = true;
  card.addEventListener('dragstart', event => {
    event.dataTransfer.setData('text/plain', pedido.id);
    event.dataTransfer.effectAllowed = 'move';
    card.classList.add('dragging');
    $('#board').classList.add('dragging');
  });
  card.addEventListener('dragend', () => endDrag(card));

  const head = el('div', 'id');
  head.append(el('span', '', pedido.id));
  if (pedido.exemplo) head.append(el('span', 'tag-ex', 'exemplo'));
  const details = button('ghost small', 'Detalhes', () => openDetalhes(pedido.id, () => loadBoard(pedido.id)));
  card.append(head, el('div', 'who', pedido.cliente || '(sem cliente)'), pedidoMeta(pedido), pedidoMoney(pedido),
    pedidoFlags(pedido), details, moveSelect(pedido));
  return card;
}

function wireDropZone(column, status) {
  column.addEventListener('dragover', event => { event.preventDefault(); column.classList.add('over'); });
  column.addEventListener('dragleave', event => { if (!column.contains(event.relatedTarget)) column.classList.remove('over'); });
  column.addEventListener('drop', event => {
    event.preventDefault();
    column.classList.remove('over');
    const id = event.dataTransfer.getData('text/plain');
    // Só ids de pedido (texto solto arrastado não vale) e só se o cartão mudou de coluna.
    if (!PEDIDO_ID_RE.test(id) || column.querySelector(`[data-pedido="${id}"]`)) return;
    moveTo(id, status);
  });
}

function boardColumn(status, pedidos) {
  const items = pedidos.filter(pedido => pedido.status === status);
  const column = el('section', items.length ? 'col has' : 'col');
  column.setAttribute('aria-label', `${status}, ${items.length} pedidos`);
  const title = el('h2');
  title.append(el('span', '', status), el('b', '', String(items.length)));
  column.append(title, ...items.map(pedidoCard));
  if (!items.length) column.append(el('p', 'empty', 'Solte aqui'));
  wireDropZone(column, status);
  return column;
}

function pipelineSummary(pedidos) {
  const real = pedidos.filter(pedido => !pedido.exemplo);
  const sum = (list, field) => list.reduce((total, pedido) => total + (toNumber(pedido[field]) ?? 0), 0);
  const open = real.filter(pedido => !CLOSED_STATUSES.includes(pedido.status));
  const stat = (label, value, extra = '') => {
    const box = el('div', extra);
    box.append(el('small', '', label), el('strong', '', value));
    return box;
  };
  return [
    stat('Pedidos reais', String(real.length)),
    stat('Em andamento', String(open.length)),
    stat('Setup em andamento', brl(sum(open, 'setup')), 'money'),
    stat('Mensalidades previstas', brl(sum(real, 'mensal')), 'money'),
  ];
}

function emptyGuide() {
  const box = el('div', 'guide');
  const steps = el('ol');
  ['Descreva o cliente no Consultor. Ele busca o fluxo e entrevista se faltar dado.',
    'Ou crie o pedido direto aqui em “Novo pedido”, sem usar o chat.',
    'Mova o cartão a cada etapa; aceite e entrada paga destravam Aprovado e Em construção.'].forEach(text => steps.append(el('li', '', text)));
  box.append(el('h2', '', 'Nenhum pedido real ainda'), steps, button('primary', 'Novo pedido', () => openNovoPedido(loadBoard)),
    button('ghost', 'Abrir o consultor', () => showView('chat')));
  return box;
}

function renderOrphans(unknown) {
  if (!unknown.length) return null;
  return el('p', 'note', `Pedidos com estado desconhecido (não aparecem nas colunas): ${unknown.map(p => `${p.id} ("${p.status}")`).join(', ')}.`);
}

let boardSeq = 0;

async function loadBoard(focusId) {
  const board = $('#board');
  const seq = ++boardSeq;
  try {
    const { pedidos } = await api('/api/pedidos');
    if (seq !== boardSeq) return;
    const hasReal = pedidos.some(pedido => !pedido.exemplo);
    $('#pipeline').replaceChildren(...pipelineSummary(pedidos));
    $('#board-guide').replaceChildren(...[hasReal ? null : emptyGuide(), renderOrphans(pedidos.filter(p => !STATUSES.includes(p.status)))].filter(Boolean));
    board.replaceChildren(...STATUSES.map(status => boardColumn(status, pedidos)));
    if (focusId && PEDIDO_ID_RE.test(focusId)) $(`[data-pedido="${focusId}"] select`)?.focus();
  } catch (error) {
    if (seq !== boardSeq) return;
    $('#pipeline').replaceChildren();
    board.replaceChildren(stateBox('error', 'Não consegui carregar os pedidos', error.message, button('ghost', 'Tentar de novo', () => loadBoard())));
  }
}

/* ---------- inicialização ---------- */
async function showHealth() {
  const status = $('#status');
  try {
    const health = await api('/api/health');
    status.replaceChildren(
      el('span', health.claude ? 'ok' : 'off', health.claude ? 'Claude ok' : 'Claude ausente'),
      document.createTextNode(' · '),
      el('span', health.catalog ? 'ok' : 'off', health.catalog ? 'catálogo ok' : 'catálogo ausente'),
    );
  } catch {
    status.textContent = 'servidor indisponível';
  }
}

function initChat() {
  STARTERS.forEach(text => $('#starters').append(button('starter', text, () => sendChat(text))));
  $('#chat-form').addEventListener('submit', event => {
    event.preventDefault();
    if (chat.busy) { toast('Aguarde a resposta atual antes de enviar outra mensagem.'); return; }
    const message = $('#message').value;
    $('#message').value = '';
    sendChat(message);
  });
  $('#message').addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) $('#chat-form').requestSubmit();
  });
  $('#reset').addEventListener('click', resetChat);
}

function initTabs() {
  tabs().forEach(tab => tab.addEventListener('click', () => showView(tab.dataset.view)));
  $('.tabs').addEventListener('keydown', onTabKey);
  let initial = 'chat';
  try { initial = localStorage.getItem(VIEW_KEY) || 'chat'; } catch { /* sem armazenamento */ }
  showView($(`.tab[data-view="${initial}"]`) ? initial : 'chat');
}

initTheme();
initChat();
$('#search-form').addEventListener('submit', searchCatalog);
$('#sort').addEventListener('change', renderResults);
initOrcamento();
$('#novo-pedido').addEventListener('click', () => openNovoPedido(loadBoard));
initTabs();
showHealth();
