"""Perfil de cada fluxo do catalogo: o que tem, por que usar e o que falta criar para entregar a um cliente.

Tudo e calculado dos proprios dados do JSON (nos, credenciais, gatilhos, notas do autor), sem IA e sem
inventar: cada item aponta para algo que existe, ou que NAO existe, no fluxo. O esforco e uma heuristica.
"""
from __future__ import annotations

import re

MAX_CREDENTIALS_SHOWN = 6
MAX_KEY_INTEGRATIONS = 5
MAX_PURPOSE_CHARS = 220
BIG_FLOW_NODES = 40
HEAVY_GAPS = 5

TRIGGER_PT = {
    "formTrigger": "envio de formulário",
    "webhook": "chamada de webhook (outro sistema chama o fluxo)",
    "scheduleTrigger": "horário agendado",
    "cron": "horário agendado",
    "manualTrigger": "clique manual (só serve para teste)",
    "executeWorkflowTrigger": "chamada de outro fluxo (é um sub-fluxo)",
    "chatTrigger": "mensagem no chat",
    "manualChatTrigger": "chat de teste",
    "telegramTrigger": "mensagem no Telegram",
    "whatsAppTrigger": "mensagem no WhatsApp",
    "gmailTrigger": "novo e-mail no Gmail",
    "googleDriveTrigger": "arquivo novo ou alterado no Google Drive",
    "googleSheetsTrigger": "mudança na planilha",
    "slackTrigger": "evento no Slack",
    "mcpTrigger": "chamada de um cliente MCP",
    "localFileTrigger": "arquivo local alterado",
    "emailReadImap": "novo e-mail (IMAP)",
}
NOT_A_TRIGGER = {"respondToWebhook"}
REAL_TRIGGERS_EXCLUDED = {"manualTrigger", "manualChatTrigger"}

INTEGRATION_PT = {
    "googleSheets": "Google Sheets", "googleDrive": "Google Drive", "googleDocs": "Google Docs",
    "googleCalendar": "Google Agenda", "gmail": "Gmail", "slack": "Slack", "telegram": "Telegram",
    "whatsApp": "WhatsApp", "openAi": "OpenAI", "supabase": "Supabase", "postgres": "PostgreSQL",
    "redis": "Redis", "notion": "Notion", "airtable": "Airtable", "hubspot": "HubSpot", "pipedrive": "Pipedrive",
    "discord": "Discord", "wordpress": "WordPress", "jira": "Jira", "clickUp": "ClickUp",
    "microsoftOutlook": "Outlook", "emailSend": "envio de e-mail", "emailReadImap": "leitura de e-mail (IMAP)",
    "httpRequest": "chamadas HTTP", "html": "leitura de páginas web", "markdown": "Markdown",
    "textClassifier": "classificação de texto (IA)", "sentimentAnalysis": "análise de sentimento (IA)",
    "informationExtractor": "extração de dados (IA)",
}
# Nos que so organizam dados ou apoiam a IA: nao ajudam a decidir se o fluxo serve ao cliente.
SUPPORT_NODES = {
    "limit", "sort", "set", "if", "switch", "merge", "code", "function", "functionItem", "noOp", "wait", "filter",
    "splitInBatches", "aggregate", "convertToFile", "extractFromFile", "executeWorkflow", "respondToWebhook",
    "dateTime", "stickyNote", "summarize", "removeDuplicates", "splitOut", "agent", "chainLlm", "toolWorkflow",
    "memoryBufferWindow", "outputParserStructured", "documentDefaultDataLoader",
}
SUPPORT_PREFIXES = ("lmChat", "embeddings", "textSplitter", "vectorStore", "toolVectorStore", "retriever", "outputParser", "memory")

CREDENTIAL_PT = {
    "openAiApi": "OpenAI (chave de API)", "googleSheetsOAuth2Api": "Google Sheets (OAuth)",
    "googleDriveOAuth2Api": "Google Drive (OAuth)", "gmailOAuth2": "Gmail (OAuth)",
    "googleCalendarOAuth2Api": "Google Agenda (OAuth)", "httpHeaderAuth": "cabeçalho de autenticação HTTP",
    "slackApi": "Slack", "supabaseApi": "Supabase", "openRouterApi": "OpenRouter", "anthropicApi": "Anthropic",
    "pineconeApi": "Pinecone", "cohereApi": "Cohere", "googlePalmApi": "Google Gemini", "telegramApi": "Telegram (token do bot)",
    "postgres": "PostgreSQL", "redis": "Redis", "huggingFaceApi": "Hugging Face", "weaviateApi": "Weaviate",
}

EN_WORDS = {"the", "and", "to", "of", "for", "with", "is", "this", "your", "you", "in", "it"}
PT_WORDS = {"de", "para", "que", "com", "uma", "não", "do", "da", "em", "os", "um", "se"}
WHAT_RE = re.compile(
    r"O que faz:?\s*(.+?)(?=\s+(?:Dispara|Como funciona|Entradas?|Sa[ií]das?|Pr[eé]-?requisitos?|Requisitos|Passos)\b|$)",
    re.IGNORECASE | re.DOTALL,
)


def humanize(name: str) -> str:
    """'googleSheetsOAuth2Api' -> 'Google sheets'; usado quando nao ha traducao pronta."""
    base = re.sub(r"(OAuth2Api|OAuth2|Api|Trigger)$", "", name)
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", base).split()
    return " ".join(word.capitalize() for word in words)


def node_types(data: dict) -> list[str]:
    nodes = [n for n in data.get("nodes", []) or [] if isinstance(n, dict)]
    return [str(n.get("type", "")).split(".")[-1] for n in nodes]


def trigger_names(types: list[str]) -> list[str]:
    seen = []
    for node_type in types:
        if node_type in NOT_A_TRIGGER or not (node_type.endswith("Trigger") or node_type in TRIGGER_PT):
            continue
        label = TRIGGER_PT.get(node_type, f"evento em {humanize(node_type)}")
        if label not in seen:
            seen.append(label)
    return seen


def key_integrations(info: dict) -> list[str]:
    names = []
    for raw in info.get("integrations", []):
        if raw in SUPPORT_NODES or raw.startswith(SUPPORT_PREFIXES):
            continue
        base = raw[:-4] if raw.endswith("Tool") and len(raw) > 4 else raw  # "googleCalendarTool": a IA usa o Google Agenda
        label = INTEGRATION_PT.get(base) or INTEGRATION_PT.get(raw) or humanize(base)
        if label not in names:
            names.append(label)
    return names[:MAX_KEY_INTEGRATIONS]


def ai_features(types: list[str]) -> list[str]:
    found = []
    if "agent" in types:
        found.append("agente de IA")
    if "memoryBufferWindow" in types:
        found.append("com memória de conversa")
    if any(t.startswith(("vectorStore", "toolVectorStore", "embeddings")) for t in types):
        found.append("busca em base de documentos (RAG)")
    providers = {"lmChatOpenAi": "OpenAI", "lmChatAnthropic": "Anthropic", "lmChatGoogleGemini": "Gemini", "lmChatOpenRouter": "OpenRouter"}
    models = [name for node, name in providers.items() if node in types]
    return found + ([f"modelo {', '.join(models)}"] if models else [])


def purpose(notes: str) -> str:
    """O que o autor diz que o fluxo faz: o trecho 'O que faz:' ou, na falta, a primeira frase das notas."""
    found = WHAT_RE.search(notes)
    text = (found.group(1) if found else notes).strip()
    if not text:
        return ""
    first = text if found else re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    first = re.sub(r"\s+", " ", first)
    return first if len(first) <= MAX_PURPOSE_CHARS else first[:MAX_PURPOSE_CHARS - 1].rstrip() + "…"


def is_english(notes: str) -> bool:
    words = re.findall(r"[a-zà-ú]+", notes.lower())
    en = sum(1 for w in words if w in EN_WORDS)
    pt = sum(1 for w in words if w in PT_WORDS)
    return en >= 4 and en > pt * 1.5


def clean_category(category: str) -> str:
    parts = [re.sub(r"[^\w &/+().,-]|_", " ", part).strip() for part in category.split(" / ")]
    return " › ".join(re.sub(r"\s+", " ", part) for part in parts[-2:] if part)


def has_error_flow(data: dict, types: list[str]) -> bool:
    return "errorTrigger" in types or bool((data.get("settings") or {}).get("errorWorkflow"))


def credentials_gap(info: dict) -> list[dict]:
    names = [CREDENTIAL_PT.get(c, humanize(c)) for c in info.get("credentials", [])]
    if not names:
        return []
    shown = ", ".join(names[:MAX_CREDENTIALS_SHOWN]) + (f" (+{len(names) - MAX_CREDENTIALS_SHOWN})" if len(names) > MAX_CREDENTIALS_SHOWN else "")
    return [{"tipo": "cliente", "texto": f"Credenciais do cliente para conectar: {shown}"}]


def security_gap(severities: list[str]) -> list[dict]:
    high, medium = severities.count("alto"), severities.count("médio")
    gaps = []
    if high:
        gaps.append({"tipo": "limpar", "texto": f"Remover {high} segredo(s) de terceiro que vieram no arquivo (chave ou token) antes de usar"})
    if medium:
        gaps.append({"tipo": "limpar", "texto": f"Trocar {medium} identificador(es) do autor (IDs de credencial, webhooks, e-mails, planilhas)"})
    return gaps


def build_gaps(data: dict, info: dict, severities: list[str]) -> list[dict]:
    types = node_types(data)
    triggers = {t for t in types if t.endswith("Trigger")}
    gaps = credentials_gap(info) + security_gap(severities)
    if not has_error_flow(data, types):
        gaps.append({"tipo": "criar", "texto": "Alerta de falha por e-mail: o fluxo não tem fluxo de erro"})
    if not (triggers - REAL_TRIGGERS_EXCLUDED - {"executeWorkflowTrigger"}) and "webhook" not in types:
        gaps.append({"tipo": "criar", "texto": "Gatilho real: hoje só dispara por clique manual ou por outro fluxo"})
    if "webhook" in types:
        gaps.append({"tipo": "criar", "texto": "Nova URL de webhook, registrada no sistema de origem do cliente"})
    if "executeWorkflowTrigger" in types:
        gaps.append({"tipo": "adaptar", "texto": "É um sub-fluxo: precisa do fluxo principal que o chama"})
    return gaps


def build_gaps_adapt(data: dict, info: dict) -> list[dict]:
    types = node_types(data)
    gaps = []
    if info.get("uses_ai"):
        gaps.append({"tipo": "adaptar", "texto": "Prompts e regras do negócio do cliente; testar respostas e definir limite de custo mensal de IA"})
    if any(t.startswith(("vectorStore", "toolVectorStore")) for t in types):
        gaps.append({"tipo": "criar", "texto": "Carregar e manter a base de documentos do cliente (e contratar o banco vetorial)"})
    http = types.count("httpRequest")
    if http:
        gaps.append({"tipo": "adaptar", "texto": f"Conferir {http} chamada(s) HTTP: endereços e autenticação do cliente"})
    if not info.get("notes"):
        gaps.append({"tipo": "adaptar", "texto": "Sem notas do autor: leia os nós antes de orçar"})
    elif is_english(info["notes"]):
        gaps.append({"tipo": "adaptar", "texto": "Notas e textos em inglês: traduzir e adaptar para o cliente"})
    if info.get("node_count", 0) >= BIG_FLOW_NODES:
        gaps.append({"tipo": "adaptar", "texto": f"Fluxo grande ({info['node_count']} nós): dividir em fases e testar por etapa"})
    return gaps


def effort(complexity: str, gaps: list[dict]) -> str:
    work = sum(1 for gap in gaps if gap["tipo"] in ("criar", "adaptar"))
    if complexity == "complexo" or work >= HEAVY_GAPS:
        return "alto"
    return "baixo" if complexity == "simples" and work <= 2 else "medio"


def what_it_has(data: dict, info: dict) -> list[str]:
    types = node_types(data)
    items = []
    triggers = trigger_names(types)
    if triggers:
        items.append("Dispara por: " + "; ".join(triggers))
    items.append(f"{info.get('node_count', 0)} etapas (nós), complexidade {info.get('complexity', '?').replace('medio', 'média')}")
    integrations = key_integrations(info)
    if integrations:
        items.append("Conversa com: " + ", ".join(integrations))
    ai = ai_features(types)
    items.append("Usa IA: " + ", ".join(ai) if ai else ("Usa IA" if info.get("uses_ai") else "Sem IA (custo de operação baixo e previsível)"))
    if has_error_flow(data, types):  # a ausencia aparece em "o que falta", nao aqui
        items.append("Tem fluxo de erro (avisa quando algo falha)")
    return items


def why_use(info: dict, category: str) -> list[str]:
    reasons = []
    said = purpose(info.get("notes", ""))
    if said:
        reasons.append(f"Segundo o autor: {said}")
    where = clean_category(category)
    if where:
        reasons.append(f"Serve para: {where}")
    reasons.append("Reaproveitar economiza as horas de montar do zero; o preço desconta só a parte reaproveitada.")
    return reasons


def build_profile(data: dict, info: dict, severities: list[str], category: str = "") -> dict:
    """Perfil completo do fluxo. `severities` sao as gravidades dos achados do scanner ('alto' ou 'médio')."""
    gaps = build_gaps(data, info, severities) + build_gaps_adapt(data, info)
    return {
        "tem": what_it_has(data, info),
        "por_que": why_use(info, category),
        "falta": gaps,
        "esforco": effort(info.get("complexity", ""), gaps),
    }
