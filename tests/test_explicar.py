import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "flowhub"))

import explicar  # noqa: E402

FLOW = {
    "name": "Lembrete",
    "nodes": [
        {"name": "Todo dia", "type": "n8n-nodes-base.scheduleTrigger",
         "parameters": {"rule": {"interval": [{"field": "days", "daysInterval": 1, "triggerAtHour": 9}]}}},
        {"name": "Ler clientes", "type": "n8n-nodes-base.googleSheets",
         "parameters": {"operation": "getAll", "documentId": {"value": "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"},
                        "sheetName": {"value": "Clientes"}}},
        {"name": "Vence?", "type": "n8n-nodes-base.if",
         "parameters": {"conditions": {"conditions": [
             {"leftValue": "={{ $json.dias }}", "rightValue": "30", "operator": {"operation": "lte"}}]}}},
        {"name": "Avisar", "type": "n8n-nodes-base.httpRequest",
         "parameters": {"method": "POST", "url": "https://api.exemplo.com/enviar?token=abc"}},
        {"name": "Sem tipo conhecido", "type": "n8n-nodes-base.coisaNova", "parameters": {}},
    ],
    "connections": {
        "Todo dia": {"main": [[{"node": "Ler clientes", "type": "main", "index": 0}]]},
        "Ler clientes": {"main": [[{"node": "Vence?", "type": "main", "index": 0}]]},
        "Vence?": {"main": [[{"node": "Avisar", "type": "main", "index": 0}], []]},
    },
}


class ExplainFlowTest(unittest.TestCase):
    def setUp(self):
        self.text = explicar.explain_flow(FLOW)

    def test_nodes_follow_execution_order(self):
        positions = [self.text.index(f". {name} —") for name in ("Todo dia", "Ler clientes", "Vence?", "Avisar")]
        self.assertEqual(positions, sorted(positions))

    def test_describes_schedule_and_condition(self):
        self.assertIn("a cada 1 dia(s), às 9h", self.text)
        self.assertIn("lte", self.text)

    def test_branch_label_in_diagram(self):
        self.assertIn("-->|sim|", self.text)

    def test_sheet_id_never_printed(self):
        self.assertNotIn("1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789", self.text)
        self.assertIn("ID omitido", self.text)

    def test_http_shows_host_only(self):
        self.assertIn("https://api.exemplo.com", self.text)
        self.assertNotIn("token=abc", self.text)

    def test_unknown_node_type_has_fallback(self):
        self.assertIn("sem descrição pronta", self.text)

    def test_orphan_node_is_still_listed(self):
        self.assertIn("Sem tipo conhecido", self.text)

    def test_secret_in_message_is_omitted(self):
        flow = {"nodes": [{"name": "Msg", "type": "n8n-nodes-base.slack",
                           "parameters": {"text": "use sk-abcdefghijklmnopqrstuvwxyz0123456789ABCD"}}],
                "connections": {}}
        self.assertNotIn("sk-abcdefghijklmnop", explicar.explain_flow(flow))

    def test_dangling_connection_does_not_crash(self):
        flow = {"nodes": [{"name": "A", "type": "x.noOp"}], "connections": {"A": {"main": [[{"node": "Fantasma"}]]}}}
        self.assertIn("fim do caminho", explicar.explain_flow(flow))

    def test_url_credentials_and_query_never_printed(self):
        flow = {"nodes": [{"name": "H", "type": "n8n-nodes-base.httpRequest",
                           "parameters": {"url": "https://user:senha@api.exemplo.com/x?token=1"}}], "connections": {}}
        text = explicar.explain_flow(flow)
        self.assertNotIn("senha", text)
        self.assertIn("api.exemplo.com", text)

    def test_webhook_path_is_omitted(self):
        flow = {"nodes": [{"name": "W", "type": "n8n-nodes-base.webhook", "parameters": {"path": "uuid-secreto-123"}}],
                "connections": {}}
        self.assertNotIn("uuid-secreto-123", explicar.explain_flow(flow))

    def test_node_name_cannot_break_out_of_markdown_or_mermaid(self):
        evil = "a\n```\n# injetado"
        flow = {"name": evil, "nodes": [{"name": evil, "type": "x.noOp"}], "connections": {}}
        text = explicar.explain_flow(flow)
        self.assertNotIn("\n# injetado", text)
        self.assertEqual(text.count("```"), 2)

    def test_malformed_json_shapes_do_not_crash(self):
        flow = {"nodes": [{"name": "A", "type": "x.set", "parameters": []}, "lixo"],
                "connections": {"A": {"main": "nao-e-lista"}, "B": "x"}}
        self.assertIn("### 1.", explicar.explain_flow(flow))

    def test_huge_flow_is_truncated(self):
        flow = {"nodes": [{"name": f"n{i}", "type": "x.noOp"} for i in range(explicar.MAX_NODES + 20)], "connections": {}}
        self.assertIn("truncado", explicar.explain_flow(flow))

    def test_cycle_does_not_hang(self):
        flow = {"nodes": [{"name": "A", "type": "x.noOp"}, {"name": "B", "type": "x.noOp"}],
                "connections": {"A": {"main": [[{"node": "B"}]]}, "B": {"main": [[{"node": "A"}]]}}}
        self.assertIn("### 2.", explicar.explain_flow(flow))


if __name__ == "__main__":
    unittest.main()
