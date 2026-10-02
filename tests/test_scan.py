"""Testes do scanner de segredos (CAT-03). Os segredos de teste sao montados em tempo de execucao
para que este arquivo nao contenha nenhum valor que parece real."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "flowhub"))

import scan  # noqa: E402

SCAN_CLI = str(ROOT / "flowhub" / "scan.py")
FILLER = "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2Yz3"

# 10 segredos plantados: (nome, valor). O valor so existe em memoria durante o teste.
SECRETS = {
    "google_api_key": "AIza" + FILLER[:35],
    "sk_key": "sk-" + FILLER[:30],
    "github_token": "ghp_" + FILLER[:36],
    "aws_key": "AKIA" + "ABCDEFGH12345678",
    "email": "pessoa.real" + "@" + "empresa-cliente.com.br",
    "slack_webhook": "https://hooks.slack.com/services/" + "T0000000/B0000000/" + FILLER[:24],
    "n8n_webhook": "https://n8n.cliente.com.br/webhook/" + "1a2b3c4d-1111-2222-3333-444455556666",
    "sheet_url": "https://docs.google.com/spreadsheets/d/" + FILLER[:30] + "/edit",
    "credential_id": "Zk9" + FILLER[:13],
    "sensitive_field": "valor-secreto-" + FILLER[:10],
}


def workflow_with_secrets() -> dict:
    s = SECRETS
    return {
        "name": "Fluxo de teste",
        "nodes": [
            {"name": "Http", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": s["n8n_webhook"], "headers": {"x": s["google_api_key"]}}},
            {"name": "IA", "type": "n8n-nodes-base.openAi", "parameters": {"apiKeyText": s["sk_key"]}},
            {"name": "Git", "type": "n8n-nodes-base.github", "parameters": {"note": "token " + s["github_token"]}},
            {"name": "Nuvem", "type": "n8n-nodes-base.aws", "parameters": {"accessKey": s["aws_key"]}},
            {"name": "Mail", "type": "n8n-nodes-base.gmail", "parameters": {"sendTo": s["email"]}, "credentials": {"gmailOAuth2": {"id": s["credential_id"], "name": "Gmail"}}},
            {"name": "Chat", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": s["slack_webhook"]}},
            {"name": "Planilha", "type": "n8n-nodes-base.googleSheets", "parameters": {"documentUrl": s["sheet_url"]}},
            {"name": "Config", "type": "n8n-nodes-base.set", "parameters": {"password": s["sensitive_field"]}},
        ],
    }


def all_output(findings: list) -> str:
    return scan.render(findings, [], 1) + json.dumps([f.__dict__ for f in findings], ensure_ascii=False)


class ScanTests(unittest.TestCase):
    def test_finds_all_ten_planted_secrets_and_never_prints_one_whole(self):
        findings = scan.scan_document(workflow_with_secrets(), "t.json")
        kinds = {finding.kind for finding in findings}
        expected = {
            "chave de API do Google", "chave de API (sk-)", "token do GitHub", "chave da AWS", "e-mail",
            "webhook de chat (Slack/Discord)", "URL de webhook do n8n", "ID de arquivo ou pasta do Google",
            "ID de credencial do n8n", 'valor sensível no campo "password"',
        }
        self.assertTrue(expected <= kinds, f"faltou: {expected - kinds}")
        output = all_output(findings)
        for name, secret in SECRETS.items():
            self.assertNotIn(secret, output, f"{name} apareceu inteiro na saida")

    def test_each_finding_names_node_and_field(self):
        findings = scan.scan_document(workflow_with_secrets(), "t.json")
        mail = [f for f in findings if f.kind == "e-mail"][0]
        self.assertEqual(mail.node, "Mail")
        self.assertEqual(mail.field, "parameters.sendTo")

    def test_clean_flow_with_placeholders_has_no_findings(self):
        clean = {"name": "Limpo", "nodes": [
            {"name": "Mail", "type": "x", "parameters": {
                "sendTo": "{{ $json.email }}", "token": "SEU_TOKEN_AQUI", "apiKey": "={{ $env.API_KEY }}",
                "cc": "contato@example.com", "documentId": "<ID_DA_PLANILHA>"}},
        ]}
        self.assertEqual(scan.scan_document(clean, "c.json"), [])

    def test_values_under_24_characters_are_fully_masked_and_long_ones_show_at_most_a_fifth(self):
        self.assertEqual(scan.mask("abc12345"), "********")
        sixteen = "abcdefghijklmnop"  # 16 caracteres: 5 de 16 seria quase um terco do segredo
        self.assertEqual(scan.mask(sixteen), "*" * 16)
        long_value = "abcdefghijklmnopqrstuvwxyz0123"
        masked = scan.mask(long_value)
        self.assertNotIn(long_value, masked)
        self.assertTrue(masked.startswith("abc"))
        self.assertLessEqual((scan.MASK_START + scan.MASK_END) / len(long_value), 0.2)

    def test_a_json_that_is_a_list_of_flows_is_scanned_not_reported_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lista.json"
            path.write_text(json.dumps([workflow_with_secrets(), {"nodes": []}]), encoding="utf-8")
            findings, invalid, total = scan.scan_paths([str(path)])
        self.assertGreaterEqual(len(findings), 10)
        self.assertEqual(invalid, [])
        self.assertEqual(total, 1)

    def test_several_concatenated_flows_in_one_file_are_all_scanned(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dois.json"
            path.write_text(json.dumps({"nodes": []}) + "\n" + json.dumps(workflow_with_secrets()), encoding="utf-8")
            findings, invalid, _ = scan.scan_paths([str(path)])
        self.assertGreaterEqual(len(findings), 10)
        self.assertEqual(invalid, [])

    def test_a_json_with_no_flow_in_it_is_invalid_never_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, content in (("numeros.json", "[1, 2, 3]"), ("texto.json", '"so uma string"')):
                (Path(folder) / name).write_text(content, encoding="utf-8")
            findings, invalid, total = scan.scan_paths([folder])
        self.assertEqual(findings, [])
        self.assertEqual(len(invalid), 2)
        self.assertEqual(total, 2)

    def test_a_huge_text_without_an_at_sign_does_not_make_the_email_regex_explode(self):
        blob = "a" * 400_000  # antes: quadratico, minutos
        started = time.monotonic()
        findings = scan.scan_document({"nodes": [{"name": "Blob", "parameters": {"texto": blob}}]})
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(findings, [])

    def test_a_secret_beyond_the_scan_limit_is_not_read_but_one_inside_it_is(self):
        inside = "x" * 100 + SECRETS["google_api_key"]
        found = scan.scan_document({"nodes": [{"name": "A", "parameters": {"t": inside}}]})
        self.assertEqual([f.kind for f in found], ["chave de API do Google"])

    def test_webhook_id_is_reported(self):
        findings = scan.scan_document({"nodes": [{"name": "Gatilho", "parameters": {}, "webhookId": "9f8e7d6c-1111-2222-3333-444455556666"}]})
        self.assertEqual([f.kind for f in findings], ["ID de webhook do n8n"])

    def test_pin_data_and_flow_level_fields_are_scanned(self):
        data = {"nodes": [], "pinData": {"Gatilho": [{"json": {"contato": SECRETS["email"]}}]}}
        findings = scan.scan_document(data)
        self.assertEqual(findings[0].node, scan.FLOW_LEVEL)

    def test_batch_reports_invalid_json_and_keeps_going(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "bom.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
            (base / "quebrado.json").write_text("{ isto nao e json", encoding="utf-8")
            (base / "segredo.json").write_text(json.dumps(workflow_with_secrets()), encoding="utf-8")
            findings, invalid, total = scan.scan_paths([folder])
        self.assertEqual(total, 3)
        self.assertEqual(len(invalid), 1)
        self.assertGreaterEqual(len(findings), 10)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCAN_CLI, *args], capture_output=True, text=True, encoding="utf-8")

    def test_cli_exit_codes_and_clean_message(self):
        with tempfile.TemporaryDirectory() as folder:
            clean = Path(folder) / "ok.json"
            clean.write_text(json.dumps({"nodes": [{"name": "A", "parameters": {"x": "{{ $json.a }}"}}]}), encoding="utf-8")
            bad = Path(folder) / "ruim.json"
            bad.write_text(json.dumps(workflow_with_secrets()), encoding="utf-8")
            ok = self.run_cli(str(clean))
            dirty = self.run_cli(str(bad))
            broken = self.run_cli(str(Path(folder) / "nao-existe.json"))
        self.assertEqual(ok.returncode, 0)
        self.assertIn("LIMPO", ok.stdout)
        self.assertIn("Padrões verificados", ok.stdout)
        self.assertEqual(dirty.returncode, 1)
        for secret in SECRETS.values():
            self.assertNotIn(secret, dirty.stdout)
        self.assertEqual(broken.returncode, 1)

    def test_cli_json_output_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "ruim.json"
            bad.write_text(json.dumps(workflow_with_secrets()), encoding="utf-8")
            result = self.run_cli(str(bad), "--json")
        data = json.loads(result.stdout)
        self.assertEqual(data["files"], 1)
        self.assertGreaterEqual(len(data["findings"]), 10)


if __name__ == "__main__":
    unittest.main()
