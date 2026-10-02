"""Calculadora de orcamento para projetos de automacao.

Os parametros (valor da hora, margem, pisos...) ficam em flowhub/parametros.json: mudar o
arquivo muda o proximo orcamento, sem tocar no codigo. Os valores sao hipoteses a validar
com vendas reais (veja vault/Precos/Parametros-de-Preco.md).

Exemplos:
  python flowhub/quote.py --complexity medio --hours 12
  python flowhub/quote.py --complexity complexo --hours 40 --adapt-hours 20 --client-hours-week 15 --client-hourly-cost 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PARAMS_PATH = Path(__file__).resolve().parent / "parametros.json"
WEEKS_PER_MONTH = 4
MONTHS_PER_YEAR = 12
DAYS_PER_MONTH = 30
ROUND_TO = -1  # dezenas de reais
COMPLEXITIES = ("simples", "medio", "complexo")
REQUIRED_PARAMS = (
    "versao", "valor_hora", "margem_risco", "desconto_adaptacao", "mensalidade_taxa",
    "mensalidade_minima", "entrada", "teto_roi", "pisos", "validade_dias",
)


def brl(value: float) -> str:
    return f"R$ {value:,.0f}".replace(",", ".")


def load_params(path: Path = PARAMS_PATH) -> dict:
    """Le e valida os parametros; falha com mensagem clara se faltar algo."""
    params = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_PARAMS if key not in params]
    if missing:
        raise ValueError(f"parametros.json sem os campos: {', '.join(missing)}")
    absent_floors = [name for name in COMPLEXITIES if name not in params["pisos"]]
    if absent_floors:
        raise ValueError(f"parametros.json sem piso para: {', '.join(absent_floors)}")
    return params


def monthly_saving(hours_per_week: float, hourly_cost: float) -> float:
    """Economia mensal do cliente: horas por semana x 4 x custo da hora."""
    return hours_per_week * WEEKS_PER_MONTH * hourly_cost


def payback_days(setup: float, monthly: float, saving: float) -> int | None:
    """Dias para o setup se pagar com a economia LIQUIDA da mensalidade; None se nunca paga."""
    net = saving - monthly
    if net <= 0:
        return None
    return round(setup / net * DAYS_PER_MONTH)


def annual_net_saving(setup: float, monthly: float, saving: float) -> float:
    """Economia do primeiro ano depois de pagar o setup e 12 mensalidades."""
    return saving * MONTHS_PER_YEAR - setup - MONTHS_PER_YEAR * monthly


def labor_cost(build_hours: float, adapt_hours: float, params: dict) -> float:
    """Custo da mao de obra; o desconto de reaproveitamento vale so para as horas de adaptacao."""
    effective_rate = params["valor_hora"] * (1 + params["margem_risco"])
    return build_hours * effective_rate + adapt_hours * effective_rate * (1 - params["desconto_adaptacao"])


def apply_roi_ceiling(raw_setup: float, floor: float, client_saving: float | None, params: dict) -> tuple[float, bool, bool]:
    """Devolve (setup, limitado_pelo_teto, inviavel). O piso sempre vence o teto de ROI."""
    if not client_saving:
        return raw_setup, False, False
    ceiling = client_saving * MONTHS_PER_YEAR * params["teto_roi"]
    if raw_setup <= ceiling:
        return raw_setup, False, False
    if ceiling < floor:
        return floor, False, True
    return ceiling, True, False


def build_quote(complexity: str, build_hours: float, adapt_hours: float = 0.0,
                client_saving: float | None = None, params: dict | None = None) -> dict:
    params = params or load_params()
    if complexity not in COMPLEXITIES:
        raise ValueError(f"complexidade invalida: {complexity}")
    if build_hours < 0 or adapt_hours < 0 or build_hours + adapt_hours <= 0:
        raise ValueError("as horas devem ser positivas")

    floor = params["pisos"][complexity]
    raw_setup = max(labor_cost(build_hours, adapt_hours, params), floor)
    setup, capped, unviable = apply_roi_ceiling(raw_setup, floor, client_saving, params)
    setup = round(setup, ROUND_TO)
    monthly = round(max(setup * params["mensalidade_taxa"], params["mensalidade_minima"]), ROUND_TO)

    warnings = []
    ceiling_pct = round(params["teto_roi"] * 100)
    if unviable:
        warnings.append(f"Inviável pelo ROI: o teto de {ceiling_pct}% da economia anual fica abaixo do piso. Rever escopo ou argumento de valor.")
    if capped:
        warnings.append(f"Preço limitado pelo teto de ROI ({ceiling_pct}% da economia anual do cliente).")
    never_pays = bool(client_saving) and payback_days(setup, monthly, client_saving) is None
    if never_pays:
        warnings.append("A mensalidade consome toda a economia do cliente: o setup nunca se paga.")

    return {
        "setup": setup,
        "monthly": monthly,
        "down_payment": round(setup * params["entrada"], ROUND_TO),
        "client_saving": client_saving,
        "payback_days": payback_days(setup, monthly, client_saving) if client_saving else None,
        "payback_gross_days": round(setup / client_saving * DAYS_PER_MONTH) if client_saving else None,
        "annual_net_saving": round(annual_net_saving(setup, monthly, client_saving)) if client_saving else None,
        "capped_by_roi": capped,
        "unviable_by_roi": unviable,
        "warnings": warnings,
        "valid_days": params["validade_dias"],
        "params_version": params["versao"],
    }


def resolve_saving(args: argparse.Namespace) -> float | None:
    """Economia mensal: informada direto ou calculada de horas por semana x custo da hora."""
    if args.client_saving is not None:
        return args.client_saving
    if args.client_hours_week is not None and args.client_hourly_cost is not None:
        return monthly_saving(args.client_hours_week, args.client_hourly_cost)
    return None


def print_quote(quote: dict) -> None:
    down_pct = round(quote["down_payment"] / quote["setup"] * 100)
    print(f"Setup (unico):      {brl(quote['setup'])}   (entrada {down_pct}%: {brl(quote['down_payment'])})")
    print(f"Suporte/mes:        {brl(quote['monthly'])}")
    if quote["client_saving"]:
        print(f"Economia do cliente: {brl(quote['client_saving'])}/mes")
    if quote["payback_days"] is not None:
        print(f"Payback liquido:    ~{quote['payback_days']} dias (bruto: ~{quote['payback_gross_days']})")
        print(f"Economia 1o ano:    {brl(quote['annual_net_saving'])} depois de setup e mensalidades")
    for warning in quote["warnings"]:
        print(f"Aviso: {warning}")
    print(f"Parametros: versao {quote['params_version']}; proposta valida por {quote['valid_days']} dias")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--complexity", choices=COMPLEXITIES, required=True)
    parser.add_argument("--hours", type=float, required=True, help="horas totais de entrega")
    parser.add_argument("--adapt-hours", type=float, default=0.0, help="quantas das horas partem de um fluxo pronto (recebem o desconto)")
    parser.add_argument("--client-saving", type=float, help="economia mensal do cliente em R$")
    parser.add_argument("--client-hours-week", type=float, help="horas por semana que o cliente gasta hoje")
    parser.add_argument("--client-hourly-cost", type=float, help="custo da hora do cliente em R$")
    parser.add_argument("--json", action="store_true", help="saida JSON (para o painel)")
    args = parser.parse_args()
    if args.hours <= 0 or not 0 <= args.adapt_hours <= args.hours:
        print("--hours deve ser maior que zero e --adapt-hours deve ficar entre 0 e --hours", file=sys.stderr)
        return 1
    try:
        quote = build_quote(args.complexity, args.hours - args.adapt_hours, args.adapt_hours, resolve_saving(args))
    except (ValueError, OSError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(quote, ensure_ascii=False))
    else:
        print_quote(quote)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
