import test from 'node:test';
import assert from 'node:assert/strict';
import { copyFile, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createPedido, nextNumber, slugify } from '../server/lib/pedido-novo.js';
import { parseFrontmatter } from '../server/lib/frontmatter.js';
import { InputError, novoPedidoInput } from '../server/lib/validate.js';

const TEMPLATE = resolve(import.meta.dirname, '..', 'vault', 'Pedidos', '_modelo-pedido.md');
const NOW = new Date(2026, 9, 1);
const FORM = {
  cliente: 'Agência Vitrine Digital', problema: 'Leads do Instagram copiados à mão.\nDuas vezes ao dia.', horasSemana: 15,
  custoHora: 50, ferramentas: 'Instagram, Google Sheets', gatilho: 'Formulário', urgencia: 'media',
  faixaOrcamento: 'R$ 3 a 5 mil', quemOpera: 'Analista de marketing',
};

async function folder() {
  const dir = await mkdtemp(join(tmpdir(), 'flowhub-novo-'));
  await copyFile(TEMPLATE, join(dir, '_modelo-pedido.md'));
  return dir;
}

test('cria o pedido a partir do modelo, com numero, estado, data e economia calculada', async () => {
  const dir = await folder();
  const { id, file } = await createPedido(dir, novoPedidoInput(FORM), NOW);
  assert.equal(id, 'PED-001');
  assert.equal(file, 'PED-001-agencia-vitrine-digital.md');
  const text = await readFile(join(dir, file), 'utf8');
  const data = parseFrontmatter(text);
  assert.equal(data.status, 'Pedido');
  assert.equal(data.criado, '2026-10-01');
  assert.equal(data.economia_mensal, '3000'); // 15 h x 4 x R$ 50
  assert.equal(data.urgencia, 'media');
  assert.ok(text.includes('# PED-001 · Agência Vitrine Digital'));
  assert.ok(text.includes('- Problema hoje: Leads do Instagram copiados à mão. Duas vezes ao dia.'));
  assert.ok(text.includes('- 2026-10-01 · pedido criado pela tela'));
});

test('o pedido criado tem os mesmos campos e secoes do modelo (paridade)', async () => {
  const dir = await folder();
  const { file } = await createPedido(dir, novoPedidoInput(FORM), NOW);
  const template = await readFile(TEMPLATE, 'utf8');
  const created = await readFile(join(dir, file), 'utf8');
  assert.deepEqual(Object.keys(parseFrontmatter(created)), Object.keys(parseFrontmatter(template)));
  const headings = text => text.split('\n').filter(line => line.startsWith('## '));
  assert.deepEqual(headings(created), headings(template));
});

test('pedidos criados em seguida recebem os proximos numeros, sem sobrescrever', async () => {
  const dir = await folder();
  await writeFile(join(dir, 'PED-007-antigo.md'), '---\nid: PED-007\n---\n');
  const first = await createPedido(dir, novoPedidoInput(FORM), NOW);
  const second = await createPedido(dir, novoPedidoInput({ ...FORM, cliente: 'Outro' }), NOW);
  assert.deepEqual([first.id, second.id], ['PED-008', 'PED-009']);
  assert.equal(await readFile(join(dir, 'PED-007-antigo.md'), 'utf8'), '---\nid: PED-007\n---\n');
});

test('criacoes simultaneas nao colidem', async () => {
  const dir = await folder();
  const results = await Promise.all([1, 2, 3].map(n => createPedido(dir, novoPedidoInput({ ...FORM, cliente: `Cliente ${n}` }), NOW)));
  assert.equal(new Set(results.map(item => item.id)).size, 3);
});

test('cifrao no nome do cliente nao vira padrao de substituicao e nao corrompe o pedido', async () => {
  for (const cliente of ["A$'B", 'A$&B', 'A$$B', 'A$`B']) {
    const dir = await folder();
    const { file } = await createPedido(dir, novoPedidoInput({ ...FORM, cliente }), NOW);
    const text = await readFile(join(dir, file), 'utf8');
    assert.ok(text.includes(`# PED-001 · ${cliente}`), cliente);
    assert.equal(text.split('## Briefing').length - 1, 1, `${cliente}: o corpo foi duplicado`);
    assert.equal(parseFrontmatter(text).cliente, cliente);
  }
});

test('sem o modelo, explica o que falta', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'flowhub-novo-'));
  await assert.rejects(createPedido(dir, novoPedidoInput(FORM), NOW), /Modelo de pedido ausente/);
});

test('slugify tira acento e simbolos, limita o tamanho e nunca devolve vazio', () => {
  assert.equal(slugify('Agência Vitrine Digital'), 'agencia-vitrine-digital');
  assert.equal(slugify('  A/B * C  '), 'a-b-c');
  assert.equal(slugify('???'), 'cliente');
  assert.ok(slugify('x'.repeat(200)).length <= 40);
  assert.equal(nextNumber(['PED-003-a.md', 'PED-010-b.md', '_modelo-pedido.md']), 11);
  assert.equal(nextNumber([]), 1);
});

test('novoPedidoInput aceita o formulario completo e a faixa de orcamento e opcional', () => {
  assert.equal(novoPedidoInput(FORM).cliente, 'Agência Vitrine Digital');
  assert.equal(novoPedidoInput({ ...FORM, faixaOrcamento: '' }).faixaOrcamento, '');
});

test('novoPedidoInput diz qual campo corrigir', () => {
  for (const field of ['cliente', 'problema', 'ferramentas', 'gatilho', 'quemOpera']) {
    assert.throws(() => novoPedidoInput({ ...FORM, [field]: '  ' }), error => error instanceof InputError && error.field === field);
  }
  for (const field of ['horasSemana', 'custoHora']) {
    assert.throws(() => novoPedidoInput({ ...FORM, [field]: '15' }), error => error.field === field);
    assert.throws(() => novoPedidoInput({ ...FORM, [field]: 0 }), error => error.field === field);
  }
  assert.throws(() => novoPedidoInput({ ...FORM, urgencia: 'urgentissima' }), error => error.field === 'urgencia');
  assert.throws(() => novoPedidoInput(undefined), InputError);
});

test('novoPedidoInput recusa nome de cliente com caractere de caminho ou que quebre o cabecalho', () => {
  for (const cliente of ['../x', 'a/b', 'a\\b', 'a..b', 'a#b', 'a\nb', 'a setup: 1', 'a\u0085b']) {
    assert.throws(() => novoPedidoInput({ ...FORM, cliente }), error => error instanceof InputError && error.field === 'cliente', cliente);
  }
});
