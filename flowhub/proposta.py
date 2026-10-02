"""Gera a proposta comercial em PDF (1 pagina) a partir de um pedido do vault (ORC-02).

Os numeros vem do pedido (setup, mensal, economia) e dos parametros de flowhub/parametros.json;
nada e digitado de novo. Se faltar setup ou mensalidade, recusa e diz quais campos faltam.
Sem economia mensal no pedido, o PDF sai sem a secao de ROI (nunca com ROI inventado).

Exemplo:
  python flowhub/proposta.py vault/Pedidos/PED-001-acme.md --out proposta.pdf --json
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import fitz  # PyMuPDF

from quote import annual_net_saving, brl, load_params, payback_days

FRONT_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
BRIEFING_RE = re.compile(r"^- ([^:\n]+):[ \t]*(.*)$", re.MULTILINE)
SECTION_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
DEFAULT_PROPONENT = "Thiago Vinigo"
DEFAULT_PHASES = "Diagnóstico: 3 dias · Prova de conceito: 7 dias · Entrega completa: 21 dias"
FONT_SIZES = (11.0, 10.5, 10.0, 9.5, 9.0, 8.5, 8.0, 7.5)
PAGE_MARGIN = 38
MAX_SCOPE_ITEMS = 7
MAX_RENDER_PAGES = 3   # teto de seguranca: uma linha de tabela maior que a pagina nao avanca nunca
MAX_FIELD_CHARS = 500
MAX_SCOPE_CHARS = 120
STANDARD_DELIVERABLES = (
    "Documentação (LEIA-ME com credenciais e variáveis)",
    "Vídeo de entrega de 5 minutos e treinamento de 30 minutos",
    "Alerta de falha por e-mail ativo e testado",
)
def terms_text(params: dict) -> str:
    """Condicoes comerciais; o percentual da entrada vem dos parametros, nunca fixo no texto."""
    down = round(params["entrada"] * 100)
    return (
        "Escopo fechado: o que não está listado não está incluso; mudanças viram pedido de alteração, cobrado por hora. "
        f"Inclui 2 rodadas de ajuste. Entrada de {down}% na aprovação e saldo na entrega validada. "
        "Licenças e APIs de terceiros por conta do cliente."
    )
SUPPORT_TERMS = (
    "Suporte mensal: monitoramento, correções de falhas do fluxo e relatório mensal; resposta em horário comercial. "
    "O fluxo entregue pertence ao contratante; se a mensalidade for cancelada, o fluxo continua funcionando sem suporte. "
    "Mudanças em APIs de terceiros ou na instância do cliente que quebrem o fluxo são tratadas como pedido de alteração."
)
AI_NOTICE = "Os dados deste pedido são processados com apoio de inteligência artificial de terceiro para preparar esta proposta."


@dataclass(frozen=True)
class Pedido:
    id: str
    campos: dict
    briefing: dict
    features: tuple


def parse_pedido(text: str) -> Pedido:
    """Le cabecalho, linhas do Briefing e tabela de Features de um pedido em Markdown."""
    match = FRONT_RE.match(text)
    campos: dict = {}
    for line in (re.split(r"\r?\n", match.group(1)) if match else []):  # splitlines() quebraria tambem em U+2028
        pair = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if pair:
            campos[pair.group(1)] = re.sub(r"(^|\s)#.*$", "", pair.group(2)).strip()
    return Pedido(campos.get("id", ""), campos, section_pairs(text, "Briefing"), section_table(text, "Features"))


def section_body(text: str, heading: str) -> str:
    matches = list(SECTION_RE.finditer(text))
    for index, found in enumerate(matches):
        if found.group(1).strip() == heading:
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            return text[found.end():end]
    return ""


def section_pairs(text: str, heading: str) -> dict:
    return {key.strip(): value.strip() for key, value in BRIEFING_RE.findall(section_body(text, heading))}


def section_table(text: str, heading: str) -> tuple:
    rows = [line for line in re.split(r"\r?\n", section_body(text, heading)) if line.startswith("|")][2:]
    parsed = [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
    return tuple(tuple(cells) for cells in parsed if any(cells))


def to_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def missing_fields(pedido: Pedido) -> list[str]:
    """Campos sem os quais nao ha proposta; vazio quando da para gerar."""
    return [name for name in ("setup", "mensal") if to_float(pedido.campos.get(name, "")) is None]


def clip(text: str, limit: int) -> str:
    """Corta textos longos com reticencias para a proposta continuar cabendo em uma pagina."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def briefing_value(briefing: dict, prefix: str) -> str:
    """Valor do primeiro rotulo do Briefing que comeca com `prefix` (aceita variacoes do modelo antigo)."""
    found = next((value for key, value in briefing.items() if key.lower().startswith(prefix.lower()) and value), "")
    return clip(found, MAX_FIELD_CHARS)


def pt_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def phases_text(prazo_dias: str) -> str:
    days = to_float(prazo_dias)
    return f"Entrega completa em até {int(days)} dias, com prova de conceito funcionando antes." if days else DEFAULT_PHASES


def build_context(pedido: Pedido, params: dict, today: date) -> dict:
    """Todos os numeros e textos da proposta, ja calculados (testavel sem gerar PDF)."""
    setup = to_float(pedido.campos["setup"])
    monthly = to_float(pedido.campos["mensal"])
    saving = to_float(pedido.campos.get("economia_mensal", ""))
    valid_until = pedido.campos.get("validade_proposta")
    try:
        until = datetime.strptime(valid_until, "%Y-%m-%d").date() if valid_until else today + timedelta(days=params["validade_dias"])
    except ValueError:
        raise ValueError(f"A validade da proposta no pedido não é uma data válida ({valid_until}). Use AAAA-MM-DD.") from None
    down = setup * params["entrada"]
    return {
        "cliente": pedido.campos.get("cliente", ""),
        "versao": pedido.campos.get("versao_proposta") or f"{pedido.id}-v1",
        "data": pt_date(today), "validade": pt_date(until),
        "proponente": params.get("proponente", DEFAULT_PROPONENT),
        "setup": setup, "mensal": monthly, "entrada": down, "saldo": setup - down,
        "percentual_entrada": round(params["entrada"] * 100),
        "economia": saving,
        "payback": payback_days(setup, monthly, saving) if saving else None,
        "ano_liquido": round(annual_net_saving(setup, monthly, saving)) if saving else None,
        "fases": phases_text(pedido.campos.get("prazo_dias", "")),
        "problema": briefing_value(pedido.briefing, "Problema"),
        "impacto": briefing_value(pedido.briefing, "Impacto"),
        "gatilho": briefing_value(pedido.briefing, "Gatilho"),
        "ferramentas": briefing_value(pedido.briefing, "Ferramentas"),
        "escopo": [clip(row[1], MAX_SCOPE_CHARS) for row in pedido.features if len(row) > 1 and row[1]][:MAX_SCOPE_ITEMS],
        "termos": terms_text(params),
        "avisos": [] if saving else ["Sem economia mensal no pedido: a proposta saiu sem a seção de ROI."],
    }


def esc(value) -> str:
    return html.escape(str(value or ""))


def block(title: str, body: str) -> str:
    return f"<h2>{esc(title)}</h2>{body}"


def list_html(items) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def problem_html(ctx: dict) -> str:
    parts = [f"<p><b>Hoje.</b> {esc(ctx['problema']) or 'A detalhar no diagnóstico.'}</p>"]
    if ctx["impacto"]:
        parts.append(f"<p><b>Impacto.</b> {esc(ctx['impacto'])}</p>")
    return block("Problema", "".join(parts))


def solution_html(ctx: dict) -> str:
    parts = [f"<p><b>Gatilho.</b> {esc(ctx['gatilho']) or 'A definir no diagnóstico.'}</p>"]
    if ctx["ferramentas"]:
        parts.append(f"<p><b>Sistemas.</b> {esc(ctx['ferramentas'])}</p>")
    parts.append("<p>Os dados passam a fluir sozinhos, com registro, alerta de falha e monitoramento.</p>")
    return block("Solução", "".join(parts))


def money_row(label: str, value: str, strong: bool = False) -> str:
    cls = ' class="strong"' if strong else ""
    return f'<tr><td class="lbl">{esc(label)}</td><td class="val"{cls}>{esc(value)}</td></tr>'


def investment_html(ctx: dict) -> str:
    rows = [
        money_row("Setup (único)", brl(ctx["setup"]), True),
        money_row(f"Entrada ({ctx['percentual_entrada']}%, na aprovação)", brl(ctx["entrada"])),
        money_row("Saldo na entrega validada", brl(ctx["saldo"])),
        money_row("Suporte mensal (após a entrega)", brl(ctx["mensal"]), True),
    ]
    return block("Investimento", f'<table class="money">{"".join(rows)}</table>')


def roi_html(ctx: dict) -> str:
    if not ctx["economia"]:
        return ""
    rows = [money_row("Economia mensal do cliente", brl(ctx["economia"]))]
    if ctx["payback"] is not None:
        rows.append(money_row("Payback (já descontada a mensalidade)", f"cerca de {ctx['payback']} dias"))
        rows.append(money_row("Economia líquida no 1º ano", brl(ctx["ano_liquido"])))
    return block("ROI estimado", f'<table class="money">{"".join(rows)}</table>')


def build_html(ctx: dict) -> str:
    scope = ctx["escopo"] + list(STANDARD_DELIVERABLES)
    return (
        '<div class="head"><p class="eyebrow">PROPOSTA COMERCIAL</p>'
        f'<h1>{esc(ctx["cliente"])}</h1>'
        f'<p class="meta">Versão {esc(ctx["versao"])} · {esc(ctx["data"])} · válida até {esc(ctx["validade"])} · '
        f'Responsável: {esc(ctx["proponente"])}</p></div>'
        f'<table class="two"><tr><td class="half">{problem_html(ctx)}</td><td class="half">{solution_html(ctx)}</td></tr></table>'
        + block("Escopo e entregáveis", list_html(scope))
        + block("Prazo", f"<p>{esc(ctx['fases'])}</p>")
        + investment_html(ctx) + roi_html(ctx)
        + block("Condições", f'<p class="small">{esc(ctx["termos"])}</p><p class="small">{esc(SUPPORT_TERMS)}</p>')
        + block("Próximos passos", "<p>1. Reunião de início (30 min) · 2. Aceite desta proposta por escrito e entrada · "
                "3. Início do diagnóstico.</p>")
        + f'<p class="foot">{esc(AI_NOTICE)}</p>'
    )


def css_for(size: float) -> str:
    return f"""
    body {{ font-family: sans-serif; font-size: {size}pt; color: #14201d; line-height: 1.3; }}
    .head {{ background-color: #0b6b5b; color: #ffffff; padding: 10pt 12pt; margin-bottom: 6pt; }}
    .eyebrow {{ font-size: {size - 1.5}pt; margin: 0; color: #bfe8df; }}
    h1 {{ font-size: {size + 9}pt; margin: 2pt 0; color: #ffffff; }}
    .meta {{ margin: 2pt 0 0 0; color: #d3ebe5; font-size: {size - 0.5}pt; }}
    h2 {{ font-size: {size + 1.5}pt; color: #0b6b5b; margin: 7pt 0 2pt 0; }}
    p {{ margin: 1pt 0 2pt 0; }}
    ul {{ margin: 0 0 0 10pt; }}
    li {{ margin: 0 0 1pt 0; }}
    table.two {{ width: 100%; }}
    td.half {{ width: 50%; vertical-align: top; padding-right: 8pt; }}
    table.money {{ width: 100%; }}
    td.lbl {{ padding: 2pt 4pt 2pt 0; }}
    td.val {{ text-align: right; padding: 2pt 0; }}
    td.strong {{ font-weight: bold; color: #0b6b5b; }}
    .small {{ font-size: {size - 1}pt; color: #4a5b56; }}
    .foot {{ font-size: {size - 1.5}pt; color: #6b7c77; margin-top: 8pt; }}
    """


def render_pdf(markup: str, size: float) -> tuple[bytes, int]:
    """Desenha o HTML em paginas A4 e devolve (pdf, numero_de_paginas)."""
    story = fitz.Story(html=markup, user_css=css_for(size))
    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    media = fitz.paper_rect("a4")
    where = media + (PAGE_MARGIN, PAGE_MARGIN, -PAGE_MARGIN, -PAGE_MARGIN)
    pages, more = 0, 1
    while more:
        device = writer.begin_page(media)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
        pages += 1
        if more and pages >= MAX_RENDER_PAGES:
            pages += 1  # sinaliza "nao coube" e desiste em vez de repetir sem progresso
            break
    writer.close()
    return buffer.getvalue(), pages


def fit_one_page(markup: str) -> tuple[bytes, int, float]:
    """Reduz a fonte ate caber em 1 pagina; falha se nem a menor couber."""
    for size in FONT_SIZES:
        pdf, pages = render_pdf(markup, size)
        if pages == 1:
            return pdf, pages, size
    raise ValueError("O conteúdo não cabe em uma página. Reduza o escopo ou os textos do briefing.")


def generate(pedido_path: Path, out_path: Path, today: date | None = None, params: dict | None = None) -> dict:
    pedido = parse_pedido(Path(pedido_path).read_text(encoding="utf-8-sig"))  # tolera o BOM do Bloco de Notas
    missing = missing_fields(pedido)
    if missing:
        raise ValueError(f"Faltam no pedido: {', '.join(missing)}. Preencha antes de gerar a proposta.")
    context = build_context(pedido, params or load_params(), today or date.today())
    pdf, pages, size = fit_one_page(build_html(context))
    Path(out_path).write_bytes(pdf)
    return {"file": str(out_path), "pages": pages, "version": context["versao"], "valid_until": context["validade"],
            "font_size": size, "warnings": context["avisos"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pedido", help="caminho do arquivo PED-NNN-*.md")
    parser.add_argument("--out", required=True, help="PDF de saida")
    parser.add_argument("--json", action="store_true", help="saida JSON (para o painel)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = generate(Path(args.pedido), Path(args.out))
    except (ValueError, OSError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False) if args.json else f"Proposta {result['version']} gerada: {result['file']}")
    for warning in result["warnings"]:
        print(f"Aviso: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
