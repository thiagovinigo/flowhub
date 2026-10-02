import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { delimiter, join } from 'node:path';

const NPM_CLAUDE_EXE = join('node_modules', '@anthropic-ai', 'claude-code', 'bin', 'claude.exe');

/**
 * Localiza o executavel real do Claude CLI. No Windows o comando `claude` e um atalho .cmd,
 * que o Node nao executa sem shell; por isso procuramos o .exe por tras dele.
 */
export function findClaude(env = process.env) {
  if (env.FLOWHUB_CLAUDE && existsSync(env.FLOWHUB_CLAUDE)) return env.FLOWHUB_CLAUDE;
  const candidates = process.platform === 'win32' ? ['claude.exe', NPM_CLAUDE_EXE] : ['claude'];
  for (const dir of (env.PATH || env.Path || '').split(delimiter)) {
    if (!dir) continue;
    for (const name of candidates) {
      const full = join(dir, name);
      if (existsSync(full)) return full;
    }
  }
  return null;
}

const MAX_OUTPUT_CHARS = 2_000_000;

/** Executa um programa sem shell, com limites de tempo e de saida, e devolve o stdout. */
export function run(command, args, { cwd, timeoutMs = 30_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
    });
    // setEncoding decodifica por caractere: sem isso um acento cortado entre dois pedacos vira "�".
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    let stdout = '';
    let stderr = '';
    const fail = error => { child.kill(); clearTimeout(timer); reject(error); };
    const timer = setTimeout(() => fail(new Error(`Tempo esgotado (${Math.round(timeoutMs / 1000)} s)`)), timeoutMs);
    child.stdout.on('data', chunk => {
      stdout += chunk;
      if (stdout.length > MAX_OUTPUT_CHARS) fail(new Error('Saída grande demais'));
    });
    child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-MAX_OUTPUT_CHARS); });
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('close', code => {
      clearTimeout(timer);
      if (code === 0) resolve(stdout);
      else reject(new Error(stderr.trim() || `Processo terminou com codigo ${code}`));
    });
  });
}
