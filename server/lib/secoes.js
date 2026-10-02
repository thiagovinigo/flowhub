/* Operacoes em secoes `## Titulo` de um pedido em Markdown. Todas devolvem texto novo (sem mutar). */
const CHECKBOX_RE = /^- \[([ xX])\]\s+(.*)$/;

function split(text) {
  return { eol: text.includes('\r\n') ? '\r\n' : '\n', lines: text.split(/\r?\n/) };
}

function findSection(lines, heading) {
  const start = lines.findIndex(line => /^##\s+/.test(line) && line.replace(/^##\s+/, '').trim() === heading);
  if (start === -1) return null;
  const next = lines.findIndex((line, index) => index > start && /^##\s/.test(line));
  return [start, next === -1 ? lines.length : next];
}

function lastContentLine(lines, start, end) {
  let last = end - 1;
  while (last > start && lines[last].trim() === '') last -= 1;
  return last;
}

/** Acrescenta uma linha ao fim da secao; um "-" solto (marcador vazio do modelo) e substituido. */
export function appendLine(text, heading, line) {
  const { eol, lines } = split(text);
  const range = findSection(lines, heading);
  if (!range) return `${text.trimEnd()}${eol}${eol}## ${heading}${eol}${line}${eol}`;
  const last = lastContentLine(lines, range[0], range[1]);
  if (last > range[0] && lines[last].trim() === '-') lines[last] = line;
  else lines.splice(last + 1, 0, line);
  return lines.join(eol);
}

function checklistRange(lines) {
  return findSection(lines, 'Checklist de entrega');
}

/** Itens `- [ ] texto` da secao "Checklist de entrega", com o indice de cada um. */
export function listChecklist(text) {
  const { lines } = split(text);
  const range = checklistRange(lines);
  if (!range) return [];
  const items = [];
  for (let i = range[0] + 1; i < range[1]; i += 1) {
    const match = CHECKBOX_RE.exec(lines[i]);
    if (match) items.push({ index: items.length, label: match[2].trim(), done: match[1] !== ' ' });
  }
  return items;
}

export function setChecklistItem(text, index, done) {
  const { eol, lines } = split(text);
  const range = checklistRange(lines);
  let seen = -1;
  for (let i = range ? range[0] + 1 : 0; range && i < range[1]; i += 1) {
    const match = CHECKBOX_RE.exec(lines[i]);
    if (!match) continue;
    seen += 1;
    if (seen === index) {
      lines[i] = `- [${done ? 'x' : ' '}] ${match[2]}`;
      return lines.join(eol);
    }
  }
  throw new RangeError('Item do checklist não encontrado');
}

const cleanCell = value => String(value).replace(/\|/g, '/').replace(/\s+/g, ' ').trim();

/** Acrescenta uma linha de tabela logo depois da ultima linha da tabela da secao. */
export function appendTableRow(text, heading, cells) {
  const { eol, lines } = split(text);
  const range = findSection(lines, heading);
  let last = -1;
  for (let i = range ? range[0] + 1 : 0; range && i < range[1]; i += 1) if (lines[i].startsWith('|')) last = i;
  if (last === -1) throw new Error(`Tabela não encontrada na seção "${heading}"`);
  lines.splice(last + 1, 0, `| ${cells.map(cleanCell).join(' | ')} |`);
  return lines.join(eol);
}

/** Linhas de dados (sem cabecalho e separador) da tabela da secao, como listas de celulas. */
export function readTableRows(text, heading) {
  const { lines } = split(text);
  const range = findSection(lines, heading);
  if (!range) return [];
  return lines.slice(range[0] + 1, range[1])
    .filter(line => line.startsWith('|'))
    .slice(2)
    .map(line => line.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim()))
    .filter(cells => cells.some(Boolean));
}
