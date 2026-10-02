import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "flowhub"))

import pacote  # noqa: E402
import scan  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "templates" / "n8n"

ORDER = """---
id: PED-009
cliente: Oficina Exemplo
status: Features
---

# PED-009

## Features
| # | Feature | Origem | Critério de aceite | Horas | Fase |
|---|---|---|---|---|---|
| 1 | Base única no Google Sheets (abas Clientes, Leads) | construir | Planilha com colunas | 3 | 1 |
| 2 | Captação de leads | `_raw\\acervo\\leads.json` | Lead entra na aba | 8 | 1 |
| 3 | Lembrete de revisão | `_raw\\acervo\\nao-existe.json` e `../fora.json` | Aviso sem repetição | 8 | 2 |

Total: 19 horas.

## Checklist de entrega
- [ ] LEIA-ME com credenciais
- [ ] Vídeo de handoff gravado

## Horas reais
"""

LEAD_FLOW = {"nodes": [{"name": "Form", "type": "n8n-nodes-base.formTrigger", "parameters": {}},
                       {"name": "Gravar", "type": "n8n-nodes-base.googleSheets", "parameters": {"operation": "append"}}],
             "connections": {"Form": {"main": [[{"node": "Gravar", "type": "main", "index": 0}]]}}}


def make_root(tmp: Path) -> Path:
    (tmp / "vault" / "Pedidos").mkdir(parents=True)
    (tmp / "vault" / "Pedidos" / "PED-009-oficina.md").write_text(ORDER, encoding="utf-8")
    (tmp / "_raw" / "acervo").mkdir(parents=True)
    (tmp / "_raw" / "acervo" / "leads.json").write_text(json.dumps(LEAD_FLOW), encoding="utf-8")
    (tmp / "templates" / "entrega").mkdir(parents=True)
    (tmp / "templates" / "entrega" / "LEIA-ME-entrega.md").write_text("# modelo", encoding="utf-8")
    (tmp / "templates" / "n8n").mkdir(parents=True)
    for source in TEMPLATES.glob("*"):
        (tmp / "templates" / "n8n" / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp


class PacoteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = make_root(Path(self._tmp.name))
        self.result = pacote.generate("PED-009", self.root)
        self.dest = self.root / "projetos" / "oficina-exemplo" / "pacote"
        self.data = json.loads((self.dest / "tarefas.json").read_text(encoding="utf-8"))
        self.tasks = {t["id"]: t for t in self.data["tarefas"]}

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_expected_files(self):
        for name in ("00-LEIA-ME.md", "BACKLOG-DEV.md", "tarefas.json"):
            self.assertTrue((self.dest / name).is_file(), name)
        self.assertEqual(self.result["features"], 3)

    def test_every_dependency_points_to_an_existing_task(self):
        for task in self.tasks.values():
            for dep in task["depende_de"]:
                self.assertIn(dep, self.tasks, f"{task['id']} depende de {dep}")

    def test_task_ids_are_unique(self):
        self.assertEqual(len(self.tasks), len(self.data["tarefas"]))

    def test_dependency_graph_has_no_cycle(self):
        state = {}

        def visit(task_id):
            self.assertNotEqual(state.get(task_id), "open", f"ciclo em {task_id}")
            if state.get(task_id) == "done":
                return
            state[task_id] = "open"
            for dep in self.tasks[task_id]["depende_de"]:
                visit(dep)
            state[task_id] = "done"

        for task_id in self.tasks:
            visit(task_id)

    def test_phase_two_waits_for_phase_one(self):
        self.assertIn("E2-F1-S3-T2", self.tasks["E2-F3-S1-T1"]["depende_de"])
        self.assertIn("E2-F2-S3-T2", self.tasks["E2-F3-S1-T1"]["depende_de"])

    def test_checklist_becomes_delivery_tasks(self):
        titles = [t["titulo"] for t in self.tasks.values() if t["epico"] == "E6"]
        self.assertEqual(titles, ["LEIA-ME com credenciais", "Vídeo de handoff gravado"])

    def test_base_flow_is_explained(self):
        explained = list((self.dest / "fluxos-base").glob("F2-*.md"))
        self.assertEqual(len(explained), 1)
        self.assertIn("Gatilho: formulário", explained[0].read_text(encoding="utf-8"))

    def test_missing_and_escaping_references_are_reported_not_fatal(self):
        readme = (self.dest / "00-LEIA-ME.md").read_text(encoding="utf-8")
        self.assertIn("Feature 3", readme)

    def test_feature_detail_in_parentheses_does_not_pick_lead_template(self):
        self.assertNotIn("captacao-de-leads", self.tasks["E2-F1-S1-T1"]["prompt"])
        self.assertIn("lembrete-diario", self.tasks["E2-F3-S1-T1"]["prompt"])

    def test_templates_copied_and_failure_alert_always_present(self):
        self.assertTrue((self.dest / "templates" / "n8n" / "alerta-de-falha.json").is_file())

    def test_regeneration_keeps_previous_package_as_backup(self):
        stale = self.dest / "BACKLOG-DEV.md"
        stale.write_text("marcado a mao [x]", encoding="utf-8")
        pacote.generate("PED-009", self.root)
        pacote.generate("PED-009", self.root)  # duas geracoes seguidas nao colidem
        backups = list(self.dest.parent.glob("pacote.bak-*"))
        self.assertEqual(len(backups), 2)
        self.assertTrue(any("marcado a mao" in (b / "BACKLOG-DEV.md").read_text(encoding="utf-8") for b in backups))
        self.assertNotIn("marcado a mao", stale.read_text(encoding="utf-8"))
        self.assertEqual(list(self.dest.parent.glob(".pacote-tmp-*")), [])

    def test_references_outside_raw_are_rejected_without_touching_disk(self):
        for bad in (r"\\servidor\share\x.json", r"C:\Windows\x.json", "/etc/x.json", "_raw/../fora.json"):
            self.assertIsNone(pacote.resolve_reference(bad, self.root), bad)
        self.assertIsNotNone(pacote.resolve_reference("_raw\\acervo\\leads.json", self.root))

    def test_order_id_with_trailing_newline_or_unicode_digits_is_rejected(self):
        for bad in ("PED-009\n", "PED-٠٠٩"):
            with self.assertRaises(ValueError):
                pacote.find_order(bad, self.root)

    def test_rejects_bad_order_id_and_missing_order(self):
        with self.assertRaises(ValueError):
            pacote.generate("../PED-009", self.root)
        with self.assertRaises(FileNotFoundError):
            pacote.generate("PED-777", self.root)

    def test_malformed_and_duplicate_feature_rows_are_refused_not_dropped(self):
        header = "---\nid: PED-011\ncliente: X\n---\n\n## Features\n| # | Feature | Origem | Critério | Horas | Fase |\n|---|---|---|---|---|---|\n"
        for name, rows in (("cinco", "| 1 | A | construir | ok | 3 |\n"),
                           ("dup", "| 1 | A | construir | ok | 3 | 1 |\n| 1 | B | construir | ok | 3 | 1 |\n")):
            path = self.root / "vault" / "Pedidos" / "PED-011-x.md"
            path.write_text(header + rows, encoding="utf-8")
            with self.assertRaises(ValueError, msg=name):
                pacote.generate("PED-011", self.root)

    def test_two_references_with_same_or_non_ascii_name_do_not_overwrite_each_other(self):
        (self.root / "_raw" / "acervo" / "copia").mkdir()
        for path in ("acervo/leads.json", "acervo/copia/leads.json", "acervo/копия.json"):
            target = self.root / "_raw" / path
            target.write_text(json.dumps(LEAD_FLOW), encoding="utf-8")
        text = ORDER.replace("`_raw\\acervo\\leads.json`", "`_raw\\acervo\\leads.json` `_raw\\acervo\\copia\\leads.json` `_raw\\acervo\\копия.json`")
        (self.root / "vault" / "Pedidos" / "PED-009-oficina.md").write_text(text, encoding="utf-8")
        pacote.generate("PED-009", self.root)
        self.assertEqual(len(list((self.dest / "fluxos-base").glob("F2-*.md"))), 3)

    def test_delivery_agent_follows_the_item(self):
        self.assertEqual(pacote.delivery_agent("Scanner de credenciais limpo"), "qa-fluxos")
        self.assertEqual(pacote.delivery_agent("LEIA-ME com credenciais"), "construtor-n8n")
        self.assertEqual(pacote.delivery_agent("Vídeo de handoff"), pacote.HUMAN)

    def test_order_without_features_is_refused(self):
        path = self.root / "vault" / "Pedidos" / "PED-010-vazio.md"
        path.write_text("---\nid: PED-010\ncliente: X\n---\n\n## Features\n| # | Feature |\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            pacote.generate("PED-010", self.root)


class TemplatesTest(unittest.TestCase):
    def test_each_template_is_valid_and_connected(self):
        files = sorted(TEMPLATES.glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            names = [n["name"] for n in data["nodes"]]
            self.assertEqual(len(names), len(set(names)), path.name)
            for source, kinds in data["connections"].items():
                self.assertIn(source, names, path.name)
                for outputs in kinds["main"]:
                    for target in outputs:
                        self.assertIn(target["node"], names, path.name)

    def test_templates_pass_the_credential_scanner(self):
        findings, invalid, total = scan.scan_paths([str(TEMPLATES)])
        self.assertEqual((len(findings), invalid), (0, []))
        self.assertGreaterEqual(total, 3)


if __name__ == "__main__":
    unittest.main()
