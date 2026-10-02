export const COMPLEXITIES = ['simples', 'medio', 'complexo'];

const MAX_QUERY = 200;
const MAX_MESSAGE = 4000;
const MAX_LIMIT = 20;
const DEFAULT_LIMIT = 8;
const MAX_HOURS = 1000;
const MAX_SAVING = 10_000_000;
const INTEGRATION_RE = /^[A-Za-z0-9]{1,40}$/;
const SESSION_RE = /^[0-9a-f-]{8,64}$/i;

const JSON_CONTENT_TYPE = /^application\/json\b/i;

/** Entrada invalida; `field` diz qual campo da tela corrigir. */
export class InputError extends Error {
  constructor(message, field) {
    super(message);
    this.field = field;
  }
}
export class ForbiddenError extends Error {}

/** Erro esperado, com mensagem segura para o usuario e codigo HTTP proprio. */
export class ServiceError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.status = status;
  }
}

/**
 * Bloqueia POST vindo de outro site (CSRF): o Origin precisa ser o proprio painel e o corpo,
 * JSON, o que obriga o navegador a fazer preflight. Clientes sem Origin (curl, Node) passam.
 */
export function checkPostRequest(headers, allowedOrigins) {
  const { origin } = headers;
  if (origin !== undefined && !allowedOrigins.has(origin)) throw new ForbiddenError('Origem não permitida');
  if (!JSON_CONTENT_TYPE.test(headers['content-type'] ?? '')) {
    throw new InputError('Content-Type deve ser application/json');
  }
}

function requiredText(value, name, max) {
  if (typeof value !== 'string' || !value.trim()) throw new InputError(`Campo "${name}" é obrigatório`);
  if (value.length > max) throw new InputError(`Campo "${name}" passa de ${max} caracteres`);
  return value.trim();
}

function finiteNumber(value, name, { min, max }) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new InputError(`Campo "${name}" deve ser um número entre ${min} e ${max}`);
  }
  return value;
}

/** Monta os argumentos de `flowhub/search.py`. O "--" impede que o texto vire opcao. */
export function searchArgs(params) {
  const query = requiredText(params.get('q'), 'q', MAX_QUERY);
  const args = ['--json'];

  const integration = params.get('integration');
  if (integration) {
    if (!INTEGRATION_RE.test(integration)) throw new InputError('Integração inválida');
    args.push('--integration', integration);
  }
  if (params.get('ai') === '1') args.push('--ai');

  const maxComplexity = params.get('max');
  if (maxComplexity) {
    if (!COMPLEXITIES.includes(maxComplexity)) throw new InputError('Complexidade inválida');
    args.push('--max-complexity', maxComplexity);
  }

  const limit = Number(params.get('limit') ?? DEFAULT_LIMIT);
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
    throw new InputError(`Limite deve ser um inteiro entre 1 e ${MAX_LIMIT}`);
  }
  args.push('--limit', String(limit), '--', query);
  return args;
}

const MAX_HOURS_WEEK = 168;
const MAX_HOURLY_COST = 100_000;
const isGiven = value => value !== undefined && value !== null && value !== '';

/** Economia do cliente: informada direto ou como horas por semana x custo da hora (o script calcula). */
function savingArgs(body) {
  if (isGiven(body.clientSaving)) {
    return ['--client-saving', String(finiteNumber(body.clientSaving, 'clientSaving', { min: 1, max: MAX_SAVING }))];
  }
  if (isGiven(body.clientHoursWeek) || isGiven(body.clientHourlyCost)) {
    const week = finiteNumber(body.clientHoursWeek, 'clientHoursWeek', { min: 0.5, max: MAX_HOURS_WEEK });
    const cost = finiteNumber(body.clientHourlyCost, 'clientHourlyCost', { min: 1, max: MAX_HOURLY_COST });
    return ['--client-hours-week', String(week), '--client-hourly-cost', String(cost)];
  }
  return [];
}

/** Monta os argumentos de `flowhub/quote.py`. `adaptHours` sao as horas (do total) que partem de fluxo pronto. */
export function quoteArgs(body) {
  if (!COMPLEXITIES.includes(body?.complexity)) throw new InputError('Complexidade inválida');
  const hours = finiteNumber(body.hours, 'hours', { min: 0.5, max: MAX_HOURS });
  const args = ['--json', '--complexity', body.complexity, '--hours', String(hours)];
  if (isGiven(body.adaptHours)) {
    args.push('--adapt-hours', String(finiteNumber(body.adaptHours, 'adaptHours', { min: 0, max: hours })));
  }
  return [...args, ...savingArgs(body)];
}

const FIELD_LABELS = {
  cliente: 'Cliente', problema: 'Problema', horasSemana: 'Horas por semana', custoHora: 'Custo da hora',
  ferramentas: 'Ferramentas', gatilho: 'Gatilho', urgencia: 'Urgência', faixaOrcamento: 'Faixa de orçamento',
  quemOpera: 'Quem opera depois',
};
const URGENCIES = ['baixa', 'media', 'alta'];
const MAX_NAME = 80;
const MAX_LINE = 300;
const MAX_STORY = 2000;
const PATH_CHARS = /[\\/]|\.\./;
const HEADER_UNSAFE = new RegExp(`[\r\n${String.fromCharCode(0x2028, 0x2029, 0x85)}\v\f#]`); // mesmo conjunto de frontmatter.js (UNSAFE_HEADER_VALUE)

function formText(body, field, max, { required = true, headerSafe = false } = {}) {
  const label = FIELD_LABELS[field];
  const value = typeof body[field] === 'string' ? body[field].trim() : '';
  if (!value) {
    if (required) throw new InputError(`${label} é obrigatório`, field);
    return '';
  }
  if (value.length > max) throw new InputError(`${label} passa de ${max} caracteres`, field);
  if (headerSafe && HEADER_UNSAFE.test(value)) throw new InputError(`${label} não pode ter quebra de linha nem "#"`, field);
  return value;
}

function formNumber(body, field, { min, max }) {
  const value = body[field];
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new InputError(`${FIELD_LABELS[field]} deve ser um número entre ${min} e ${max}`, field);
  }
  return value;
}

/** Valida o formulario "Novo pedido" (INT-06). Nada e gravado se qualquer campo falhar. */
export function novoPedidoInput(body) {
  const data = body ?? {};
  const cliente = formText(data, 'cliente', MAX_NAME, { headerSafe: true });
  if (PATH_CHARS.test(cliente)) throw new InputError('Cliente não pode ter barras nem ".."', 'cliente');
  const urgencia = typeof data.urgencia === 'string' ? data.urgencia : '';
  if (!URGENCIES.includes(urgencia)) throw new InputError('Escolha a urgência (baixa, média ou alta)', 'urgencia');
  return {
    cliente,
    problema: formText(data, 'problema', MAX_STORY),
    horasSemana: formNumber(data, 'horasSemana', { min: 0.5, max: MAX_HOURS_WEEK }),
    custoHora: formNumber(data, 'custoHora', { min: 1, max: MAX_HOURLY_COST }),
    ferramentas: formText(data, 'ferramentas', MAX_LINE),
    gatilho: formText(data, 'gatilho', MAX_LINE),
    urgencia,
    faixaOrcamento: formText(data, 'faixaOrcamento', MAX_NAME, { required: false, headerSafe: true }),
    quemOpera: formText(data, 'quemOpera', MAX_LINE),
  };
}

/** Valida a mensagem do chat e o id de sessao opcional. */
export function chatInput(body) {
  const message = requiredText(body?.message, 'message', MAX_MESSAGE);
  const sessionId = body.sessionId ?? null;
  if (sessionId !== null && (typeof sessionId !== 'string' || !SESSION_RE.test(sessionId))) {
    throw new InputError('Sessão inválida');
  }
  return { message, sessionId };
}
