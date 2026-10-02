import { readdir, readFile, rename, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { UNSAFE_HEADER_VALUE, parseFrontmatter, setFrontmatterField } from './frontmatter.js';
import { today } from './pedido-novo.js';
import { appendLine, appendTableRow, listChecklist, readTableRows, setChecklistItem } from './secoes.js';
import { STATUSES, isBackward, transitionProblems } from './transicoes.js';

export { STATUSES, parseFrontmatter };

const FILE_RE = /^(PED-\d{3,})[^\\/]*\.md$/;
const ID_RE = /^PED-\d{3,}$/;
const MAX_TEXT = 200;
const MAX_HOURS_ENTRY = 24;
const HOURS_DECIMALS = 100;
const APPROVED = STATUSES.indexOf('Aprovado');

export class NotFoundError extends Error {}
/** A mudanca e valida, mas uma regra de negocio (trava, congelamento) a impede. */
export class TransitionError extends Error {}

/** Data real no formato AAAA-MM-DD: "2026-02-31" nao passa (Date.parse a empurraria para marco). */
function isDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
const isNumber = value => /^\d+(\.\d+)?$/.test(value);
const oneOf = list => value => list.includes(value);
const isFileName = value => /^[\p{L}\p{N} _.()-]{1,120}$/u.test(value); // letras com acento valem; barras nao
const isText = value => value.length <= MAX_TEXT && !UNSAFE_HEADER_VALUE.test(value);

/** Campos editaveis pela tela e a regra de cada um. Valor vazio limpa o campo (menos entrada_paga). */
const FIELD_RULES = {
  aceite_em: isDate,
  aceite_canal: oneOf(['email', 'whatsapp', 'reuniao']),
  aceite_evidencia: isFileName,
  versao_proposta: value => /^PED-\d{3,}-v\d+$/.test(value),
  entrada_paga: oneOf(['true', 'false']),
  comprovante: isFileName,
  economia_mensal: isNumber,
  setup: isNumber,
  mensal: isNumber,
  horas_estimadas: isNumber,
  prazo_dias: isNumber,
  complexidade: oneOf(['simples', 'medio', 'complexo']),
  validade_proposta: isDate,
  fluxo_origem: oneOf(['proprio', 'curso', 'terceiros']),
  fluxo_licenca: isText,
  fluxo_qualidade: oneOf(['testado', 'precisa ajuste', 'quebrado']),
  urgencia: oneOf(['baixa', 'media', 'alta']),
  faixa_orcamento: isText,
  fluxo_base: isText,
};
/** Depois do aceite, escopo e preco ficam congelados: mudar vira pedido de alteracao. */
const FROZEN_FIELDS = ['setup', 'mensal', 'horas_estimadas', 'complexidade'];

/* Uma gravacao por vez em cada pedido, e gravacao atomica (arquivo temporario + rename):
   dois cliques ou duas abas nao perdem atualizacao nem deixam o arquivo pela metade. */
const locks = new Map();

async function withPedidoLock(dir, id, task) {
  const key = `${dir}::${id}`;
  const run = (locks.get(key) ?? Promise.resolve()).catch(() => {}).then(task);
  locks.set(key, run);
  try {
    return await run;
  } finally {
    if (locks.get(key) === run) locks.delete(key);
  }
}

async function writeAtomic(path, text) {
  const temp = `${path}.${process.pid}.tmp`;
  await writeFile(temp, text, 'utf8');
  await rename(temp, path);
}

async function pedidoFiles(dir) {
  try {
    return (await readdir(dir)).filter(name => FILE_RE.test(name));
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
}

/** Le o arquivo sem o BOM que o Bloco de Notas e alguns editores do Windows gravam no inicio. */
const readText = async path => (await readFile(path, 'utf8')).replace(/^﻿/, '');

async function locate(dir, id) {
  if (!ID_RE.test(id)) throw new NotFoundError('Pedido inválido');
  const file = (await pedidoFiles(dir)).find(name => FILE_RE.exec(name)[1] === id);
  if (!file) throw new NotFoundError('Pedido não encontrado');
  const path = join(dir, file);
  return { file, path, text: await readText(path) };
}

function summarize(file, text) {
  const data = parseFrontmatter(text);
  const checklist = listChecklist(text);
  return {
    id: FILE_RE.exec(file)[1],
    file,
    cliente: data.cliente ?? '',
    status: data.status ?? '',
    complexidade: data.complexidade ?? '',
    horas: data.horas_estimadas ?? '',
    setup: data.setup ?? '',
    mensal: data.mensal ?? '',
    exemplo: data.exemplo === 'true',
    aceite: Boolean(data.aceite_em),
    entradaPaga: data.entrada_paga === 'true',
    checklist: { done: checklist.filter(item => item.done).length, total: checklist.length },
  };
}

export async function listPedidos(dir) {
  const files = await pedidoFiles(dir);
  const pedidos = await Promise.all(files.map(async file => summarize(file, await readText(join(dir, file)))));
  return pedidos.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
}

/** Caminho do arquivo de um pedido (validando o id), para os scripts que leem o pedido direto. */
export async function pedidoFilePath(dir, id) {
  return (await locate(dir, id)).path;
}

/** Tudo que a tela de detalhes precisa: campos do cabecalho, checklist e horas reais. */
export async function getPedido(dir, id) {
  const { file, text } = await locate(dir, id);
  return {
    ...summarize(file, text),
    campos: parseFrontmatter(text),
    checklistItens: listChecklist(text),
    horasLinhas: readTableRows(text, 'Horas reais').map(([data, horas, atividade]) => ({ data, horas, atividade })),
  };
}

/** Muda o estado respeitando as travas; voltar e sempre permitido. Registra a mudanca no Historico. */
export async function setStatus(dir, id, status, now = new Date()) {
  if (!STATUSES.includes(status)) throw new RangeError('Status inválido');
  return withPedidoLock(dir, id, async () => {
    const { path, text } = await locate(dir, id);
    const data = parseFrontmatter(text);
    const from = data.status ?? '';
    if (from === status) return { id, status };

    const problems = transitionProblems(from, status, data, listChecklist(text));
    if (problems.length) throw new TransitionError(`Não dá para mover ${id} para "${status}". Falta: ${problems.join('; ')}.`);

    const note = STATUSES.includes(from) && isBackward(from, status) ? ' (voltou)' : '';
    const updated = appendLine(setFrontmatterField(text, 'status', status), 'Histórico', `- ${today(now)} · ${from || '?'} → ${status}${note}`);
    await writeAtomic(path, updated);
    return { id, status };
  });
}

function normalizeField(key, raw) {
  // hasOwn: chaves herdadas do Object ("constructor", "__proto__") nao sao campos validos.
  if (!Object.hasOwn(FIELD_RULES, key)) throw new RangeError('Campo não editável');
  const value = String(raw ?? '').trim().replace(/^(\d+),(\d+)$/, '$1.$2');
  const valid = value === '' ? key !== 'entrada_paga' : FIELD_RULES[key](value);
  if (!valid) throw new RangeError(`Valor inválido para "${key}"`);
  return value;
}

/** Recusa mudancas que desfariam o aceite ou o congelamento. `data` e o cabecalho atual. */
function guardChange(key, value, data) {
  if (data.aceite_em && FROZEN_FIELDS.includes(key)) {
    throw new TransitionError(`Escopo e preço estão congelados depois do aceite ("${key}"). Registre um pedido de alteração.`);
  }
  const approved = STATUSES.indexOf(data.status) >= APPROVED;
  if (approved && key.startsWith('aceite_') && value === '') {
    throw new TransitionError('O aceite já foi dado. Para desfazê-lo, volte o pedido para Orçado primeiro.');
  }
}

export async function updateCampos(dir, id, campos, now = new Date()) {
  const entries = Object.entries(campos ?? {});
  if (entries.length === 0) throw new RangeError('Nenhum campo para atualizar');
  return withPedidoLock(dir, id, async () => {
    const { path, text } = await locate(dir, id);
    const data = parseFrontmatter(text);
    let updated = text;
    const changes = [];
    for (const [key, raw] of entries) {
      const before = data[key] ?? '';
      // Campo que nao mudou nao e revalidado: um valor antigo fora do padrao nao pode travar o grupo inteiro.
      if (Object.hasOwn(FIELD_RULES, key) && String(raw ?? '').trim() === before) continue;
      const value = normalizeField(key, raw);
      if (value === before) continue;
      guardChange(key, value, data);
      updated = setFrontmatterField(updated, key, value);
      changes.push(`${key}: ${before || '(vazio)'} → ${value || '(vazio)'}`);
    }
    if (changes.length === 0) return { id, campos: [] };
    updated = appendLine(updated, 'Histórico', `- ${today(now)} · campos atualizados: ${changes.join('; ')}`);
    await writeAtomic(path, updated);
    return { id, campos: changes.map(change => change.split(':')[0]) };
  });
}

export async function toggleChecklist(dir, id, index, done) {
  if (!Number.isInteger(index) || typeof done !== 'boolean') throw new RangeError('Item ou valor inválido');
  return withPedidoLock(dir, id, async () => {
    const { path, text } = await locate(dir, id);
    await writeAtomic(path, setChecklistItem(text, index, done));
    return { id, index, done };
  });
}

const sumHours = rows => rows.reduce((total, [, hours]) => total + Number(hours || 0), 0);

/** Acrescenta uma linha em "Horas reais" e atualiza `horas_reais` com o total (ENT-05). */
export async function addHoras(dir, id, entry, now = new Date()) {
  const date = entry?.data || today(now);
  const hours = Number(String(entry?.horas ?? '').replace(',', '.'));
  const activity = String(entry?.atividade ?? '').replace(/\s+/g, ' ').trim();
  if (!isDate(date)) throw new RangeError('Data inválida (use AAAA-MM-DD)');
  if (!Number.isFinite(hours) || hours <= 0 || hours > MAX_HOURS_ENTRY) throw new RangeError(`Horas devem ficar entre 0 e ${MAX_HOURS_ENTRY}`);
  if (!activity || activity.length > MAX_TEXT) throw new RangeError('Descreva a feature ou atividade (até 200 caracteres)');

  return withPedidoLock(dir, id, async () => {
    const { path, text } = await locate(dir, id);
    let updated;
    try {
      updated = appendTableRow(text, 'Horas reais', [date, String(hours), activity]);
    } catch {
      throw new RangeError('Este pedido é de um modelo antigo e não tem a tabela "Horas reais".');
    }
    const total = Math.round(sumHours(readTableRows(updated, 'Horas reais')) * HOURS_DECIMALS) / HOURS_DECIMALS;
    await writeAtomic(path, setFrontmatterField(updated, 'horas_reais', String(total)));
    return { id, horasReais: total };
  });
}
