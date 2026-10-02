"""Gera o pacote de desenvolvimento de um pedido: épicos, features, histórias e tasks para os agentes.

Lê vault/Pedidos/PED-NNN-*.md (tabela Features e Checklist de entrega) e grava em projetos/<cliente>/pacote/:
  00-LEIA-ME.md      como usar o pacote
  BACKLOG-DEV.md     épicos > features > histórias > tasks, com prompt pronto para cada agente
  tarefas.json       o mesmo backlog em formato de máquina (id, agente, depende_de, prompt)
  fluxos-base/       explicação nó a nó de cada fluxo de referência citado na feature
  templates/         fluxos-modelo anotados e modelos de entrega

Não copia dado pessoal: só o que está nas colunas da tabela de features.

Exemplo:
  python flowhub/pacote.py PED-002
"""
from __future__ import annotations

import argparse
import json
import re
import os
import shutil
import sys
import time
import unicodedata
from pathlib import Path

from explicar import explain_flow
from scan import read_documents

ROOT = Path(__file__).resolve().parent.parent
PED_ID_RE = re.compile(r"PED-[0-9]{3,}")
MAX_FEATURES = 50
MAX_REFS_PER_FEATURE = 5
MAX_FLOW_BYTES = 5_000_000
BACKTICK_RE = re.compile(r"`([^`]+)`")
MAX_SLUG = 60

TEMPLATE_RULES = (  # (palavras na feature, modelo)
    (("lead", "captação", "captacao", "formulário", "formulario"), "captacao-de-leads"),
    (("lembrete", "aniversário", "aniversario", "revisão", "revisao", "agendamento", "cobrança", "cobranca"), "lembrete-diario"),
)
ALWAYS_TEMPLATE = "alerta-de-falha"
HUMAN = "humano (Thiago)"


def slugify(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:MAX_SLUG]


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = re.split(r"\r?\n", text)
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = re.split(r"\s+#\s", match.group(2))[0].strip()
    return fields


def section(text: str, title: str) -> list[str]:
    found, out = False, []
    for line in re.split(r"\r?\n", text):
        if line.startswith("## "):
            if found:
                break
            found = line[3:].strip().lower().startswith(title.lower())
            continue
        if found:
            out.append(line)
    return out


def parse_features(text: str) -> list[dict]:
    features = []
    for line in section(text, "Features"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not re.match(r"\d", cells[0]):
            continue  # cabeçalho e separador
        if len(cells) < 6 or not cells[0].isdigit():
            raise ValueError(f"A linha {cells[0]!r} da tabela de Features não tem as 6 colunas (# | Feature | Origem | Critério | Horas | Fase).")
        hours = re.search(r"\d+(?:[.,]\d+)?", cells[4])
        phase = re.search(r"\d+", cells[5])
        features.append({
            "numero": int(cells[0]), "nome": cells[1], "origem": cells[2],
            "caminhos": [p for p in BACKTICK_RE.findall(cells[2]) if p.lower().endswith(".json")][:MAX_REFS_PER_FEATURE],
            "criterio": cells[3], "horas": float(hours.group().replace(",", ".")) if hours else 0.0,
            "fase": int(phase.group()) if phase else 1,
        })
    numbers = [f["numero"] for f in features]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Há duas features com o mesmo número na tabela de Features.")
    return features[:MAX_FEATURES]


def parse_checklist(text: str) -> list[str]:
    items = []
    for line in section(text, "Checklist de entrega"):
        match = re.match(r"^- \[[ xX]\]\s*(.+)$", line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def resolve_reference(path: str, root: Path) -> Path | None:
    """Fluxo de referência só vale se estiver dentro de _raw/ (o acervo): nada de caminho fora da pasta."""
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
        return None  # absoluto, unidade ou UNC: nem chega a tocar o disco
    base = (root / "_raw").resolve()
    candidate = (base / normalized.removeprefix("_raw/")).resolve()
    return candidate if long_path(candidate).is_file() and base in candidate.parents else None


def long_path(path: Path) -> Path:
    """No Windows o acervo tem caminhos acima de 260 caracteres: só o prefixo \\\\?\\ os deixa abrir."""
    text = str(path)
    return Path("\\\\?\\" + text) if os.name == "nt" and not text.startswith("\\\\?\\") else path


def short_name(name: str) -> str:
    """Nome da feature sem o detalhe entre parênteses (abas, colunas), que confunde a escolha do modelo e o nome do arquivo."""
    return name.split("(")[0].strip() or name.strip()


def pick_templates(feature: dict) -> list[str]:
    haystack = short_name(feature["nome"]).lower()
    return [name for words, name in TEMPLATE_RULES if any(w in haystack for w in words)]


def make_task(task_id: str, titulo: str, agente: str, prompt: str, entradas: list[str], saidas: list[str],
              pronto: str, depende_de: list[str]) -> dict:
    return {"id": task_id, "titulo": titulo, "agente": agente, "entradas": entradas, "saidas": saidas,
            "pronto_quando": pronto, "depende_de": depende_de, "prompt": prompt}


def feature_block(feature: dict, client: str, base_files: list[str], templates: list[str],
                  previous_qa: list[str], setup_task: str) -> dict:
    n, name = feature["numero"], feature["nome"]
    prefix = f"E2-F{n}"
    out_flow = f"projetos/{client}/fluxos/F{n}-{slugify(short_name(name))[:40].strip('-')}.json"
    plan = f"projetos/{client}/fluxos/F{n}-plano.md"
    reference = base_files or [f"projetos/{client}/pacote/templates/n8n/{t}.json" for t in templates]
    ref_text = ", ".join(reference) if reference else "nenhum fluxo pronto: construir do zero"
    criterion = feature["criterio"]
    plan_task = make_task(
        f"{prefix}-S1-T1", f"Planejar a feature {n}: o que fica, sai e entra", "construtor-n8n",
        f"Feature {n} do pedido: {name}. Leia {ref_text} e a explicação nó a nó em pacote/fluxos-base, se houver. "
        f"Liste em {plan} os nós que ficam, os que saem (credenciais e integrações do autor) e os que entram. "
        f"Critério de aceite: {criterion}",
        reference, [plan], "Plano lista nós que ficam, saem e entram", [setup_task, *previous_qa])
    build_task = make_task(
        f"{prefix}-S2-T1", f"Construir o fluxo da feature {n}", "construtor-n8n",
        f"Monte {out_flow} a partir de {ref_text}, seguindo {plan}. Use placeholders COLE_AQUI_ para IDs e "
        f"credenciais (nunca valores reais). Rode `python flowhub/scan.py {out_flow}` até ficar limpo.",
        [plan], [out_flow], "JSON válido, scan limpo, nós do plano implementados", [plan_task["id"]])
    qa_task = make_task(
        f"{prefix}-S3-T1", f"Validar a feature {n} contra o critério de aceite", "qa-fluxos",
        f"Valide {out_flow}: (1) `python flowhub/scan.py {out_flow}`; (2) `python flowhub/explicar.py {out_flow}` e confira "
        f"se cada nó faz o que o critério pede; (3) liste casos de teste com dados fictícios. Critério de aceite: {criterion}",
        [out_flow], [f"projetos/{client}/fluxos/F{n}-qa.md"], "Cada critério com evidência (passa ou falha)",
        [build_task["id"]])
    live_task = make_task(
        f"{prefix}-S3-T2", f"Teste no n8n real, feature {n}", HUMAN,
        f"Importe {out_flow} no n8n do cliente, preencha as credenciais e rode com dados de exemplo. "
        f"Registre as horas e o resultado no pedido.",
        [out_flow], ["resultado do teste no pedido (Horas reais e Histórico)"],
        "Fluxo executou no n8n com dado de exemplo", [qa_task["id"]])
    return {
        "id": prefix, "titulo": f"F{n} · {name}", "horas": feature["horas"], "fase": feature["fase"],
        "criterio_de_aceite": criterion, "origem": feature["origem"],
        "historias": [
            {"id": f"{prefix}-S1", "titulo": f"Como dev, entendo o fluxo de referência da F{n}", "tasks": [plan_task]},
            {"id": f"{prefix}-S2", "titulo": f"Como dev, construo a F{n} sem credencial do autor", "tasks": [build_task]},
            {"id": f"{prefix}-S3", "titulo": f"Como Thiago, sei que a F{n} atende ao aceite", "tasks": [qa_task, live_task]},
        ],
    }


def feature_gate_ids(blocks: list[dict]) -> list[str]:
    """Última task da última história de cada feature (o teste real), de que a próxima fase depende."""
    return [block["historias"][-1]["tasks"][-1]["id"] for block in blocks]


def setup_task_for(order_id: str) -> dict:
    return make_task(
        "E1-S1-T1", "Ambiente e acessos do cliente", "analista-de-pedido",
        f"Confirme com o cliente, sem pedir senha: planilha criada e compartilhada, conta do serviço de mensagens, "
        f"servidor do n8n e e-mail do alerta. Registre o que falta em vault/Pedidos/{order_id}-*.md.",
        [f"vault/Pedidos/{order_id}-*.md"], ["lista de acessos confirmados no pedido"],
        "Todos os acessos confirmados ou pendências registradas", [])


def delivery_agent(item: str) -> str:
    lowered = item.lower()
    if "qa-fluxos" in lowered or "scanner" in lowered:
        return "qa-fluxos"
    return "construtor-n8n" if "leia-me" in lowered else HUMAN


def closing_epics(client: str, checklist: list[str], gate_ids: list[str]) -> list[dict]:
    security = make_task(
        "E3-S1-T1", "Revisão de segurança e dados", "qa-fluxos",
        f"Rode `python flowhub/scan.py projetos/{client}` e confira: nenhuma credencial em arquivo, planilha privada, "
        f"opt-out respeitado, nenhum dado pessoal do cliente final no vault. Relate achados com severidade.",
        [f"projetos/{client}/"], [f"projetos/{client}/seguranca.md"], "Scan limpo e relatório gravado", gate_ids)
    errors = make_task(
        "E4-S1-T1", "Alerta de falha ativo", "construtor-n8n",
        f"Importe templates/n8n/alerta-de-falha.json, configure remetente e destino e ligue-o como fluxo de erro de "
        f"todos os fluxos de projetos/{client}/fluxos/.",
        [f"projetos/{client}/pacote/templates/n8n/alerta-de-falha.json"], [f"projetos/{client}/fluxos/alerta-de-falha.json"],
        "Falha provocada de propósito gera e-mail", gate_ids)
    accept = make_task(
        "E5-S1-T1", "Ensaio ponta a ponta e aceite", HUMAN,
        "Rode o caminho completo com dados de exemplo no n8n do cliente e peça o aceite por escrito. "
        "Registre aceite_em, aceite_canal e aceite_evidencia no pedido.",
        ["fluxos validados"], ["aceite registrado no pedido"], "Aceite do cliente com evidência",
        ["E3-S1-T1", "E4-S1-T1"])
    delivery = [
        make_task(f"E6-S1-T{i}", item, delivery_agent(item),
                  f"Item do checklist de entrega: {item}. Use templates/entrega/ quando houver modelo.",
                  ["templates/entrega/"], [item], "Item marcado no Checklist de entrega do pedido", ["E5-S1-T1"])
        for i, item in enumerate(checklist, 1)]
    return [
        {"id": "E3", "titulo": "Segurança e dados", "historias": [
            {"id": "E3-S1", "titulo": "Como cliente, tenho meus dados protegidos", "tasks": [security]}]},
        {"id": "E4", "titulo": "Observabilidade e falhas", "historias": [
            {"id": "E4-S1", "titulo": "Como dono, sou avisado quando algo falha", "tasks": [errors]}]},
        {"id": "E5", "titulo": "Validação e aceite", "historias": [
            {"id": "E5-S1", "titulo": "Como Thiago, tenho o aceite do cliente", "tasks": [accept]}]},
        {"id": "E6", "titulo": "Entrega e suporte", "historias": [
            {"id": "E6-S1", "titulo": "Como cliente, sei operar e tenho suporte", "tasks": delivery}]},
    ]


def build_backlog(order_id: str, client: str, features: list[dict], checklist: list[str],
                  base_files: dict[int, list[str]], templates: dict[int, list[str]]) -> list[dict]:
    setup = setup_task_for(order_id)
    blocks: list[dict] = []
    for feature in sorted(features, key=lambda f: (f["fase"], f["numero"])):
        earlier = [b for b in blocks if b["fase"] < feature["fase"]]
        blocks.append(feature_block(feature, client, base_files.get(feature["numero"], []),
                                    templates.get(feature["numero"], []), feature_gate_ids(earlier), setup["id"]))
    discovery = {"id": "E1", "titulo": "Descoberta e acessos", "historias": [
        {"id": "E1-S1", "titulo": "Como dev, tenho os acessos para começar", "tasks": [setup]}]}
    main = {"id": "E2", "titulo": "Features do pedido", "historias": [], "features": blocks}
    return [discovery, main, *closing_epics(client, checklist, feature_gate_ids(blocks))]


def flat_tasks(backlog: list[dict]) -> list[dict]:
    tasks = []
    for epic in backlog:
        stories = epic.get("historias", []) + [h for f in epic.get("features", []) for h in f["historias"]]
        tasks += [{**t, "epico": epic["id"]} for story in stories for t in story["tasks"]]
    return tasks


def render_story(story: dict, out: list[str]) -> None:
    out.append(f"#### História {story['id']}: {story['titulo']}")
    for t in story["tasks"]:
        out += [f"- [ ] **{t['id']}** · {t['titulo']} · agente: `{t['agente']}`",
                f"  - Depende de: {', '.join(t['depende_de']) or 'nada'}",
                f"  - Pronto quando: {t['pronto_quando']}",
                f"  - Prompt: {t['prompt']}"]
    out.append("")


def render_backlog(order_id: str, client: str, backlog: list[dict]) -> str:
    out = [f"# Backlog de desenvolvimento · {order_id} · {client}", "",
           "Execute na ordem de `depende_de`. Marque `[x]` ao concluir; registre horas no pedido.", ""]
    for epic in backlog:
        out += [f"## Épico {epic['id']}: {epic['titulo']}", ""]
        for story in epic.get("historias", []):
            render_story(story, out)
        for feat in epic.get("features", []):
            out += [f"### Feature {feat['id']}: {feat['titulo']} ({feat['horas']:g} h, fase {feat['fase']})",
                    f"Critério de aceite: {feat['criterio_de_aceite']}", ""]
            for story in feat["historias"]:
                render_story(story, out)
    return "\n".join(out)


def render_readme(order_id: str, client: str, total_hours: float, tasks: list[dict], notes: list[str]) -> str:
    agents = sorted({t["agente"] for t in tasks})
    lines = [f"# Pacote de desenvolvimento · {order_id} · {client}", "",
             f"- {len(tasks)} tasks, {total_hours:g} horas orçadas, agentes: {', '.join(agents)}",
             "- `BACKLOG-DEV.md`: épicos, features, histórias e tasks com prompt pronto",
             "- `tarefas.json`: o mesmo backlog para ler por máquina",
             "- `fluxos-base/`: cada fluxo de referência explicado nó a nó",
             "- `templates/n8n/`: fluxos-modelo anotados (JSON + explicação) · `templates/entrega/`: modelos de entrega", "",
             "## Como usar", "1. Abra o Claude Code na pasta do projeto.",
             "2. Peça: `Execute a task E1-S1-T1 do pacote` e siga a ordem de `depende_de`.",
             "3. Cada task diz o agente, o que entra, o que sai e quando está pronta.", "",
             "## Limites que você precisa saber",
             "- Os fluxos-modelo foram validados na estrutura (JSON, conexões, scanner), **não foram executados no n8n**: "
             "ajuste parâmetros à versão do seu n8n e teste antes de entregar.",
             "- O formato de mensagem do WhatsApp (API oficial da Meta) deve ser conferido na documentação da versão em uso.",
             "- A explicação nó a nó é gerada por regra, sem IA: confira nós de código ou expressões complexas no editor do n8n."]
    if notes:
        lines += ["", "## Avisos desta geração", *notes]
    return "\n".join(lines + [""])


def find_order(order_id: str, root: Path) -> Path:
    if not PED_ID_RE.fullmatch(order_id):
        raise ValueError("Número de pedido inválido (esperado PED-001).")
    matches = sorted((root / "vault" / "Pedidos").glob(f"{order_id}-*.md"))
    if not matches:
        raise FileNotFoundError(f"Pedido {order_id} não encontrado em vault/Pedidos.")
    return matches[0]


def explain_references(features: list[dict], client: str, root: Path) -> tuple[dict[str, str], dict[int, list[str]], list[str]]:
    files: dict[str, str] = {}
    base_files: dict[int, list[str]] = {}
    notes: list[str] = []
    for feature in features:
        n = feature["numero"]
        for index, path in enumerate(feature["caminhos"], 1):
            name = Path(path.replace("\\", "/")).name
            resolved = resolve_reference(path, root)
            try:
                too_big = resolved is not None and long_path(resolved).stat().st_size > MAX_FLOW_BYTES
                docs = read_documents(resolved) if resolved and not too_big else []
                explained = "\n\n---\n\n".join(explain_flow(d) for d in docs)
            except (OSError, ValueError, RecursionError):
                docs, explained = [], ""
            if not docs:
                notes.append(f"- Feature {n}: fluxo de referência não encontrado ou ilegível em _raw/ ({name}).")
                continue
            rel = f"fluxos-base/F{n}-{index}-{slugify(resolved.stem)[:40].strip('-') or 'fluxo'}.md"
            files[rel] = explained
            base_files.setdefault(n, []).append(f"projetos/{client}/pacote/{rel}")
    return files, base_files, notes


def copy_templates(chosen: set[str], root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for name in sorted(chosen):
        for suffix in (".json", ".explicado.md"):
            source = root / "templates" / "n8n" / f"{name}{suffix}"
            if source.is_file():
                files[f"templates/n8n/{name}{suffix}"] = source.read_text(encoding="utf-8")
    for source in sorted((root / "templates" / "entrega").glob("*.md")):
        files[f"templates/entrega/{source.name}"] = source.read_text(encoding="utf-8")
    return files


def build_package(order_id: str, client: str, features: list[dict], checklist: list[str], root: Path) -> tuple[dict[str, str], list[dict]]:
    files, base_files, notes = explain_references(features, client, root)
    templates = {f["numero"]: pick_templates(f) for f in features}
    chosen = {ALWAYS_TEMPLATE, *(t for names in templates.values() for t in names)}
    files.update(copy_templates(chosen, root))
    backlog = build_backlog(order_id, client, features, checklist, base_files, templates)
    tasks = flat_tasks(backlog)
    files["BACKLOG-DEV.md"] = render_backlog(order_id, client, backlog)
    files["tarefas.json"] = json.dumps({"pedido": order_id, "cliente": client, "epicos": backlog, "tarefas": tasks},
                                       ensure_ascii=False, indent=2)
    files["00-LEIA-ME.md"] = render_readme(order_id, client, sum(f["horas"] for f in features), tasks, notes)
    return files, tasks


def write_package(root: Path, client: str, files: dict[str, str]) -> None:
    """Grava num diretório temporário e só então troca: falha no meio nunca deixa pacote pela metade.
    O pacote anterior vira pacote.bak-<hora> (guarda os [x] marcados à mão); nunca é apagado."""
    projects = (root / "projetos").resolve()
    parent = root / "projetos" / client
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or projects not in parent.resolve().parents:
        raise ValueError("A pasta do projeto é inválida (atalho ou fora de projetos/).")
    tmp = parent / f".pacote-tmp-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for rel, content in files.items():
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        dest = parent / "pacote"
        if dest.exists():
            os.replace(dest, parent / f"pacote.bak-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1_000_000:06d}")
        os.replace(tmp, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def generate(order_id: str, root: Path = ROOT) -> dict:
    text = find_order(order_id, root).read_text(encoding="utf-8-sig")
    client = slugify(parse_frontmatter(text).get("cliente", ""))
    features = parse_features(text)
    if not client:
        raise ValueError("O pedido não tem o campo cliente preenchido.")
    if not features:
        raise ValueError("O pedido não tem features na tabela: quebre o pedido em features antes de gerar o pacote.")
    files, tasks = build_package(order_id, client, features, parse_checklist(text), root)
    write_package(root, client, files)
    return {"pedido": order_id, "cliente": client, "pasta": f"projetos/{client}/pacote", "arquivos": len(files),
            "tasks": len(tasks), "features": len(features)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pedido", help="número do pedido, ex.: PED-002")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = generate(args.pedido)
    except ValueError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Falha de arquivo: {error.__class__.__name__}", file=sys.stderr)
        print("Erro: não consegui gravar o pacote. Feche arquivos abertos da pasta projetos/ e tente de novo.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Pacote de {result['pedido']} ({result['cliente']}): {result['features']} features, {result['tasks']} tasks, "
              f"{result['arquivos']} arquivos em {result['pasta']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
