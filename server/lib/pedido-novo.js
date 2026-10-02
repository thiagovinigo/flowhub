import { readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setFrontmatterField } from './frontmatter.js';
import { appendLine } from './secoes.js';

const TEMPLATE_NAME = '_modelo-pedido.md';
const ID_FILE_RE = /^PED-(\d+)/;
const WEEKS_PER_MONTH = 4;
const MAX_SLUG = 40;
const MAX_ATTEMPTS = 5;
const pad = number => String(number).padStart(3, '0');

export const today = (now = new Date()) =>
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

/** Nome de arquivo seguro: sem acento, minusculo, so letras, numeros e hifen. */
export function slugify(name) {
  const slug = name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, MAX_SLUG).replace(/-+$/g, '');
  return slug || 'cliente';
}

export function nextNumber(fileNames) {
  const numbers = fileNames.map(name => ID_FILE_RE.exec(name)).filter(Boolean).map(match => Number(match[1]));
  return Math.max(0, ...numbers) + 1;
}

const oneLine = text => String(text).replace(/\s+/g, ' ').trim();
const fillLine = (text, prefix, value) => text.replace(prefix, () => `${prefix} ${value}`);

/** Preenche o modelo `_modelo-pedido.md` com os dados do formulario. Devolve o texto do pedido. */
export function fillTemplate(template, id, input, date) {
  const monthlySaving = input.horasSemana * WEEKS_PER_MONTH * input.custoHora;
  let text = template;
  for (const [key, value] of [
    ['id', id], ['cliente', input.cliente], ['status', 'Pedido'], ['urgencia', input.urgencia],
    ['faixa_orcamento', input.faixaOrcamento], ['economia_mensal', String(monthlySaving)], ['criado', date],
  ]) text = setFrontmatterField(text, key, value);

  text = text.replace('# PED-000 · Cliente', () => `# ${id} · ${input.cliente}`); // funcao: "$'" no nome nao pode virar padrao de replace
  text = fillLine(text, '- Problema hoje:', oneLine(input.problema));
  text = fillLine(text, '- Impacto (horas por semana, custo):', `${input.horasSemana} h por semana a R$ ${input.custoHora} por hora`);
  text = fillLine(text, '- Ferramentas que usa:', oneLine(input.ferramentas));
  text = fillLine(text, '- Gatilho:', oneLine(input.gatilho));
  text = fillLine(text, '- Quem opera depois:', oneLine(input.quemOpera));
  text = fillLine(text, '- Horas por semana:', String(input.horasSemana));
  text = fillLine(text, '- Custo da hora:', `R$ ${input.custoHora}`);
  text = fillLine(text, '- Economia mensal:', `R$ ${monthlySaving}`);
  return appendLine(text, 'Histórico', `- ${date} · pedido criado pela tela (estado Pedido)`);
}

async function readTemplate(dir) {
  try {
    return await readFile(join(dir, TEMPLATE_NAME), 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') throw new Error(`Modelo de pedido ausente: vault/Pedidos/${TEMPLATE_NAME}`);
    throw error;
  }
}

/**
 * Reserva o numero criando `PED-NNN.reserva` de forma exclusiva. O nome do pedido leva o cliente,
 * entao so o nome do arquivo final nao impede dois pedidos simultaneos de pegarem o mesmo numero.
 */
async function reserveId(dir) {
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    const id = `PED-${pad(nextNumber(await readdir(dir)))}`;
    try {
      await writeFile(join(dir, `${id}.reserva`), '', { flag: 'wx' });
      return id;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
  }
  throw new Error('Não consegui reservar um número de pedido. Tente de novo.');
}

/** Cria vault/Pedidos/PED-NNN-<cliente>.md com o proximo numero livre, sem sobrescrever nada. */
export async function createPedido(dir, input, now = new Date()) {
  const template = await readTemplate(dir);
  const id = await reserveId(dir);
  const file = `${id}-${slugify(input.cliente)}.md`;
  try {
    await writeFile(join(dir, file), fillTemplate(template, id, input, today(now)), { encoding: 'utf8', flag: 'wx' });
    return { id, file };
  } finally {
    await rm(join(dir, `${id}.reserva`), { force: true });
  }
}
