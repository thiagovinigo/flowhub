import test from 'node:test';
import assert from 'node:assert/strict';
import { run } from '../server/lib/run.js';

const NODE = process.execPath;
const BIG_OUTPUT_CHARS = 300_000;

test('run devolve acentos intactos mesmo em saidas grandes (varios pedacos)', async () => {
  const script = `process.stdout.write('çã'.repeat(${BIG_OUTPUT_CHARS}))`;
  const output = await run(NODE, ['-e', script]);
  assert.equal(output.length, BIG_OUTPUT_CHARS * 2);
  assert.ok(!output.includes('�'), 'nao pode haver caractere de substituicao');
});

test('run rejeita com a saida de erro quando o processo falha', async () => {
  await assert.rejects(run(NODE, ['-e', "console.error('falhou aqui'); process.exit(3)"]), /falhou aqui/);
});

test('run interrompe quando passa do limite de tempo', async () => {
  await assert.rejects(run(NODE, ['-e', 'setTimeout(() => {}, 10000)'], { timeoutMs: 300 }), /Tempo esgotado/);
});

test('run rejeita saidas acima do limite em vez de acumular sem fim', async () => {
  const script = "const chunk = 'x'.repeat(100000); const t = setInterval(() => process.stdout.write(chunk), 1); setTimeout(() => clearInterval(t), 5000)";
  await assert.rejects(run(NODE, ['-e', script], { timeoutMs: 8000 }), /Saída grande demais/);
});

test('run rejeita quando o programa nao existe', async () => {
  await assert.rejects(run('programa-que-nao-existe-xyz', []), error => error.code === 'ENOENT');
});
