"""Testes da proposta em PDF (ORC-02)."""
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "flowhub"))

import proposta  # noqa: E402
import quote  # noqa: E402

TODAY = date(2026, 10, 1)


def pedido_text(extra: str = "", setup: str = "3500", mensal: str = "497", cliente: str = "Acme Ltda",
                features: str = "", briefing_problem: str = "Leads copiados à mão") -> str:
    return f"""---
id: PED-007
cliente: {cliente}
status: Orçado
setup: {setup}
mensal: {mensal}
{extra}---

# PED-007 · {cliente}

## Briefing
- Problema hoje: {briefing_problem}
- Impacto (horas por semana, custo): 15 h por semana a R$ 50 por hora
- Ferramentas que usa: Sheets, WhatsApp
- Gatilho: Formulário

## Features
| # | Feature | Origem | Critério de aceite | Horas | Fase |
|---|---|---|---|---|---|
{features}
## Histórico
-
"""


def make_pdf(text: str, params=None):
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "PED-007-acme.md"
        source.write_text(text, encoding="utf-8")
        out = Path(folder) / "proposta.pdf"
        result = proposta.generate(source, out, TODAY, params)
        with fitz.open(out) as doc:  # fechar antes de apagar a pasta (o Windows trava arquivo aberto)
            return result, doc.page_count, normalize("".join(page.get_text() for page in doc))


def normalize(text: str) -> str:
    """Junta linhas quebradas pelo layout e desfaz as ligaduras (fi, fl) da extracao de texto do PDF."""
    return " ".join(text.replace("ﬁ", "fi").replace("ﬂ", "fl").split())


class PropostaTests(unittest.TestCase):
    def test_refuses_without_setup_or_monthly_and_names_the_fields(self):
        for text, expected in ((pedido_text(setup=""), "setup"), (pedido_text(mensal="abc"), "mensal")):
            with self.assertRaises(ValueError) as caught:
                make_pdf(text)
            self.assertIn(expected, str(caught.exception))

    def test_fits_one_page_and_carries_the_numbers_from_the_order(self):
        result, pages, text = make_pdf(pedido_text(extra="economia_mensal: 3000\n"))
        self.assertEqual(pages, 1)
        self.assertEqual(result["version"], "PED-007-v1")
        for expected in ("R$ 3.500", "R$ 1.750", "R$ 497", "Acme Ltda", "PED-007-v1", "16/10/2026"):
            self.assertIn(expected, text)

    def test_roi_section_uses_net_payback_and_never_appears_without_saving(self):
        _, _, with_roi = make_pdf(pedido_text(extra="economia_mensal: 3000\n"))
        self.assertIn("ROI estimado", with_roi)
        self.assertIn("cerca de 42 dias", with_roi)  # 3.500 / (3.000 - 497) x 30
        self.assertIn("R$ 26.536", with_roi)
        result, _, without = make_pdf(pedido_text())
        self.assertNotIn("ROI estimado", without)
        self.assertTrue(result["warnings"])

    def test_support_terms_third_party_and_ai_notice_are_always_included(self):
        _, _, text = make_pdf(pedido_text())
        self.assertIn("Licenças e APIs de terceiros por conta do cliente", text)
        self.assertIn("inteligência artificial de terceiro", text)
        self.assertIn("Suporte mensal", text)

    def test_text_from_the_order_is_escaped_not_interpreted(self):
        _, _, text = make_pdf(pedido_text(cliente="<b>Acme</b> & Cia", briefing_problem="<script>alert(1)</script>"))
        self.assertIn("<b>Acme</b> & Cia", text)
        self.assertIn("<script>alert(1)</script>", text)

    def test_custom_version_and_validity_are_respected(self):
        _, _, text = make_pdf(pedido_text(extra="versao_proposta: PED-007-v3\nvalidade_proposta: 2026-12-31\n"))
        self.assertIn("PED-007-v3", text)
        self.assertIn("31/12/2026", text)

    def test_scope_lists_features_up_to_the_limit(self):
        rows = "".join(f"| {n} | Feature numero {n} | construir | ok | 2 | PoC |\n" for n in range(1, 12))
        _, pages, text = make_pdf(pedido_text(features=rows))
        self.assertEqual(pages, 1)
        self.assertIn(f"Feature numero {proposta.MAX_SCOPE_ITEMS}", text)
        self.assertNotIn(f"Feature numero {proposta.MAX_SCOPE_ITEMS + 1}", text)

    def test_old_briefing_labels_are_still_understood(self):
        old = pedido_text().replace("Impacto (horas por semana, custo)", "Impacto").replace("Ferramentas que usa", "Ferramentas")
        _, _, text = make_pdf(old)
        self.assertIn("15 h por semana", text)
        self.assertIn("Sheets, WhatsApp", text)

    def test_very_long_text_is_clipped_and_still_fits_one_page(self):
        _, pages, text = make_pdf(pedido_text(briefing_problem="palavra " * 4000))
        self.assertEqual(pages, 1)
        self.assertIn("…", text)

    def test_rendering_gives_up_quickly_instead_of_looping_on_an_unbreakable_block(self):
        # uma linha de tabela maior que a pagina nao avanca: sem o teto de paginas isto nunca terminava
        markup = "<table><tr><td>" + "palavra " * 6000 + "</td></tr></table>"
        started = time.monotonic()
        _, pages = proposta.render_pdf(markup, 10)
        self.assertGreater(pages, 1)
        self.assertLess(time.monotonic() - started, 30)
        with self.assertRaises(ValueError) as caught:
            proposta.fit_one_page(markup)
        self.assertIn("não cabe em uma página", str(caught.exception))

    def test_the_terms_text_uses_the_down_payment_from_the_parameters(self):
        params = {**quote.load_params(), "entrada": 0.3}
        _, _, text = make_pdf(pedido_text(), params)
        self.assertIn("Entrada de 30% na aprovação", text)
        self.assertNotIn("Entrada de 50%", text)

    def test_an_impossible_validity_date_is_explained_in_portuguese(self):
        with self.assertRaises(ValueError) as caught:
            make_pdf(pedido_text(extra="validade_proposta: 2026-02-31\n"))
        self.assertIn("não é uma data válida", str(caught.exception))
        self.assertNotIn("day is out of range", str(caught.exception))

    def test_a_unicode_line_separator_in_the_client_name_does_not_inject_a_header_field(self):
        text = pedido_text(cliente="Acme setup: 1")
        parsed = proposta.parse_pedido(text)
        self.assertEqual(parsed.campos["setup"], "3500")  # a linha real continua valendo

    def test_a_file_with_bom_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "PED-007-acme.md"
            source.write_bytes(b"\xef\xbb\xbf" + pedido_text().encode("utf-8"))
            out = Path(folder) / "p.pdf"
            result = proposta.generate(source, out, TODAY)
        self.assertEqual(result["pages"], 1)

    def test_parameters_drive_the_down_payment_and_validity(self):
        params = {**quote.load_params(), "entrada": 0.3, "validade_dias": 30}
        _, _, text = make_pdf(pedido_text(), params)
        self.assertIn("Entrada (30%", text)
        self.assertIn("R$ 1.050", text)
        self.assertIn("31/10/2026", text)


if __name__ == "__main__":
    unittest.main()
