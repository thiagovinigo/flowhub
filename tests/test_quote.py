"""Testes da calculadora (ORC-12). Rode: python -m unittest discover -s tests -p "test_*.py" """
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "flowhub"))

import quote  # noqa: E402


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.params = quote.load_params()

    def test_floor_wins_over_roi_ceiling_and_warns(self):
        # medio, 10 h, economia de R$ 300/mes: teto R$ 1.800 < piso R$ 2.200
        result = quote.build_quote("medio", 10, 0, 300, self.params)
        self.assertEqual(result["setup"], 2200)
        self.assertTrue(result["unviable_by_roi"])
        self.assertTrue(any("Inviável" in w for w in result["warnings"]))

    def test_ceiling_limits_price_when_above_floor(self):
        result = quote.build_quote("complexo", 60, 0, 1000, self.params)  # teto R$ 6.000 > piso R$ 5.000
        self.assertEqual(result["setup"], 6000)
        self.assertTrue(result["capped_by_roi"])
        self.assertFalse(result["unviable_by_roi"])

    def test_net_payback_and_annual_saving_match_the_reference_case(self):
        self.assertEqual(quote.payback_days(3500, 497, 3000), 42)  # 3.500 / 2.503 x 30
        self.assertEqual(quote.annual_net_saving(3500, 497, 3000), 26536)  # 36.000 - 3.500 - 12 x 497

    def test_payback_is_none_when_monthly_eats_the_saving(self):
        self.assertIsNone(quote.payback_days(3000, 500, 400))

    def test_monthly_saving_comes_from_the_script(self):
        self.assertEqual(quote.monthly_saving(15, 50), 3000)

    def test_discount_applies_only_to_adaptation_hours(self):
        build_only = quote.labor_cost(40, 0, self.params)
        adapt_only = quote.labor_cost(0, 40, self.params)
        mixed = quote.labor_cost(20, 20, self.params)
        self.assertAlmostEqual(adapt_only, build_only * (1 - self.params["desconto_adaptacao"]))
        self.assertAlmostEqual(mixed, (build_only + adapt_only) / 2)

    def test_floor_applies_to_tiny_jobs_and_monthly_has_a_minimum(self):
        result = quote.build_quote("simples", 1, 0, None, self.params)
        self.assertEqual(result["setup"], self.params["pisos"]["simples"])
        self.assertGreaterEqual(result["monthly"], self.params["mensalidade_minima"])

    def test_changing_the_params_file_changes_the_next_quote_and_records_the_version(self):
        changed = {**self.params, "valor_hora": 180, "versao": "teste.1"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "parametros.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            loaded = quote.load_params(path)
        base = quote.build_quote("complexo", 40, 0, None, self.params)
        raised = quote.build_quote("complexo", 40, 0, None, loaded)
        self.assertGreater(raised["setup"], base["setup"])
        self.assertEqual(raised["params_version"], "teste.1")

    def test_load_params_rejects_missing_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "parametros.json"
            path.write_text(json.dumps({"versao": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                quote.load_params(path)

    def test_rejects_invalid_complexity_and_hours(self):
        with self.assertRaises(ValueError):
            quote.build_quote("gigante", 5, 0, None, self.params)
        with self.assertRaises(ValueError):
            quote.build_quote("medio", 0, 0, None, self.params)

    def test_cli_json_output(self):
        out = subprocess.run(
            [sys.executable, str(ROOT / "flowhub" / "quote.py"), "--json", "--complexity", "medio", "--hours", "20",
             "--adapt-hours", "10", "--client-hours-week", "15", "--client-hourly-cost", "50"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
        data = json.loads(out)
        self.assertEqual(data["client_saving"], 3000)
        self.assertIn("params_version", data)

    def test_cli_rejects_adapt_hours_above_total(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "flowhub" / "quote.py"), "--complexity", "medio", "--hours", "5", "--adapt-hours", "9"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
