"""Testes do perfil de fluxo (o que tem, por que usar, o que falta criar)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "flowhub"))

import perfil  # noqa: E402


def flow(*types, settings=None):
    return {"nodes": [{"name": f"n{i}", "type": f"n8n-nodes-base.{t}", "parameters": {}} for i, t in enumerate(types)],
            "settings": settings or {}}


def info(**overrides):
    base = {"triggers": [], "integrations": [], "credentials": [], "uses_ai": False, "node_count": 5,
            "complexity": "medio", "notes": ""}
    return {**base, **overrides}


def texts(gaps, kind=None):
    return [g["texto"] for g in gaps if kind is None or g["tipo"] == kind]


class PerfilTests(unittest.TestCase):
    def test_triggers_are_translated_and_respond_to_webhook_is_not_a_trigger(self):
        names = perfil.trigger_names(["formTrigger", "webhook", "respondToWebhook", "scheduleTrigger", "novoBichoTrigger"])
        self.assertIn("envio de formulário", names)
        self.assertIn("horário agendado", names)
        self.assertIn("evento em Novo Bicho", names)
        self.assertFalse(any("respond" in n.lower() for n in names))

    def test_credentials_become_friendly_names_and_are_listed_as_the_clients_job(self):
        gaps = perfil.credentials_gap(info(credentials=["gmailOAuth2", "openAiApi", "algumaCoisaNovaApi"]))
        self.assertEqual(gaps[0]["tipo"], "cliente")
        self.assertIn("Gmail (OAuth)", gaps[0]["texto"])
        self.assertIn("OpenAI (chave de API)", gaps[0]["texto"])
        self.assertIn("Alguma Coisa Nova", gaps[0]["texto"])
        self.assertEqual(perfil.credentials_gap(info()), [])

    def test_many_credentials_are_summarised(self):
        gap = perfil.credentials_gap(info(credentials=[f"c{i}Api" for i in range(10)]))[0]["texto"]
        self.assertIn("(+4)", gap)

    def test_missing_error_flow_is_a_gap_and_having_one_is_not(self):
        without = perfil.build_gaps(flow("webhook"), info(), [])
        self.assertTrue(any("fluxo de erro" in t for t in texts(without, "criar")))
        for data in (flow("webhook", "errorTrigger"), flow("webhook", settings={"errorWorkflow": "abc"})):
            self.assertFalse(any("fluxo de erro" in t for t in texts(perfil.build_gaps(data, info(), []))))

    def test_manual_only_flow_needs_a_real_trigger(self):
        gaps = perfil.build_gaps(flow("manualTrigger", "set"), info(), [])
        self.assertTrue(any("Gatilho real" in t for t in texts(gaps, "criar")))
        gaps = perfil.build_gaps(flow("formTrigger"), info(), [])
        self.assertFalse(any("Gatilho real" in t for t in texts(gaps)))

    def test_webhook_needs_a_new_url_and_a_sub_workflow_needs_its_caller(self):
        self.assertTrue(any("Nova URL de webhook" in t for t in texts(perfil.build_gaps(flow("webhook"), info(), []))))
        self.assertTrue(any("sub-fluxo" in t for t in texts(perfil.build_gaps(flow("executeWorkflowTrigger"), info(), []), "adaptar")))

    def test_secrets_become_cleanup_items_with_counts(self):
        gaps = perfil.security_gap(["alto", "alto", "médio"])
        self.assertEqual([g["tipo"] for g in gaps], ["limpar", "limpar"])
        self.assertIn("2 segredo(s)", gaps[0]["texto"])
        self.assertIn("1 identificador(es)", gaps[1]["texto"])
        self.assertEqual(perfil.security_gap([]), [])

    def test_ai_flows_need_prompts_and_a_cost_limit_and_rag_needs_the_clients_documents(self):
        gaps = perfil.build_gaps_adapt(flow("agent", "vectorStoreSupabase"), info(uses_ai=True))
        self.assertTrue(any("limite de custo" in t for t in texts(gaps, "adaptar")))
        self.assertTrue(any("base de documentos" in t for t in texts(gaps, "criar")))
        self.assertEqual(perfil.build_gaps_adapt(flow("set"), info(notes="Faz uma coisa simples em português para o cliente")), [])

    def test_http_calls_are_counted(self):
        gaps = perfil.build_gaps_adapt(flow("httpRequest", "httpRequest", "set"), info(notes="x"))
        self.assertTrue(any("2 chamada(s) HTTP" in t for t in texts(gaps)))

    def test_missing_notes_and_english_notes_are_flagged(self):
        no_notes = perfil.build_gaps_adapt(flow("set"), info(notes=""))
        self.assertTrue(any("Sem notas" in t for t in texts(no_notes)))
        english = perfil.build_gaps_adapt(flow("set"), info(notes="This flow reads the data and sends it to the CRM for you in the morning"))
        self.assertTrue(any("inglês" in t for t in texts(english)))
        portuguese = perfil.build_gaps_adapt(flow("set"), info(notes="Este fluxo lê os dados e envia para o CRM de manhã, com uma regra que não falha"))
        self.assertFalse(any("inglês" in t for t in texts(portuguese)))

    def test_big_flows_are_split_in_phases(self):
        gaps = perfil.build_gaps_adapt(flow("set"), info(node_count=83, notes="x"))
        self.assertTrue(any("83 nós" in t for t in texts(gaps)))

    def test_purpose_prefers_what_it_does_then_the_first_sentence_and_is_bounded(self):
        notes = "Bla bla O que faz: Recebe e-mails, resume e responde com IA. Dispara: Novo e-mail IMAP"
        self.assertEqual(perfil.purpose(notes), "Recebe e-mails, resume e responde com IA.")
        self.assertEqual(perfil.purpose("Primeira frase aqui. Segunda frase."), "Primeira frase aqui.")
        self.assertEqual(perfil.purpose(""), "")
        self.assertLessEqual(len(perfil.purpose("palavra " * 200)), perfil.MAX_PURPOSE_CHARS)

    def test_category_is_cleaned_of_emoji_and_keeps_the_last_two_levels(self):
        self.assertEqual(perfil.clean_category("Acervo / Fluxos Especiais / 💬 Chatbots & Atendimento"), "Fluxos Especiais › Chatbots & Atendimento")
        self.assertEqual(perfil.clean_category(""), "")

    def test_effort_is_a_heuristic_from_complexity_and_open_work(self):
        few = [{"tipo": "cliente", "texto": "x"}]
        many = [{"tipo": "criar", "texto": "x"}] * 5
        self.assertEqual(perfil.effort("simples", few), "baixo")
        self.assertEqual(perfil.effort("medio", few), "medio")
        self.assertEqual(perfil.effort("medio", many), "alto")
        self.assertEqual(perfil.effort("complexo", []), "alto")

    def test_support_nodes_do_not_appear_as_what_the_flow_talks_to(self):
        names = perfil.key_integrations(info(integrations=["agent", "set", "lmChatOpenAi", "googleSheets", "gmail", "memoryBufferWindow"]))
        self.assertEqual(names, ["Google Sheets", "Gmail"])

    def test_unknown_names_are_title_cased_and_ai_tools_show_the_service_they_use_without_duplicates(self):
        self.assertEqual(perfil.humanize("googleDocsOAuth2Api"), "Google Docs")
        names = perfil.key_integrations(info(integrations=["googleCalendarTool", "googleCalendar", "supabaseTool", "textClassifier"]))
        self.assertEqual(names, ["Google Agenda", "Supabase", "classificação de texto (IA)"])

    def test_the_full_profile_has_the_three_blocks_and_never_crashes_on_a_bare_flow(self):
        profile = perfil.build_profile(flow("formTrigger", "gmail"), info(integrations=["gmail"], credentials=["gmailOAuth2"],
                                       notes="O que faz: Envia a proposta por e-mail. Dispara: formulário"), ["médio"], "Acervo / Vendas & Propostas")
        self.assertTrue(profile["tem"] and profile["por_que"] and profile["falta"])
        self.assertIn(profile["esforco"], {"baixo", "medio", "alto"})
        self.assertTrue(any("Segundo o autor: Envia a proposta" in r for r in profile["por_que"]))
        bare = perfil.build_profile({}, {}, [])
        self.assertIn("tem", bare)


if __name__ == "__main__":
    unittest.main()
