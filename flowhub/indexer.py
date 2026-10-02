"""Indexa todos os fluxos n8n de _raw/ em flowhub/catalog.db (SQLite + FTS5).

Uso: python flowhub/indexer.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

from perfil import build_profile
from scan import read_documents, scan_document, severity

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "_raw"
DB_PATH = ROOT / "flowhub" / "catalog.db"

TRIGGER_HINTS = ("trigger", "webhook", "cron", "schedule", "manualtrigger", "chattrigger")
IGNORED_NODE_TYPES = {"stickyNote", "noOp", "set", "if", "merge", "code", "function",
                      "functionItem", "switch", "splitInBatches", "wait", "manualTrigger"}
SCHEMA = """
DROP TABLE IF EXISTS flows;
DROP TABLE IF EXISTS flows_fts;
CREATE TABLE flows (
    id INTEGER PRIMARY KEY,
    sha TEXT UNIQUE,
    name TEXT,
    category TEXT,
    path TEXT,
    source TEXT,
    triggers TEXT,
    integrations TEXT,
    credentials TEXT,
    uses_ai INTEGER,
    node_count INTEGER,
    complexity TEXT,
    notes TEXT,
    secrets_high INTEGER DEFAULT 0,
    secrets_medium INTEGER DEFAULT 0,
    profile TEXT,
    copies INTEGER DEFAULT 1
);
CREATE VIRTUAL TABLE flows_fts USING fts5(
    name, category, integrations, notes, content='flows', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
"""


def short_type(node_type: str) -> str:
    return node_type.split(".")[-1]


def classify_complexity(node_count: int, uses_ai: bool) -> str:
    score = node_count + (8 if uses_ai else 0)
    if score <= 8:
        return "simples"
    if score <= 25:
        return "medio"
    return "complexo"


def analyse(data: dict) -> dict | None:
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return None
    nodes = [n for n in nodes if isinstance(n, dict)]
    types = [short_type(n.get("type", "")) for n in nodes]
    triggers = sorted({t for t in types if any(h in t.lower() for h in TRIGGER_HINTS)})
    integrations = sorted({t for t in types if t not in IGNORED_NODE_TYPES and t not in triggers})
    credentials = sorted({c for n in nodes for c in (n.get("credentials") or {}).keys()})
    uses_ai = any("langchain" in n.get("type", "").lower() for n in nodes)
    notes = " ".join(
        str((n.get("parameters") or {}).get("content", ""))
        for n in nodes if short_type(n.get("type", "")) == "stickyNote"
    )
    notes = re.sub(r"[#*`>\[\]()!_-]+", " ", notes)
    notes = re.sub(r"\s+", " ", notes).strip()[:1500]
    functional = [t for t in types if t != "stickyNote"]
    return {
        "triggers": triggers,
        "integrations": integrations,
        "credentials": credentials,
        "uses_ai": uses_ai,
        "node_count": len(functional),
        "complexity": classify_complexity(len(functional), uses_ai),
        "notes": notes,
    }


def content_hash(data: dict) -> str:
    skeleton = json.dumps(
        [(n.get("type"), n.get("name"), n.get("parameters")) for n in data.get("nodes", []) if isinstance(n, dict)],
        sort_keys=True, ensure_ascii=False, default=str,
    )
    return hashlib.sha1(skeleton.encode("utf-8")).hexdigest()


def category_of(path: Path, source_root: Path) -> str:
    rel = path.relative_to(source_root).parent
    return " / ".join(rel.parts) if rel.parts else "(raiz)"


def iter_flow_files():
    for source_dir in sorted(RAW.glob("src*")):
        for path in source_dir.rglob("*.json"):
            if "__MACOSX" in path.parts:
                continue
            yield source_dir, path


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    inserted = skipped = invalid = 0
    for source_dir, path in iter_flow_files():
        try:
            documents = read_documents(path)
        except (OSError, ValueError) as exc:
            invalid += 1
            print(f"[invalido] {path.name}: {exc}", file=sys.stderr)
            continue
        for data in documents:
            info = analyse(data)
            if info is None:
                skipped += 1
                continue
            sha = content_hash(data)
            existing = conn.execute("SELECT id FROM flows WHERE sha=?", (sha,)).fetchone()
            if existing:
                conn.execute("UPDATE flows SET copies = copies + 1 WHERE id=?", (existing[0],))
                continue
            name = data.get("name") or path.stem
            risks = [severity(finding.kind) for finding in scan_document(data)]
            category = category_of(path, source_dir)
            profile = json.dumps(build_profile(data, info, risks, category), ensure_ascii=False)
            conn.execute(
                "INSERT INTO flows (sha,name,category,path,source,triggers,integrations,credentials,"
                "uses_ai,node_count,complexity,notes,secrets_high,secrets_medium,profile) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sha, name, category, str(path.relative_to(ROOT)), source_dir.name,
                 ",".join(info["triggers"]), ",".join(info["integrations"]), ",".join(info["credentials"]),
                 int(info["uses_ai"]), info["node_count"], info["complexity"], info["notes"],
                 risks.count("alto"), risks.count("médio"), profile),
            )
            inserted += 1
    conn.execute("INSERT INTO flows_fts(rowid,name,category,integrations,notes) "
                 "SELECT id,name,category,integrations,notes FROM flows")
    conn.commit()
    ai = conn.execute("SELECT COUNT(*) FROM flows WHERE uses_ai=1").fetchone()[0]
    conn.close()
    print(f"unicos={inserted} (com IA={ai}) | sem nodes={skipped} | JSON invalido={invalid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
