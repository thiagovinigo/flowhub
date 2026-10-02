"""Busca fluxos no catalogo. Usado direto no terminal e como ferramenta do agente.

Exemplos:
  python flowhub/search.py "whatsapp atendimento imobiliaria"
  python flowhub/search.py "proposta comercial" --integration gmail --max-complexity medio
  python flowhub/search.py "rag documentos" --ai --limit 5 --json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "catalog.db"
COMPLEXITY_ORDER = {"simples": 0, "medio": 1, "complexo": 2}
MIN_TERM_LENGTH = 3
CANDIDATE_POOL = 200


def build_match(query: str) -> str:
    """Transforma texto livre em uma consulta FTS5 (OR entre termos, prefixo)."""
    terms = [t for t in re.findall(r"\w+", query, flags=re.UNICODE) if len(t) >= MIN_TERM_LENGTH]
    return " OR ".join(f'"{t}"*' for t in terms)


def search(query: str, *, integration: str | None = None, only_ai: bool = False,
           max_complexity: str | None = None, limit: int = 8) -> list[dict]:
    match = build_match(query)
    if not match:
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT f.*, bm25(flows_fts, 6.0, 2.0, 3.0, 1.0) AS score "
            "FROM flows_fts JOIN flows f ON f.id = flows_fts.rowid "
            "WHERE flows_fts MATCH ? ORDER BY score LIMIT ?",
            (match, CANDIDATE_POOL),
        ).fetchall()
    finally:
        conn.close()
    results = []
    for row in rows:
        if integration and integration.lower() not in row["integrations"].lower():
            continue
        if only_ai and not row["uses_ai"]:
            continue
        if max_complexity and COMPLEXITY_ORDER[row["complexity"]] > COMPLEXITY_ORDER[max_complexity]:
            continue
        results.append({
            "id": row["id"], "name": row["name"], "category": row["category"],
            "complexity": row["complexity"], "nodes": row["node_count"],
            "triggers": row["triggers"], "integrations": row["integrations"],
            "credentials": row["credentials"], "uses_ai": bool(row["uses_ai"]),
            "path": row["path"], "notes": row["notes"][:240],
            "secrets_high": row["secrets_high"], "secrets_medium": row["secrets_medium"],
            "profile": json.loads(row["profile"]) if row["profile"] else None,
        })
        if len(results) >= limit:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query")
    parser.add_argument("--integration", help="exige esta integracao (ex.: gmail, whatsapp, googleSheets)")
    parser.add_argument("--ai", action="store_true", help="somente fluxos com IA")
    parser.add_argument("--max-complexity", choices=list(COMPLEXITY_ORDER))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="saida JSON (para o agente)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not DB_PATH.exists():
        print("catalog.db nao existe. Rode: python flowhub/indexer.py", file=sys.stderr)
        return 1
    results = search(args.query, integration=args.integration, only_ai=args.ai,
                     max_complexity=args.max_complexity, limit=args.limit)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("Nenhum fluxo encontrado. Tente menos termos ou sinonimos.")
        return 0
    for i, r in enumerate(results, 1):
        ai = " IA" if r["uses_ai"] else ""
        print(f"{i}. [{r['complexity']}{ai}] {r['name']}  ({r['nodes']} nodes)")
        print(f"   {r['category']}")
        print(f"   gatilho: {r['triggers'] or '-'} | integra: {r['integrations'][:110]}")
        print(f"   {r['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
