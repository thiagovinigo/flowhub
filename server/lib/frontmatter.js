const FRONT_RE = /^---\r?\n([\s\S]*?)\r?\n---/;
const KEY_RE = /^[a-z_]+$/;
/** Qualquer quebra de linha (inclusive U+2028/U+0085, que o Python tambem trata como linha) ou "#" (comentario). */
export const UNSAFE_HEADER_VALUE = new RegExp(`[\r\n${String.fromCharCode(0x2028, 0x2029, 0x85)}\v\f#]`); // U+2028, U+2029 e U+0085 por codigo: o caractere literal quebraria a regex

/** Le o cabecalho `chave: valor` e descarta comentarios `# ...`. */
export function parseFrontmatter(text) {
  const match = FRONT_RE.exec(text);
  if (!match) return {};
  const data = {};
  for (const line of match[1].split(/\r?\n/)) {
    const pair = /^([A-Za-z_]+):\s*(.*)$/.exec(line);
    if (!pair) continue;
    data[pair[1]] = pair[2].replace(/(^|\s)#.*$/, '').trim();
  }
  return data;
}

/**
 * Troca (ou acrescenta) `chave: valor` no cabecalho, preservando o comentario da linha.
 * Devolve o texto novo; o resto do arquivo fica intacto.
 */
export function setFrontmatterField(text, key, value) {
  if (!KEY_RE.test(key)) throw new RangeError('Nome de campo inválido');
  if (UNSAFE_HEADER_VALUE.test(value)) throw new RangeError('Valor inválido para o cabeçalho');
  const match = FRONT_RE.exec(text);
  if (!match) throw new Error('Pedido sem cabeçalho');
  const lineRe = new RegExp(`^${key}:([^#\\r\\n]*)(#.*)?$`, 'm');
  const header = lineRe.test(match[1])
    ? match[1].replace(lineRe, (_line, _value, comment) => `${key}: ${value}${comment ? `   ${comment}` : ''}`.trimEnd())
    : `${match[1]}\n${key}: ${value}`.trimEnd();
  return text.replace(match[1], () => header);
}
