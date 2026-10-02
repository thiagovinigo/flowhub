import test from 'node:test';
import assert from 'node:assert/strict';
import { parseFrontmatter, setFrontmatterField } from '../server/lib/frontmatter.js';
import { appendLine, appendTableRow, listChecklist, readTableRows, setChecklistItem } from '../server/lib/secoes.js';
import { STATUSES, isBackward, transitionProblems } from '../server/lib/transicoes.js';

const DOC = `---
id: PED-001
status: Pedido   # comentario
setup:
---

# PED-001

## Checklist de entrega
- [ ] primeiro
- [x] segundo

## Horas reais
| Data | Horas | Atividade |
|---|---|---|
| 2026-10-01 | 2 | a |

## Histórico
-
`;

test('setFrontmatterField troca o valor, preserva o comentario e nao toca no corpo', () => {
  const updated = setFrontmatterField(DOC, 'status', 'Orçado');
  assert.equal(parseFrontmatter(updated).status, 'Orçado');
  assert.match(updated, /^status: Orçado {3}# comentario$/m);
  assert.ok(updated.includes('- [x] segundo'));
});

test('setFrontmatterField recusa valor com quebra de linha, inclusive as Unicode, e "#"', () => {
  for (const value of ['a\nb', 'a\rb', 'a b', 'a b', 'a\u0085b', 'a#b']) {
    assert.throws(() => setFrontmatterField(DOC, 'status', value), RangeError, JSON.stringify(value));
  }
});

test('setFrontmatterField acrescenta a chave quando ela nao existe e rejeita nome invalido', () => {
  assert.equal(parseFrontmatter(setFrontmatterField(DOC, 'comprovante', 'pix.png')).comprovante, 'pix.png');
  assert.throws(() => setFrontmatterField(DOC, 'a.b', 'x'), RangeError);
  assert.throws(() => setFrontmatterField(DOC, '.*', 'x'), RangeError);
});

test('appendLine troca o marcador "-" do modelo e depois acrescenta no fim da secao', () => {
  const first = appendLine(DOC, 'Histórico', '- 2026-10-01 · criado');
  const second = appendLine(first, 'Histórico', '- 2026-10-02 · mudou');
  const section = second.split('## Histórico')[1];
  assert.ok(section.includes('- 2026-10-01 · criado\n- 2026-10-02 · mudou'));
  assert.ok(!/^-$/m.test(section));
});

test('appendLine cria a secao quando ela nao existe e respeita CRLF', () => {
  assert.match(appendLine('# x\n', 'Histórico', '- a'), /## Histórico\n- a\n$/);
  const crlf = appendLine(DOC.replace(/\n/g, '\r\n'), 'Histórico', '- a');
  assert.ok(crlf.includes('\r\n') && !/[^\r]\n/.test(crlf));
});

test('listChecklist indexa os itens e setChecklistItem altera so o escolhido', () => {
  assert.deepEqual(listChecklist(DOC), [
    { index: 0, label: 'primeiro', done: false },
    { index: 1, label: 'segundo', done: true },
  ]);
  const updated = setChecklistItem(DOC, 0, true);
  assert.deepEqual(listChecklist(updated).map(item => item.done), [true, true]);
  assert.throws(() => setChecklistItem(DOC, 7, true), RangeError);
});

test('appendTableRow e readTableRows: acrescenta, limpa barras e le so as linhas de dados', () => {
  const updated = appendTableRow(DOC, 'Horas reais', ['2026-10-02', '1.5', 'a | b\nc']);
  assert.deepEqual(readTableRows(updated, 'Horas reais'), [['2026-10-01', '2', 'a'], ['2026-10-02', '1.5', 'a / b c']]);
  assert.throws(() => appendTableRow(DOC, 'Orçamento', ['x']), /Tabela não encontrada/);
});

const DONE = [{ index: 0, label: 'a', done: true }];
const ACEITE = { aceite_em: '2026-10-01', aceite_canal: 'email', versao_proposta: 'PED-001-v1', aceite_evidencia: 'ok.png' };

test('voltar de estado e sempre permitido', () => {
  assert.deepEqual(transitionProblems('Entregue', 'Pedido', {}, []), []);
  assert.ok(isBackward('Aprovado', 'Orçado'));
  assert.ok(!isBackward('Orçado', 'Aprovado'));
});

test('Aprovado exige versao, data, canal e evidencia do aceite', () => {
  assert.equal(transitionProblems('Orçado', 'Aprovado', {}, []).length, 4);
  assert.deepEqual(transitionProblems('Orçado', 'Aprovado', ACEITE, []), []);
});

test('Em construcao exige entrada paga e comprovante, alem do aceite (mesmo pulando estados)', () => {
  const problems = transitionProblems('Pedido', 'Em construção', {}, []);
  assert.ok(problems.some(item => item.includes('aceite_em')));
  assert.ok(problems.some(item => item.includes('entrada_paga')));
  assert.ok(problems.some(item => item.includes('comprovante')));
  assert.deepEqual(transitionProblems('Aprovado', 'Em construção', { ...ACEITE, entrada_paga: 'true', comprovante: 'pix.png' }, []), []);
  assert.ok(transitionProblems('Aprovado', 'Em construção', { ...ACEITE, entrada_paga: 'false', comprovante: 'pix.png' }, []).length > 0);
});

test('Entregue exige o checklist completo', () => {
  const data = { ...ACEITE, entrada_paga: 'true', comprovante: 'pix.png' };
  assert.ok(transitionProblems('Em construção', 'Entregue', data, [{ done: true }, { done: false }])[0].includes('1 de 2'));
  assert.ok(transitionProblems('Em construção', 'Entregue', data, [])[0].includes('não existe'));
  assert.deepEqual(transitionProblems('Em construção', 'Entregue', data, DONE), []);
});

test('STATUSES mantem a ordem do kanban', () => {
  assert.deepEqual(STATUSES.slice(0, 2), ['Pedido', 'Discovery']);
  assert.equal(STATUSES.at(-1), 'Suporte');
});
