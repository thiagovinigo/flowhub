import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  NotFoundError, TransitionError, addHoras, getPedido, listPedidos, setStatus, toggleChecklist, updateCampos,
} from '../server/lib/pedidos.js';

const NOW = new Date(2026, 9, 1);
const ACEITE = 'aceite_em: 2026-10-01\naceite_canal: email\nversao_proposta: PED-001-v1\naceite_evidencia: ok.png\n';

function pedido({ status = 'Orçado', extra = '', checklist = '- [ ] um\n- [ ] dois', horas = true } = {}) {
  return `---
id: PED-001
cliente: Acme
status: ${status}   # Pedido | Discovery
setup: 3500
mensal: 497
entrada_paga: false
${extra}---

# PED-001 · Acme

## Checklist de entrega
${checklist}

${horas ? '## Horas reais\n| Data | Horas | Atividade |\n|---|---|---|\n\n' : ''}## Decisões
-

## Histórico
-
`;
}

async function fixture(text = pedido()) {
  const dir = await mkdtemp(join(tmpdir(), 'flowhub-regras-'));
  await writeFile(join(dir, 'PED-001-acme.md'), text);
  return { dir, read: () => readFile(join(dir, 'PED-001-acme.md'), 'utf8') };
}

test('Aprovado e recusado sem aceite e o arquivo nao muda', async () => {
  const { dir, read } = await fixture();
  const before = await read();
  await assert.rejects(setStatus(dir, 'PED-001', 'Aprovado', NOW), error => error instanceof TransitionError && /aceite_em/.test(error.message));
  assert.equal(await read(), before);
});

test('com o aceite completo, Aprovado passa e o Historico registra a mudanca', async () => {
  const { dir, read } = await fixture(pedido({ extra: ACEITE }));
  await setStatus(dir, 'PED-001', 'Aprovado', NOW);
  const text = await read();
  assert.match(text, /^status: Aprovado {3}#/m);
  assert.ok(text.includes('- 2026-10-01 · Orçado → Aprovado'));
});

test('Em construcao exige entrada paga com comprovante', async () => {
  const { dir } = await fixture(pedido({ status: 'Aprovado', extra: ACEITE }));
  await assert.rejects(setStatus(dir, 'PED-001', 'Em construção', NOW), /entrada_paga/);
  await updateCampos(dir, 'PED-001', { entrada_paga: 'true', comprovante: 'pix.png' }, NOW);
  assert.deepEqual(await setStatus(dir, 'PED-001', 'Em construção', NOW), { id: 'PED-001', status: 'Em construção' });
});

test('Entregue so com o checklist inteiro marcado', async () => {
  const extra = `${ACEITE}comprovante: pix.png\n`;
  const { dir } = await fixture(pedido({ status: 'Em construção', extra }).replace('entrada_paga: false', 'entrada_paga: true'));
  await assert.rejects(setStatus(dir, 'PED-001', 'Entregue', NOW), /2 de 2 itens pendentes/);
  await toggleChecklist(dir, 'PED-001', 0, true);
  await toggleChecklist(dir, 'PED-001', 1, true);
  assert.equal((await setStatus(dir, 'PED-001', 'Entregue', NOW)).status, 'Entregue');
});

test('voltar e permitido, mesmo com travas pendentes, e fica registrado', async () => {
  const { dir, read } = await fixture(pedido({ status: 'Em construção' }));
  await setStatus(dir, 'PED-001', 'Orçado', NOW);
  assert.ok((await read()).includes('Em construção → Orçado (voltou)'));
});

test('updateCampos valida cada campo e registra no Historico', async () => {
  const { dir, read } = await fixture();
  await updateCampos(dir, 'PED-001', { aceite_em: '2026-10-05', aceite_canal: 'whatsapp' }, NOW);
  const text = await read();
  assert.match(text, /^aceite_em: 2026-10-05$/m);
  assert.ok(text.includes('campos atualizados: aceite_em: (vazio) → 2026-10-05; aceite_canal: (vazio) → whatsapp'));
  await assert.rejects(updateCampos(dir, 'PED-001', { aceite_em: '05/10/2026' }), RangeError);
  await assert.rejects(updateCampos(dir, 'PED-001', { aceite_canal: 'pombo' }), RangeError);
  await assert.rejects(updateCampos(dir, 'PED-001', { entrada_paga: '' }), RangeError);
  await assert.rejects(updateCampos(dir, 'PED-001', { status: 'Entregue' }), /não editável/);
  await assert.rejects(updateCampos(dir, 'PED-001', { fluxo_base: 'a # b' }), RangeError);
  await assert.rejects(updateCampos(dir, 'PED-001', {}), RangeError);
});

test('depois do aceite, escopo e preco ficam congelados', async () => {
  const { dir } = await fixture(pedido({ status: 'Aprovado', extra: ACEITE }));
  await assert.rejects(updateCampos(dir, 'PED-001', { setup: '9000' }), TransitionError);
  await updateCampos(dir, 'PED-001', { setup: '3500' }); // mesmo valor nao e mudanca
  await updateCampos(dir, 'PED-001', { comprovante: 'pix.png' }); // campos de cobranca continuam livres
});

test('addHoras soma em horas_reais e recusa horas invalidas', async () => {
  const { dir, read } = await fixture();
  await addHoras(dir, 'PED-001', { data: '2026-10-02', horas: '2,5', atividade: 'Montar fluxo' }, NOW);
  const result = await addHoras(dir, 'PED-001', { horas: 1, atividade: 'Teste' }, NOW);
  assert.equal(result.horasReais, 3.5);
  assert.match(await read(), /^horas_reais: 3\.5$/m);
  for (const horas of [0, -1, 'abc', 25]) {
    await assert.rejects(addHoras(dir, 'PED-001', { horas, atividade: 'x' }, NOW), RangeError);
  }
  await assert.rejects(addHoras(dir, 'PED-001', { horas: 1, atividade: ' ' }, NOW), RangeError);
});

test('addHoras explica quando o pedido e de um modelo antigo', async () => {
  const { dir } = await fixture(pedido({ horas: false }));
  await assert.rejects(addHoras(dir, 'PED-001', { horas: 1, atividade: 'x' }, NOW), /modelo antigo/);
});

test('getPedido e listPedidos expoem aceite, entrada, checklist e horas', async () => {
  const { dir } = await fixture(pedido({ extra: ACEITE, checklist: '- [x] um\n- [ ] dois' }));
  await addHoras(dir, 'PED-001', { data: '2026-10-02', horas: 2, atividade: 'a' }, NOW);
  const detail = await getPedido(dir, 'PED-001');
  assert.equal(detail.campos.aceite_canal, 'email');
  assert.deepEqual(detail.horasLinhas, [{ data: '2026-10-02', horas: '2', atividade: 'a' }]);
  assert.equal(detail.checklistItens.length, 2);
  const [summary] = await listPedidos(dir);
  assert.equal(summary.aceite, true);
  assert.equal(summary.entradaPaga, false);
  assert.deepEqual(summary.checklist, { done: 1, total: 2 });
  await assert.rejects(getPedido(dir, 'PED-999'), NotFoundError);
});

test('chaves herdadas do Object (constructor, __proto__) nao burlam as travas nem injetam linhas no cabecalho', async () => {
  const { dir, read } = await fixture();
  const before = await read();
  const injection = 'x\nstatus: Entregue\naceite_em: 2026-01-01\nentrada_paga: true';
  await assert.rejects(updateCampos(dir, 'PED-001', { constructor: injection }), /não editável/);
  await assert.rejects(updateCampos(dir, 'PED-001', { ['__proto__']: injection }), /não editável/);
  await assert.rejects(updateCampos(dir, 'PED-001', { fluxo_base: injection }), RangeError);
  assert.equal(await read(), before);
});

test('quebras de linha Unicode no valor sao recusadas (o Python tambem as trata como linha)', async () => {
  const { dir } = await fixture();
  for (const separator of [' ', ' ', '\u0085', '\v', '\f']) {
    await assert.rejects(updateCampos(dir, 'PED-001', { fluxo_base: `a${separator}setup: 1` }), RangeError);
  }
});

test('o congelamento nao se desfaz voltando de estado: so limpando o aceite, e isso so antes de Aprovado', async () => {
  const { dir } = await fixture(pedido({ status: 'Orçado', extra: ACEITE }));
  await assert.rejects(updateCampos(dir, 'PED-001', { setup: '9999' }), TransitionError); // Orçado, mas com aceite
  await updateCampos(dir, 'PED-001', { aceite_em: '' }, NOW); // desfazer o aceite e permitido antes de Aprovado
  await updateCampos(dir, 'PED-001', { setup: '9999' }, NOW); // sem aceite o preco volta a ser editavel
});

test('depois de Aprovado o aceite nao pode ser apagado', async () => {
  const { dir } = await fixture(pedido({ status: 'Aprovado', extra: ACEITE }));
  await assert.rejects(updateCampos(dir, 'PED-001', { aceite_em: '' }), /aceite já foi dado/);
  await assert.rejects(updateCampos(dir, 'PED-001', { aceite_canal: '' }), TransitionError);
});

test('o Historico guarda valor antigo e novo, e campo que nao mudou nao gera linha', async () => {
  const { dir, read } = await fixture();
  await updateCampos(dir, 'PED-001', { setup: '4000' }, NOW);
  assert.ok((await read()).includes('setup: 3500 → 4000'));
  const before = await read();
  await updateCampos(dir, 'PED-001', { setup: '4000' }, NOW);
  assert.equal(await read(), before);
});

test('valor antigo fora do padrao, sem mudar, nao trava o grupo inteiro', async () => {
  const { dir, read } = await fixture(pedido({ extra: 'horas_estimadas: 12h\n' }));
  await updateCampos(dir, 'PED-001', { horas_estimadas: '12h', comprovante: 'pix.png' }, NOW);
  assert.match(await read(), /^comprovante: pix.png$/m);
});

test('datas inexistentes sao recusadas e nome de arquivo com acento e aceito', async () => {
  const { dir } = await fixture();
  await assert.rejects(updateCampos(dir, 'PED-001', { aceite_em: '2026-02-31' }), RangeError);
  await updateCampos(dir, 'PED-001', { aceite_evidencia: 'aceite-joão março.png' }, NOW);
  await assert.rejects(updateCampos(dir, 'PED-001', { comprovante: '../x.png' }), RangeError);
});

test('gravacoes simultaneas no mesmo pedido nao perdem atualizacao e nao deixam arquivo temporario', async () => {
  const { dir, read } = await fixture();
  await Promise.all([
    toggleChecklist(dir, 'PED-001', 0, true),
    toggleChecklist(dir, 'PED-001', 1, true),
    ...[1, 2, 3, 4, 5].map(n => addHoras(dir, 'PED-001', { data: '2026-10-02', horas: n, atividade: `a${n}` }, NOW)),
    updateCampos(dir, 'PED-001', { comprovante: 'pix.png' }, NOW),
  ]);
  const detail = await getPedido(dir, 'PED-001');
  assert.deepEqual(detail.checklistItens.map(item => item.done), [true, true]);
  assert.equal(detail.horasLinhas.length, 5);
  assert.equal(detail.campos.horas_reais, '15');
  assert.equal(detail.campos.comprovante, 'pix.png');
  assert.ok(!(await readdir(dir)).some(name => name.endsWith('.tmp')));
  assert.ok((await read()).startsWith('---'));
});

test('arquivo com BOM (Bloco de Notas) continua sendo lido e alterado', async () => {
  const { dir } = await fixture('﻿' + pedido());
  assert.equal((await listPedidos(dir))[0].cliente, 'Acme');
  await setStatus(dir, 'PED-001', 'Discovery', NOW);
  assert.equal((await getPedido(dir, 'PED-001')).status, 'Discovery');
});
