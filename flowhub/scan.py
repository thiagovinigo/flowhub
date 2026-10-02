"""Scanner de segredos e dados de terceiros em fluxos n8n (CAT-03).

Procura tokens, chaves de API, e-mails, IDs de credencial, URLs de webhook e IDs de
planilha/pasta do Google. Mostra nome do no, campo e um trecho MASCARADO (nunca o valor inteiro).
Sai com codigo 0 quando tudo esta limpo; 1 se achar algo ou se algum JSON for invalido.

Exemplos:
  python flowhub/scan.py projetos/acme/fluxo.json
  python flowhub/scan.py projetos/acme --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

MASK_START = 3
MASK_END = 2
MIN_REVEAL_LENGTH = 24   # abaixo disso nada do valor aparece: 5 caracteres de 10 seriam metade do segredo
MAX_SCAN_CHARS = 20_000  # teto por texto: regex sobre blobs enormes ficaria quadratica
MIN_SENSITIVE_LENGTH = 8
MIN_ID_LENGTH = 20
FLOW_LEVEL = "(fluxo)"

# Valores que sao modelo, expressao do n8n ou exemplo, nao segredo.
PLACEHOLDER_RE = re.compile(
    r"\{\{|\}\}|SEU_|SUA_|YOUR_|COLE_AQUI|<[^>\s]+>|REPLACE|CHANGE_?ME|X{4,}|example\.(?:com|org|net)|exemplo\.",
    re.IGNORECASE,
)

# (tipo, expressao). Cada uma e aplicada a todo texto do fluxo.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("chave de API do Google", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("chave de API (sk-)", re.compile(r"sk-(?:ant-)?[A-Za-z0-9_\-]{20,}")),
    ("token do GitHub", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("token do Slack", re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("chave da AWS", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("Bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("e-mail", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("webhook de chat (Slack/Discord)", re.compile(
        r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+|https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+")),
    ("URL de webhook do n8n", re.compile(r"https?://[^\s\"']+/webhook(?:-test)?/[0-9a-fA-F\-]{8,}")),
    ("ID de arquivo ou pasta do Google", re.compile(
        r"docs\.google\.com/(?:spreadsheets|document|presentation)/d/[A-Za-z0-9_\-]{25,}"
        r"|drive\.google\.com/(?:drive/folders|file/d)/[A-Za-z0-9_\-]{25,}")),
)
SENSITIVE_KEY_RE = re.compile(r"api[_-]?key|token|secret|password|senha|authorization|client[_-]?secret", re.IGNORECASE)
GOOGLE_ID_KEY_RE = re.compile(r"^(?:document|spreadsheet|folder|file|calendar|sheet)Id$")


# Identificadores que todo fluxo exportado do n8n carrega: nao abrem acesso, mas apontam para a
# instancia ou o cliente de origem e devem sair antes da entrega. Todo o resto (chaves, tokens) e grave.
MEDIUM_KINDS = frozenset({
    "e-mail", "ID de credencial do n8n", "ID de webhook do n8n", "URL de webhook do n8n", "ID de arquivo ou pasta do Google",
})


def severity(kind: str) -> str:
    return "médio" if kind in MEDIUM_KINDS else "alto"


@dataclass(frozen=True)
class Finding:
    file: str
    node: str
    field: str
    kind: str
    preview: str


def mask(value: str) -> str:
    """Esconde o valor: abaixo de 24 caracteres some por completo; nos maiores so aparecem 3 do comeco e 2 do fim."""
    text = value.strip()
    if len(text) < MIN_REVEAL_LENGTH:
        return "*" * len(text)
    return f"{text[:MASK_START]}…{text[-MASK_END:]} ({len(text)} car.)"


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value)) or value.strip().startswith("=")


def walk(value, path: str = "", key: str = ""):
    """Gera (caminho, nome_do_campo, texto) para cada string do documento."""
    if isinstance(value, dict):
        for name, child in value.items():
            yield from walk(child, f"{path}.{name}" if path else str(name), str(name))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]", key)
    elif isinstance(value, str):
        yield path, key, value


def scan_text(path: str, key: str, text: str) -> list[tuple[str, str]]:
    """Achados (tipo, trecho_mascarado) de uma unica string."""
    text = text[:MAX_SCAN_CHARS]
    found = []
    for kind, pattern in PATTERNS:
        if kind == "e-mail" and "@" not in text:
            continue
        for match in pattern.finditer(text):
            if not is_placeholder(match.group(0)):
                found.append((kind, mask(match.group(0))))
    if found:
        return found
    if SENSITIVE_KEY_RE.search(key) and len(text) >= MIN_SENSITIVE_LENGTH and not is_placeholder(text):
        return [(f'valor sensível no campo "{key}"', mask(text))]
    if GOOGLE_ID_KEY_RE.match(key) and len(text) >= MIN_ID_LENGTH and not is_placeholder(text):
        return [("ID de arquivo ou pasta do Google", mask(text))]
    return []


def node_strings(node: dict):
    """Textos de um no, incluindo o bloco de credenciais e o id do webhook."""
    yield from walk(node.get("parameters", {}), "parameters")
    for credential_type, credential in (node.get("credentials") or {}).items():
        identifier = credential.get("id") if isinstance(credential, dict) else None
        if identifier and not is_placeholder(str(identifier)):
            yield f"credentials.{credential_type}.id", "credentialId", str(identifier)
    if node.get("webhookId"):
        yield "webhookId", "webhookId", str(node["webhookId"])


def scan_document(data: dict, file: str = "") -> list[Finding]:
    findings: list[Finding] = []

    def add(node: str, path: str, key: str, text: str) -> None:
        if key == "credentialId":
            findings.append(Finding(file, node, path, "ID de credencial do n8n", mask(text)))
        elif key == "webhookId":
            findings.append(Finding(file, node, path, "ID de webhook do n8n", mask(text)))
        else:
            findings.extend(Finding(file, node, path, kind, preview) for kind, preview in scan_text(path, key, text))

    for node in data.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        for path, key, text in node_strings(node):
            add(str(node.get("name", "?")), path, key, text)
    rest = {name: value for name, value in data.items() if name != "nodes"}
    for path, key, text in walk(rest):
        add(FLOW_LEVEL, path, key, text)
    return findings


def read_documents(path: Path) -> list[dict]:
    """Le um arquivo com um fluxo, uma lista deles ou varios objetos concatenados (como no acervo).

    No Windows o prefixo \\\\?\\ permite caminhos com mais de 260 caracteres. Lixo depois de um
    fluxo valido e ignorado; so um arquivo sem nenhum JSON valido gera erro.
    """
    target = Path("\\\\?\\" + str(path.resolve())) if os.name == "nt" else path
    text = target.read_text(encoding="utf-8-sig")
    decoder = json.JSONDecoder()
    docs, pos = [], 0
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        try:
            obj, pos = decoder.raw_decode(text, pos)
        except ValueError:
            if docs:
                break
            raise
        docs.extend(obj if isinstance(obj, list) else [obj])
    return [doc for doc in docs if isinstance(doc, dict)]


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        files.extend(sorted(path.rglob("*.json")) if path.is_dir() else [path])
    return files


def scan_paths(paths: list[str]) -> tuple[list[Finding], list[str], int]:
    """Varre arquivos e pastas. Devolve (achados, arquivos_invalidos, total_de_arquivos)."""
    findings: list[Finding] = []
    invalid: list[str] = []
    files = collect_files(paths)
    for file in files:
        try:
            documents = read_documents(file)
        except (OSError, ValueError) as error:
            invalid.append(f"{file}: {error}")
            continue
        if not documents:  # um JSON que nao e fluxo nunca pode contar como "limpo"
            invalid.append(f"{file}: não contém nenhum fluxo (objeto JSON)")
            continue
        for data in documents:
            findings.extend(scan_document(data, str(file)))
    return findings, invalid, len(files)


def render(findings: list[Finding], invalid: list[str], total: int) -> str:
    checked = ", ".join(kind for kind, _ in PATTERNS) + ", valores em campos sensíveis, IDs de credencial e de webhook"
    lines: list[str] = []
    for finding in findings:
        lines.append(f"{finding.file}\n  [{severity(finding.kind)}] [nó \"{finding.node}\" · {finding.field}] {finding.kind}: {finding.preview}")
    for problem in invalid:
        lines.append(f"JSON inválido: {problem}")
    high = sum(1 for finding in findings if severity(finding.kind) == "alto")
    status = ("LIMPO" if not findings and not invalid
              else f"{high} segredo(s) de gravidade alta, {len(findings) - high} identificador(es) de gravidade média, {len(invalid)} arquivo(s) inválido(s)")
    lines.append(f"\nResultado: {status} em {total} arquivo(s).")
    lines.append(f"Padrões verificados: {checked}.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="arquivos .json ou pastas")
    parser.add_argument("--json", action="store_true", help="saida JSON")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    findings, invalid, total = scan_paths(args.paths)
    if args.json:
        report = [{**asdict(f), "severity": severity(f.kind)} for f in findings]
        print(json.dumps({"files": total, "findings": report, "invalid": invalid}, ensure_ascii=False))
    else:
        print(render(findings, invalid, total))
    return 0 if not findings and not invalid else 1


if __name__ == "__main__":
    raise SystemExit(main())
