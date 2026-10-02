import test from 'node:test';
import assert from 'node:assert/strict';
import { ForbiddenError, InputError, chatInput, checkPostRequest, quoteArgs, searchArgs } from '../server/lib/validate.js';

const ORIGINS = new Set(['http://127.0.0.1:3100', 'http://localhost:3100']);
const JSON_HEADERS = { 'content-type': 'application/json' };

test('checkPostRequest aceita o proprio painel e clientes sem Origin', () => {
  assert.doesNotThrow(() => checkPostRequest({ ...JSON_HEADERS, origin: 'http://127.0.0.1:3100' }, ORIGINS));
  assert.doesNotThrow(() => checkPostRequest({ ...JSON_HEADERS, 'content-type': 'application/json; charset=utf-8' }, ORIGINS));
  assert.doesNotThrow(() => checkPostRequest(JSON_HEADERS, ORIGINS));
});

test('checkPostRequest bloqueia Origin de outro site, inclusive "null"', () => {
  assert.throws(() => checkPostRequest({ ...JSON_HEADERS, origin: 'https://evil.com' }, ORIGINS), ForbiddenError);
  assert.throws(() => checkPostRequest({ ...JSON_HEADERS, origin: 'null' }, ORIGINS), ForbiddenError);
  assert.throws(() => checkPostRequest({ ...JSON_HEADERS, origin: 'http://127.0.0.1:9999' }, ORIGINS), ForbiddenError);
});

test('checkPostRequest exige Content-Type JSON (text/plain evita o preflight)', () => {
  assert.throws(() => checkPostRequest({ 'content-type': 'text/plain' }, ORIGINS), InputError);
  assert.throws(() => checkPostRequest({}, ORIGINS), InputError);
});

const params = obj => new URLSearchParams(obj);

test('searchArgs monta os argumentos e coloca "--" antes do texto', () => {
  const args = searchArgs(params({ q: 'whatsapp imobiliaria', integration: 'gmail', ai: '1', max: 'medio', limit: '5' }));
  assert.deepEqual(args, ['--json', '--integration', 'gmail', '--ai', '--max-complexity', 'medio', '--limit', '5', '--', 'whatsapp imobiliaria']);
});

test('searchArgs nao deixa o texto virar opcao', () => {
  const args = searchArgs(params({ q: '--limit 999' }));
  assert.equal(args.at(-2), '--');
  assert.equal(args.at(-1), '--limit 999');
});

test('searchArgs rejeita consulta vazia, longa, integracao e complexidade invalidas, limite fora da faixa', () => {
  assert.throws(() => searchArgs(params({ q: '  ' })), InputError);
  assert.throws(() => searchArgs(params({ q: 'x'.repeat(201) })), InputError);
  assert.throws(() => searchArgs(params({ q: 'a', integration: 'gmail; rm' })), InputError);
  assert.throws(() => searchArgs(params({ q: 'a', max: 'enorme' })), InputError);
  assert.throws(() => searchArgs(params({ q: 'a', limit: '0' })), InputError);
  assert.throws(() => searchArgs(params({ q: 'a', limit: '21' })), InputError);
  assert.throws(() => searchArgs(new URLSearchParams()), InputError);
});

test('quoteArgs monta os argumentos com opcionais', () => {
  assert.deepEqual(
    quoteArgs({ complexity: 'medio', hours: 20, adaptHours: 10, clientSaving: 3000 }),
    ['--json', '--complexity', 'medio', '--hours', '20', '--adapt-hours', '10', '--client-saving', '3000'],
  );
  assert.deepEqual(
    quoteArgs({ complexity: 'medio', hours: 20, clientHoursWeek: 15, clientHourlyCost: 50 }),
    ['--json', '--complexity', 'medio', '--hours', '20', '--client-hours-week', '15', '--client-hourly-cost', '50'],
  );
  assert.deepEqual(quoteArgs({ complexity: 'simples', hours: 4 }), ['--json', '--complexity', 'simples', '--hours', '4']);
});

test('quoteArgs rejeita entradas invalidas', () => {
  assert.throws(() => quoteArgs({ complexity: 'x', hours: 5 }), InputError);
  assert.throws(() => quoteArgs({ complexity: 'medio', hours: 0 }), InputError);
  assert.throws(() => quoteArgs({ complexity: 'medio', hours: '5' }), InputError);
  assert.throws(() => quoteArgs({ complexity: 'medio', hours: 5, clientSaving: -1 }), InputError);
  assert.throws(() => quoteArgs({ complexity: 'medio', hours: 5, adaptHours: 9 }), InputError);
  assert.throws(() => quoteArgs({ complexity: 'medio', hours: 5, clientHoursWeek: 15 }), InputError);
  assert.throws(() => quoteArgs(undefined), InputError);
});

test('chatInput valida mensagem e sessao', () => {
  assert.deepEqual(chatInput({ message: ' oi ' }), { message: 'oi', sessionId: null });
  assert.equal(chatInput({ message: 'oi', sessionId: '123e4567-e89b-12d3-a456-426614174000' }).sessionId, '123e4567-e89b-12d3-a456-426614174000');
  assert.throws(() => chatInput({ message: '' }), InputError);
  assert.throws(() => chatInput({ message: 'x'.repeat(4001) }), InputError);
  assert.throws(() => chatInput({ message: 'oi', sessionId: '../etc' }), InputError);
});
