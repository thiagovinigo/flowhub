import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { NotFoundError, listPedidos, parseFrontmatter, setStatus } from '../server/lib/pedidos.js';

const BODY = '\n# Corpo\nstatus: isto no corpo nao pode mudar\n';

function pedido(id, cliente, status) {
  return `---\nid: ${id}\ncliente: ${cliente}\nstatus: ${status}   # Pedido | Discovery\nsetup: 3500\nexemplo: true\n---\n${BODY}`;
}

async function fixture() {
  const dir = await mkdtemp(join(tmpdir(), 'flowhub-'));
  await writeFile(join(dir, 'PED-002-beta.md'), pedido('PED-002', 'Beta', 'Orçado'));
  await writeFile(join(dir, 'PED-001-acme.md'), pedido('PED-001', 'Acme', 'Pedido'));
  await writeFile(join(dir, '_modelo-pedido.md'), pedido('PED-000', 'Modelo', 'Pedido'));
  await writeFile(join(dir, 'notas.txt'), 'ignorar');
  return dir;
}

test('parseFrontmatter remove comentarios e devolve as chaves', () => {
  const data = parseFrontmatter(pedido('PED-001', 'Acme', 'Pedido'));
  assert.equal(data.status, 'Pedido');
  assert.equal(data.cliente, 'Acme');
  assert.equal(data.setup, '3500');
});

test('parseFrontmatter trata valor vazio seguido de comentario', () => {
  assert.equal(parseFrontmatter('---\nfluxo_base:      # path do catalogo\n---\n').fluxo_base, '');
});

test('parseFrontmatter devolve objeto vazio sem cabecalho', () => {
  assert.deepEqual(parseFrontmatter('# so texto'), {});
});

test('listPedidos ignora modelo e arquivos nao-pedido, e ordena por id', async () => {
  const lista = await listPedidos(await fixture());
  assert.deepEqual(lista.map(p => p.id), ['PED-001', 'PED-002']);
  assert.equal(lista[0].exemplo, true);
});

test('listPedidos ordena numericamente: PED-999 vem antes de PED-1000', async () => {
  const dir = await fixture();
  await writeFile(join(dir, 'PED-1000-gama.md'), pedido('PED-1000', 'Gama', 'Pedido'));
  await writeFile(join(dir, 'PED-999-delta.md'), pedido('PED-999', 'Delta', 'Pedido'));
  const ids = (await listPedidos(dir)).map(p => p.id);
  assert.deepEqual(ids, ['PED-001', 'PED-002', 'PED-999', 'PED-1000']);
});

test('listPedidos devolve lista vazia quando a pasta nao existe', async () => {
  assert.deepEqual(await listPedidos(join(tmpdir(), 'flowhub-nao-existe-xyz')), []);
});

test('setStatus troca so a linha status do cabecalho', async () => {
  const dir = await fixture();
  await setStatus(dir, 'PED-001', 'Discovery');
  const text = await readFile(join(dir, 'PED-001-acme.md'), 'utf8');
  assert.match(text, /^status: Discovery {3}#/m);
  assert.ok(text.includes('status: isto no corpo nao pode mudar'));
  assert.ok(text.includes('cliente: Acme'));
});

test('setStatus preserva o comentario da linha de status', async () => {
  const dir = await fixture();
  await setStatus(dir, 'PED-002', 'Features');
  const text = await readFile(join(dir, 'PED-002-beta.md'), 'utf8');
  assert.match(text, /^status: Features {3}# Pedido \| Discovery$/m);
});

test('setStatus rejeita status desconhecido sem alterar o arquivo', async () => {
  const dir = await fixture();
  await assert.rejects(setStatus(dir, 'PED-001', 'Inventado'), RangeError);
  assert.match(await readFile(join(dir, 'PED-001-acme.md'), 'utf8'), /^status: Pedido/m);
});

test('setStatus rejeita id malformado e pedido inexistente', async () => {
  const dir = await fixture();
  await assert.rejects(setStatus(dir, '../x', 'Pedido'), NotFoundError);
  await assert.rejects(setStatus(dir, 'PED-999', 'Pedido'), NotFoundError);
});
