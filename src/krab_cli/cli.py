"""Krab CLI — Spec-Driven Development toolkit.

Commands:
  krab optimize   — Optimize specs (compress, deduplicate, analyze)
  krab convert    — Convert between Markdown, JSON, and YAML
  krab analyze    — Analyze spec quality, tokens, and similarity
  krab diff       — Compare two specs for similarity
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from krab_cli import __version__

app = typer.Typer(
    name="krab",
    help="Krab CLI -- Spec-Driven Development toolkit for AI agents",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

optimize_app = typer.Typer(help="Optimize specs for token efficiency", no_args_is_help=True)
convert_app = typer.Typer(help="Convert specs between formats", no_args_is_help=True)
analyze_app = typer.Typer(help="Analyze spec quality and metrics", no_args_is_help=True)
search_app = typer.Typer(help="Search and index spec corpus", no_args_is_help=True)
diff_app = typer.Typer(help="Compare spec versions (delta encoding)", no_args_is_help=True)
spec_app = typer.Typer(
    help="Generate specs from templates (task, architecture, plan, skill, refine)",
    no_args_is_help=True,
)
registry_app = typer.Typer(
    help="Manage spec registry — save remote Git repo URLs as aliases",
    no_args_is_help=True,
)
memory_app = typer.Typer(help="Manage project memory (.sdd/)", no_args_is_help=True)
agent_app = typer.Typer(
    help="Generate instruction files for AI agents (Claude Code, Copilot, Codex)",
    no_args_is_help=True,
)
cache_app = typer.Typer(help="Manage analysis result cache", no_args_is_help=True)
workflow_app = typer.Typer(
    help="Run multi-step SDD workflows (spec-create, implement, review, full-cycle)",
    no_args_is_help=True,
)

app.add_typer(optimize_app, name="optimize")
app.add_typer(convert_app, name="convert")
app.add_typer(analyze_app, name="analyze")
app.add_typer(search_app, name="search")
app.add_typer(diff_app, name="diff")
app.add_typer(spec_app, name="spec")
spec_app.add_typer(registry_app, name="registry")
app.add_typer(memory_app, name="memory")
app.add_typer(agent_app, name="agent")
app.add_typer(cache_app, name="cache")
app.add_typer(workflow_app, name="workflow")


# ─── Version callback ────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        from krab_cli.utils.display import print_logo

        print_logo(f"v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", help="Show version", callback=_version_callback),
    ] = None,
) -> None:
    """Krab CLI -- Spec-Driven Development toolkit for AI agents."""


# ═══════════════════════════════════════════════════════════════════════════
# INIT command — Project setup wizard
# ═══════════════════════════════════════════════════════════════════════════


AGENT_CHOICES = {
    "claude": "Claude Code (Anthropic) — CLAUDE.md + .claude/commands/",
    "copilot": "GitHub Copilot — .github/copilot-instructions.md + agents/prompts/skills",
    "codex": "OpenAI Codex — AGENTS.md + .agents/skills/",
}

ARCHITECTURE_CHOICES = [
    "monolith",
    "microservices",
    "hexagonal",
    "clean-architecture",
    "event-driven",
    "serverless",
    "modular-monolith",
]


@app.command("init")
def init_project(
    name: Annotated[str, typer.Option("--name", "-n", help="Project name")] = "",
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent: claude, copilot, codex")] = "",
    skip_wizard: Annotated[
        bool, typer.Option("--skip-wizard", help="Skip interactive wizard")
    ] = False,
) -> None:
    """Initialize a new SDD project with agent selection and full setup wizard.

    This is the entry point for any new project. It will:
    1. Select the AI agent (Claude Code, Copilot, or Codex)
    2. Set up project memory (name, description, stack, conventions)
    3. Generate global specs (Constitution, GuardRails, Runbook)
    4. Create the default SDD lifecycle workflow
    5. Generate agent instruction files and slash commands
    """
    from rich.panel import Panel
    from rich.table import Table

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_info,
        print_success,
        print_warning,
    )

    console = get_console()
    print_header("Krab SDD Project Setup", "Interactive wizard")

    store = MemoryStore()
    if store.is_initialized:
        print_warning("Projeto ja inicializado em .sdd/")
        overwrite = typer.confirm(
            "Deseja reinicializar? (dados existentes serao preservados)",
            default=False,
        )
        if not overwrite:
            raise typer.Exit()

    # ── Step 1: Agent Selection ──────────────────────────────────────
    console.print("\n[bold cyan]Step 1/5[/bold cyan] — Selecione o agente de IA\n")

    if not agent:
        if skip_wizard:
            agent = "claude"
        else:
            table = Table(show_header=True, border_style="cyan", title="Agentes Disponiveis")
            table.add_column("#", style="dim", width=4)
            table.add_column("Agent", style="bold yellow", min_width=12)
            table.add_column("Descricao")

            agent_keys = list(AGENT_CHOICES.keys())
            for i, (key, desc) in enumerate(AGENT_CHOICES.items(), 1):
                table.add_row(str(i), key, desc)
            console.print(table)
            console.print()

            choice = typer.prompt(
                "Escolha o agente (1-3 ou nome) [Enter=claude]", default="1"
            )
            if choice.isdigit() and 1 <= int(choice) <= len(agent_keys):
                agent = agent_keys[int(choice) - 1]
            elif choice.lower() in AGENT_CHOICES:
                agent = choice.lower()
            else:
                print_error(f"Agente invalido: {choice}")
                raise typer.Exit(code=1)

    if agent not in AGENT_CHOICES:
        print_error(f"Agente invalido: {agent}. Opcoes: {', '.join(AGENT_CHOICES)}")
        raise typer.Exit(code=1)

    print_success(f"Agente selecionado: {agent} — {AGENT_CHOICES[agent]}")

    # ── Step 2: Project Memory Setup ─────────────────────────────────
    console.print("\n[bold cyan]Step 2/5[/bold cyan] — Configuracao do projeto\n")

    if not name:
        if skip_wizard:
            name = Path.cwd().name
        else:
            name = typer.prompt(
                f"Nome do projeto [Enter={Path.cwd().name}]", default=Path.cwd().name
            )

    description = ""
    architecture = ""
    tech_stack: dict[str, str] = {}
    conventions: dict[str, str] = {}

    if not skip_wizard:
        description = typer.prompt("Descricao do projeto [Enter=pular]", default="")

        # Architecture
        console.print(f"\n[dim]Estilos: {', '.join(ARCHITECTURE_CHOICES)}[/dim]")
        architecture = typer.prompt("Estilo de arquitetura [Enter=pular]", default="")

        # Tech stack
        console.print("\n[dim]Informe a tech stack (Enter para pular/encerrar):[/dim]")
        while True:
            key = typer.prompt("  Componente (ex: backend, frontend, database) [Enter=pular]", default="")
            if not key:
                break
            value = typer.prompt(f"  Tecnologia para {key} [Enter=pular]", default="")
            if value:
                tech_stack[key] = value

        # Conventions
        console.print("\n[dim]Convencoes do projeto (Enter para pular/encerrar):[/dim]")
        while True:
            key = typer.prompt("  Convencao (ex: naming, testing, git) [Enter=pular]", default="")
            if not key:
                break
            value = typer.prompt(f"  Regra para {key} [Enter=pular]", default="")
            if value:
                conventions[key] = value

    # Initialize memory
    memory = store.init(
        project_name=name,
        description=description,
        agent_preference=agent,
        tech_stack=tech_stack,
        architecture_style=architecture,
        conventions=conventions,
    )
    print_success(f"Memoria do projeto inicializada: {store.sdd_path}/")

    # ── Step 3: Generate Global Specs ────────────────────────────────
    console.print("\n[bold cyan]Step 3/5[/bold cyan] — Gerando specs globais\n")

    _generate_global_specs(store, memory)
    print_success("Specs globais geradas: constitution, guardrails, runbook")

    # ── Step 4: Create Default Workflow ──────────────────────────────
    console.print("\n[bold cyan]Step 4/5[/bold cyan] — Criando workflow padrao\n")

    from krab_cli.workflows.builtins import get_builtin

    try:
        wf = get_builtin("sdd-lifecycle")
        wf_path = store.sdd_path / "workflows" / "sdd-lifecycle.yaml"
        wf.save(wf_path)
        print_success(f"Workflow padrao criado: {wf_path}")
    except ValueError:
        print_info("Workflow sdd-lifecycle sera registrado como built-in")

    # ── Step 5: Generate Agent Files + Slash Commands ────────────────
    console.print("\n[bold cyan]Step 5/5[/bold cyan] — Gerando arquivos do agente\n")

    try:
        from krab_cli.agents import sync_agent

        paths = sync_agent(agent)
        for p in paths:
            print_success(f"[{agent}] {p}")
    except Exception as e:
        print_warning(f"Aviso ao gerar arquivos do agente: {e}")

    # Generate slash commands
    try:
        from krab_cli.workflows.commands import generate_all as gen_commands

        cmd_results = gen_commands(root=Path.cwd(), agent=agent)
        cmd_total = sum(len(v) for v in cmd_results.values())
        if cmd_total:
            print_success(f"Gerados {cmd_total} slash commands para {agent}")
    except Exception:
        pass

    # ── Summary ──────────────────────────────────────────────────────
    console.print()
    summary = Panel(
        f"[bold green]Projeto '{name}' inicializado com sucesso![/bold green]\n\n"
        f"  Agente: [yellow]{agent}[/yellow]\n"
        f"  Workflow: [yellow]sdd-lifecycle[/yellow]\n"
        f"  Specs globais: [yellow]constitution, guardrails, runbook[/yellow]\n\n"
        f"[dim]Proximos passos:[/dim]\n"
        f"  1. Revise as specs globais em .sdd/specs/\n"
        f"  2. Use [bold]krab spec new task -n 'feature'[/bold] para criar specs\n"
        f"  3. Use [bold]krab workflow run sdd-lifecycle -s 'feature'[/bold] para executar o ciclo\n"
        f"  4. Use [bold]krab spec clarify <spec>[/bold] para enriquecer specs com Q&A\n",
        title="Setup Completo",
        border_style="green",
    )
    console.print(summary)


def _generate_global_specs(store, memory) -> None:
    """Generate the three global spec files: constitution, guardrails, runbook."""
    import krab_cli.templates.constitution
    import krab_cli.templates.guardrails
    import krab_cli.templates.runbook  # noqa: F401
    from krab_cli.templates import build_context, get_template

    global_specs = {
        "constitution": "Constituicao do Projeto",
        "guardrails": "GuardRails do Projeto",
        "runbook": "Runbook do Projeto",
    }

    for spec_type, spec_name in global_specs.items():
        template = get_template(spec_type)
        ctx = build_context(name=spec_name, description=memory.description, store=store)
        content = template.render(ctx)

        filename = Path(template.suggested_filename(ctx))
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(content, encoding="utf-8")

        # Track in memory
        memory.global_specs[spec_type] = str(filename)

        # Record in history
        if store.is_initialized:
            store.add_history_entry(
                {
                    "action": "spec_new",
                    "template": spec_type,
                    "name": spec_name,
                    "file": str(filename),
                }
            )

    # Save updated memory with global_specs paths
    store.save_memory(memory)


# ═══════════════════════════════════════════════════════════════════════════
# OPTIMIZE commands
# ═══════════════════════════════════════════════════════════════════════════


@optimize_app.command("run")
def optimize_run(
    file: Annotated[Path, typer.Argument(help="Path to spec file (Markdown)")],
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output file")] = None,
    no_compress: Annotated[bool, typer.Option("--no-compress", help="Skip compression")] = False,
    no_dedup: Annotated[bool, typer.Option("--no-dedup", help="Skip deduplication")] = False,
    min_freq: Annotated[int, typer.Option("--min-freq", help="Min frequency for aliases")] = 3,
    max_aliases: Annotated[int, typer.Option("--max-aliases", help="Max aliases")] = 50,
    threshold: Annotated[
        float, typer.Option("--threshold", help="Dedup similarity threshold (0-100)")
    ] = 90.0,
    context_window: Annotated[
        int, typer.Option("--context-window", help="Target context window size")
    ] = 8192,
) -> None:
    """Run the full optimization pipeline on a spec file."""
    from krab_cli.core.optimizer import optimize_spec
    from krab_cli.utils.display import (
        print_aliases_table,
        print_comparison_table,
        print_header,
        print_info,
        print_metrics_table,
        print_success,
    )

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Krab Optimizer", f"Processing: {file.name}")

    result = optimize_spec(
        text,
        compress=not no_compress,
        deduplicate=not no_dedup,
        min_freq=min_freq,
        max_aliases=max_aliases,
        dedup_threshold=threshold,
        context_window=context_window,
    )

    print_metrics_table("Compression Metrics", result.compression_metrics)
    print_comparison_table("Context Quality", result.quality_before, result.quality_after)

    if result.aliases:
        print_aliases_table(result.aliases)

    if result.duplicates_found:
        print_info(f"Duplicates found: {result.duplicates_found}")
        print_info(f"Sections removed: {result.sections_removed}")

    # Write output
    out_path = output or file.with_suffix(".optimized.md")
    out_path.write_text(result.final_output, encoding="utf-8")
    print_success(f"Optimized spec saved to: {out_path}")


@optimize_app.command("aliases")
def optimize_aliases(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    min_freq: Annotated[int, typer.Option("--min-freq")] = 2,
    max_aliases: Annotated[int, typer.Option("--max-aliases")] = 50,
) -> None:
    """Show the alias dictionary that would be generated for a spec."""
    from krab_cli.core.huffman import build_frequency_table, create_alias_dictionary
    from krab_cli.utils.display import print_aliases_table, print_header, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Alias Analysis", file.name)

    freq_table = build_frequency_table(text, min_freq=min_freq)
    print_metrics_table("Top Frequencies", dict(list(freq_table.items())[:20]))

    aliases = create_alias_dictionary(freq_table, max_aliases=max_aliases)
    print_aliases_table(aliases)


@optimize_app.command("dedup")
def optimize_dedup(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    threshold: Annotated[float, typer.Option("--threshold")] = 80.0,
    method: Annotated[str, typer.Option("--method")] = "weighted",
) -> None:
    """Find duplicate sections in a spec."""
    from krab_cli.core.fuzzy import find_duplicates
    from krab_cli.core.optimizer import split_into_sections
    from krab_cli.utils.display import print_duplicates, print_header, print_info

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    sections = split_into_sections(text)
    print_header("Deduplication Analysis", f"{file.name} — {len(sections)} sections")

    matches = find_duplicates(sections, threshold=threshold, method=method)
    print_duplicates(matches)
    print_info(f"Total matches above {threshold}%: {len(matches)}")


# ═══════════════════════════════════════════════════════════════════════════
# CONVERT commands
# ═══════════════════════════════════════════════════════════════════════════


@convert_app.command("md2json")
def convert_md_to_json(
    file: Annotated[Path, typer.Argument(help="Input Markdown file")],
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
    indent: Annotated[int, typer.Option("--indent")] = 2,
) -> None:
    """Convert Markdown spec to JSON."""
    from krab_cli.converters.converter import md_to_json
    from krab_cli.utils.display import print_code, print_header, print_success

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    result = md_to_json(text, indent=indent)

    print_header("Convert", f"MD → JSON: {file.name}")

    if output:
        output.write_text(result, encoding="utf-8")
        print_success(f"Saved to: {output}")
    else:
        print_code(result, "json")


@convert_app.command("json2md")
def convert_json_to_md(
    file: Annotated[Path, typer.Argument(help="Input JSON file")],
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Convert JSON spec to Markdown."""
    from krab_cli.converters.converter import json_to_md
    from krab_cli.utils.display import print_code, print_header, print_success

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    result = json_to_md(text)

    print_header("Convert", f"JSON → MD: {file.name}")

    if output:
        output.write_text(result, encoding="utf-8")
        print_success(f"Saved to: {output}")
    else:
        print_code(result, "markdown")


@convert_app.command("md2yaml")
def convert_md_to_yaml(
    file: Annotated[Path, typer.Argument(help="Input Markdown file")],
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Convert Markdown spec to YAML."""
    from krab_cli.converters.converter import md_to_yaml
    from krab_cli.utils.display import print_code, print_header, print_success

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    result = md_to_yaml(text)

    print_header("Convert", f"MD → YAML: {file.name}")

    if output:
        output.write_text(result, encoding="utf-8")
        print_success(f"Saved to: {output}")
    else:
        print_code(result, "yaml")


@convert_app.command("yaml2md")
def convert_yaml_to_md(
    file: Annotated[Path, typer.Argument(help="Input YAML file")],
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Convert YAML spec to Markdown."""
    from krab_cli.converters.converter import yaml_to_md
    from krab_cli.utils.display import print_code, print_header, print_success

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    result = yaml_to_md(text)

    print_header("Convert", f"YAML → MD: {file.name}")

    if output:
        output.write_text(result, encoding="utf-8")
        print_success(f"Saved to: {output}")
    else:
        print_code(result, "markdown")


@convert_app.command("auto")
def convert_auto(
    file: Annotated[Path, typer.Argument(help="Input file")],
    to: Annotated[str, typer.Option("--to", help="Target format: md, json, yaml")],
    output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
) -> None:
    """Auto-detect input format and convert to target format."""
    from krab_cli.converters.converter import convert, detect_format
    from krab_cli.utils.display import get_console, print_header, print_success

    _check_file(file)
    from_fmt = detect_format(file)
    text = file.read_text(encoding="utf-8")

    print_header("Convert", f"{from_fmt.upper()} → {to.upper()}: {file.name}")
    result = convert(text, from_fmt, to)

    if output:
        output.write_text(result, encoding="utf-8")
        print_success(f"Saved to: {output}")
    else:
        get_console().print(result)


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE commands
# ═══════════════════════════════════════════════════════════════════════════


@analyze_app.command("tokens")
def analyze_tokens(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    encoding: Annotated[str, typer.Option("--encoding")] = "cl100k_base",
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Count tokens and analyze token efficiency."""
    from krab_cli.core.tokens import estimate_cost, token_summary
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_header, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Token Analysis", file.name)

    params = {"encoding": encoding}
    cached = None if no_cache else cache.get(text, "analyze_tokens", params)
    if cached:
        print_metrics_table("Token Summary", cached["summary"])
        print_metrics_table("Estimated Cost (per call)", cached["cost"])
        return

    summary = token_summary(text, encoding)
    print_metrics_table("Token Summary", summary)

    cost = estimate_cost(summary["tokens"])
    print_metrics_table("Estimated Cost (per call)", cost)

    cache.put(text, "analyze_tokens", {"summary": summary, "cost": cost}, params)


@analyze_app.command("quality")
def analyze_quality(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    context_window: Annotated[int, typer.Option("--context-window")] = 8192,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Analyze spec information density and context utilization."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_header, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Quality Analysis", file.name)

    params = {"context_window": context_window}
    cached = None if no_cache else cache.get(text, "analyze_quality", params)
    if cached:
        print_metrics_table("Context Quality", cached)
        return

    from krab_cli.core.similarity import context_quality_score

    quality = context_quality_score(text, context_window)
    print_metrics_table("Context Quality", quality)

    cache.put(text, "analyze_quality", quality, params)


@analyze_app.command("compare")
def analyze_compare(
    file_a: Annotated[Path, typer.Argument(help="First spec file")],
    file_b: Annotated[Path, typer.Argument(help="Second spec file")],
) -> None:
    """Compare two specs for similarity."""
    from krab_cli.core.similarity import full_comparison
    from krab_cli.utils.display import print_header, print_info, print_metrics_table

    _check_file(file_a)
    _check_file(file_b)

    text_a = file_a.read_text(encoding="utf-8")
    text_b = file_b.read_text(encoding="utf-8")
    print_header("Spec Comparison", f"{file_a.name} vs {file_b.name}")

    report = full_comparison(text_a, text_b)
    print_metrics_table(
        "Similarity Scores",
        {
            "Jaccard": report.jaccard,
            "Cosine": report.cosine,
            "N-gram Overlap": report.ngram_overlap,
            "Combined": report.combined,
            "Verdict": report.verdict,
        },
    )
    print_info(f"Shared terms: {', '.join(report.shared_terms[:10])}")
    print_info(f"Unique to A: {', '.join(report.unique_to_a[:10])}")
    print_info(f"Unique to B: {', '.join(report.unique_to_b[:10])}")


@analyze_app.command("freq")
def analyze_freq(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    min_freq: Annotated[int, typer.Option("--min-freq")] = 2,
    top: Annotated[int, typer.Option("--top")] = 30,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Show term frequency analysis for a spec."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_header, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Frequency Analysis", file.name)

    params = {"min_freq": min_freq, "top": top}
    cached = None if no_cache else cache.get(text, "analyze_freq", params)
    if cached:
        print_metrics_table(f"Top {top} Terms (min_freq={min_freq})", cached)
        return

    from krab_cli.core.huffman import build_frequency_table

    freq_table = build_frequency_table(text, min_freq=min_freq)
    top_items = dict(list(freq_table.items())[:top])
    print_metrics_table(f"Top {top} Terms (min_freq={min_freq})", top_items)

    cache.put(text, "analyze_freq", top_items, params)


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE commands — Wave 1: Entropy, Readability, Ambiguity, Substrings
# ═══════════════════════════════════════════════════════════════════════════


@analyze_app.command("entropy")
def analyze_entropy(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Analyze information entropy, Markov predictability, and perplexity."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import get_console, print_header, print_info, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Entropy Analysis", file.name)

    cached = None if no_cache else cache.get(text, "analyze_entropy")
    if cached:
        print_metrics_table("Information Theory Metrics", cached["metrics"])
        if cached.get("patterns"):
            print_info("Top predictable patterns:")
            for state, next_token, prob in cached["patterns"]:
                get_console().print(
                    f"  [dim]{state}[/dim] -> [yellow]{next_token}[/yellow] ({prob:.0%})"
                )
        return

    from krab_cli.core.entropy import full_entropy_analysis

    report = full_entropy_analysis(text)
    metrics = {
        "Shannon Entropy (bits)": report.entropy,
        "Entropy Grade": report.entropy_grade,
        "Perplexity": report.perplexity,
        "Perplexity Grade": report.perplexity_grade,
        "Markov Predictability": report.markov.predictability,
        "Predictability Grade": report.markov.predictability_grade,
        "Token Count": report.token_count,
        "Unique Tokens": report.unique_tokens,
        "Vocabulary Richness": report.vocabulary_richness,
    }
    print_metrics_table("Information Theory Metrics", metrics)

    patterns = []
    if report.markov.top_patterns:
        print_info("Top predictable patterns:")
        for state, next_token, prob in report.markov.top_patterns[:8]:
            get_console().print(
                f"  [dim]{state}[/dim] -> [yellow]{next_token}[/yellow] ({prob:.0%})"
            )
            patterns.append([state, next_token, prob])

    cache.put(text, "analyze_entropy", {"metrics": metrics, "patterns": patterns})


@analyze_app.command("readability")
def analyze_readability(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Analyze readability scores (Flesch-Kincaid, Gunning Fog, etc)."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_header, print_info, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Readability Analysis", file.name)

    cached = None if no_cache else cache.get(text, "analyze_readability")
    if cached:
        print_metrics_table("Readability Scores", cached["metrics"])
        print_info(f"Recommendation: {cached['recommendation']}")
        return

    from krab_cli.core.readability import full_readability_analysis

    report = full_readability_analysis(text)
    metrics = {
        "Flesch-Kincaid Grade": report.flesch_kincaid_grade,
        "Flesch Reading Ease": report.flesch_reading_ease,
        "Coleman-Liau Index": report.coleman_liau,
        "Gunning Fog Index": report.gunning_fog,
        "ARI Score": report.ari,
        "Avg Words/Sentence": report.avg_words_per_sentence,
        "Complex Word %": report.complex_word_pct,
        "Overall Grade": report.overall_grade,
    }
    print_metrics_table("Readability Scores", metrics)
    print_info(f"Recommendation: {report.recommendation}")

    cache.put(
        text,
        "analyze_readability",
        {
            "metrics": metrics,
            "recommendation": report.recommendation,
        },
    )


@analyze_app.command("ambiguity")
def analyze_ambiguity(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    top: Annotated[int, typer.Option("--top")] = 20,
) -> None:
    """Detect vague/ambiguous terms that increase hallucination risk."""
    from rich.table import Table

    from krab_cli.core.ambiguity import detect_ambiguity
    from krab_cli.utils.display import get_console, print_header, print_info, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Ambiguity Analysis", file.name)

    report = detect_ambiguity(text)
    print_metrics_table(
        "Precision Metrics",
        {
            "Precision Score": report.precision_score,
            "Grade": report.grade,
            "Total Words": report.total_words,
            "Ambiguous Terms Found": report.ambiguous_terms,
            "HIGH Severity": report.severity_counts.get("HIGH", 0),
            "MEDIUM Severity": report.severity_counts.get("MEDIUM", 0),
            "LOW Severity": report.severity_counts.get("LOW", 0),
        },
    )

    if report.matches:
        table = Table(title="Ambiguity Findings", show_header=True, border_style="yellow")
        table.add_column("#", style="dim", width=4)
        table.add_column("Term", style="bold red", min_width=12)
        table.add_column("Line", justify="right", width=5)
        table.add_column("Severity", width=8)
        table.add_column("Suggestion", style="green")

        for i, m in enumerate(report.matches[:top], 1):
            sev_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}.get(m.severity, "dim")
            table.add_row(
                str(i), m.term, str(m.line_number), f"[{sev_color}]{m.severity}[/]", m.suggestion
            )

        get_console().print(table)

    print_info(report.recommendation)


@analyze_app.command("substrings")
def analyze_substrings(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    min_words: Annotated[int, typer.Option("--min-words")] = 3,
    top: Annotated[int, typer.Option("--top")] = 20,
) -> None:
    """Find repeated substrings/phrases wasting tokens."""
    from rich.table import Table

    from krab_cli.core.substrings import find_repeated_phrases, total_waste_analysis
    from krab_cli.utils.display import get_console, print_header, print_metrics_table

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Repeated Substring Analysis", file.name)

    waste = total_waste_analysis(text)
    print_metrics_table("Waste Summary", waste)

    phrases = find_repeated_phrases(text, min_words=min_words)
    if phrases:
        table = Table(title="Repeated Phrases", show_header=True, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Phrase", style="yellow", max_width=50)
        table.add_column("Count", justify="right", width=6)
        table.add_column("Savings", justify="right", style="green")

        for i, p in enumerate(phrases[:top], 1):
            table.add_row(str(i), p.text, str(p.count), f"{p.savings_potential} chars")

        get_console().print(table)


@analyze_app.command("risk")
def analyze_risk(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    context_window: Annotated[int, typer.Option("--context-window")] = 8192,
) -> None:
    """Assess hallucination risk score for a spec."""
    from rich.table import Table

    from krab_cli.core.risk import assess_hallucination_risk
    from krab_cli.utils.display import (
        get_console,
        print_header,
        print_info,
        print_metrics_table,
        print_warning,
    )

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Hallucination Risk Assessment", file.name)

    report = assess_hallucination_risk(text, context_window)

    print_metrics_table(
        "Risk Overview",
        {
            "Overall Risk Score": f"{report.overall_score}/100",
            "Risk Level": report.risk_level,
            "Safe for Agents": "Yes" if report.safe_for_agents else "No",
            "Spec Word Count": report.spec_word_count,
        },
    )

    table = Table(title="Risk Factors", show_header=True, border_style="cyan")
    table.add_column("Factor", style="bold", min_width=22)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Weight", justify="right", width=8)
    table.add_column("Severity", width=10)
    table.add_column("Detail", max_width=45)

    for f in report.factors:
        sev_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(
            f.severity, "dim"
        )
        table.add_row(
            f.name, f"{f.score:.2f}", f"{f.weight:.2f}", f"[{sev_color}]{f.severity}[/]", f.detail
        )

    get_console().print(table)

    if report.recommendations:
        get_console().print()
        for rec in report.recommendations:
            print_warning(rec) if report.overall_score >= 40 else print_info(rec)


@analyze_app.command("chunking")
def analyze_chunking(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
) -> None:
    """Compare chunking strategies for optimal context splitting."""
    from rich.table import Table

    from krab_cli.core.chunking import compare_strategies
    from krab_cli.utils.display import get_console, print_header

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Chunking Strategy Comparison", file.name)

    results = compare_strategies(text)

    table = Table(title="Strategy Comparison", show_header=True, border_style="cyan")
    table.add_column("Strategy", style="bold", min_width=15)
    table.add_column("Chunks", justify="right", width=8)
    table.add_column("Avg Tokens", justify="right", width=10)
    table.add_column("Min", justify="right", width=6)
    table.add_column("Max", justify="right", width=6)
    table.add_column("Coherence", justify="right", width=10)
    table.add_column("Verdict", max_width=30)

    for r in results:
        is_rec = "RECOMMENDED" in r.recommendation
        name = f"[bold green]{r.strategy}[/bold green]" if is_rec else r.strategy
        table.add_row(
            name,
            str(r.total_chunks),
            str(r.avg_chunk_tokens),
            str(r.min_chunk_tokens),
            str(r.max_chunk_tokens),
            f"{r.coherence_score:.3f}",
            r.recommendation,
        )

    get_console().print(table)


@analyze_app.command("keywords")
def analyze_keywords(
    file: Annotated[Path, typer.Argument(help="Path to spec file")],
    top: Annotated[int, typer.Option("--top")] = 20,
) -> None:
    """Extract key terms using RAKE and TextRank algorithms."""
    from rich.table import Table

    from krab_cli.core.semantic import rake_extract, textrank_sentences
    from krab_cli.utils.display import get_console, print_header, print_info

    _check_file(file)
    text = file.read_text(encoding="utf-8")
    print_header("Keyword Extraction", file.name)

    keywords = rake_extract(text, top_n=top)
    if keywords:
        table = Table(title="RAKE Keywords", show_header=True, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Keyword Phrase", style="yellow", min_width=25)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Freq", justify="right", width=5)

        for i, kw in enumerate(keywords, 1):
            table.add_row(str(i), kw.phrase, f"{kw.score:.2f}", str(kw.frequency))
        get_console().print(table)

    sentences = textrank_sentences(text, top_n=5)
    if sentences:
        get_console().print()
        print_info("Top sentences by TextRank:")
        for sent, score in sentences:
            get_console().print(f"  [{score:.3f}] {sent[:100]}...")


# ─── Batch analysis ──────────────────────────────────────────────────────

_BATCH_TYPES = ("tokens", "quality", "entropy", "readability")


@analyze_app.command("batch")
def analyze_batch(
    directory: Annotated[Path, typer.Argument(help="Directory containing spec files")],
    analysis: Annotated[
        str,
        typer.Option(
            "-a", "--analysis", help="Analysis type: tokens, quality, entropy, readability"
        ),
    ] = "tokens",
    pattern: Annotated[str, typer.Option("-p", "--pattern", help="Glob pattern")] = "*.md",
    context_window: Annotated[int, typer.Option("--context-window")] = 8192,
    encoding: Annotated[str, typer.Option("--encoding")] = "cl100k_base",
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Skip cache")] = False,
) -> None:
    """Run analysis on all spec files in a directory.

    Outputs a summary table with one row per file.
    Supports caching -- repeated runs on unchanged files are instant.
    """
    from rich.table import Table

    from krab_cli.utils import cache
    from krab_cli.utils.display import get_console, print_error, print_header, print_info

    if analysis not in _BATCH_TYPES:
        print_error(f"Unknown analysis type: {analysis}. Must be one of: {', '.join(_BATCH_TYPES)}")
        raise typer.Exit(code=1)

    if not directory.is_dir():
        print_error(f"Not a directory: {directory}")
        raise typer.Exit(code=1)

    files = sorted(directory.glob(pattern))
    files = [f for f in files if f.is_file()]
    if not files:
        print_info(f"No files matching '{pattern}' in {directory}")
        raise typer.Exit()

    print_header("Batch Analysis", f"{analysis} | {len(files)} files in {directory}")

    if analysis == "tokens":
        from krab_cli.core.tokens import estimate_cost, token_summary

        table = Table(
            title=f"Token Analysis ({len(files)} files)", show_header=True, border_style="cyan"
        )
        table.add_column("File", style="bold", max_width=35)
        table.add_column("Chars", justify="right")
        table.add_column("Words", justify="right")
        table.add_column("Tokens", justify="right", style="metric")
        table.add_column("Chars/Tok", justify="right")
        table.add_column("Cost (USD)", justify="right", style="yellow")

        total_tokens = 0
        for f in files:
            text = f.read_text(encoding="utf-8")
            params = {"encoding": encoding}
            cached_result = None if no_cache else cache.get(text, "analyze_tokens", params)
            if cached_result:
                s = cached_result["summary"]
                c = cached_result["cost"]
            else:
                s = token_summary(text, encoding)
                c = estimate_cost(s["tokens"])
                cache.put(text, "analyze_tokens", {"summary": s, "cost": c}, params)
            total_tokens += s["tokens"]
            table.add_row(
                f.name,
                str(s["characters"]),
                str(s["words"]),
                str(s["tokens"]),
                f"{s['chars_per_token']:.1f}",
                f"${c['total_cost_usd']:.4f}",
            )

        get_console().print(table)
        print_info(f"Total tokens: {total_tokens:,}")

    elif analysis == "quality":
        from krab_cli.core.similarity import context_quality_score

        table = Table(
            title=f"Quality Analysis ({len(files)} files)", show_header=True, border_style="cyan"
        )
        table.add_column("File", style="bold", max_width=35)
        table.add_column("Words", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Util %", justify="right", style="metric")
        table.add_column("Density", justify="right")
        table.add_column("Redundancy", justify="right")
        table.add_column("Grade", justify="center")

        for f in files:
            text = f.read_text(encoding="utf-8")
            params = {"context_window": context_window}
            cached_result = None if no_cache else cache.get(text, "analyze_quality", params)
            if cached_result:
                q = cached_result
            else:
                q = context_quality_score(text, context_window)
                cache.put(text, "analyze_quality", q, params)
            table.add_row(
                f.name,
                str(q["word_count"]),
                str(q["estimated_tokens"]),
                f"{q['utilization_pct']:.1f}",
                f"{q['information_density']:.3f}",
                f"{q['redundancy_ratio']:.3f}",
                q["density_grade"],
            )

        get_console().print(table)

    elif analysis == "entropy":
        from krab_cli.core.entropy import full_entropy_analysis

        table = Table(
            title=f"Entropy Analysis ({len(files)} files)", show_header=True, border_style="cyan"
        )
        table.add_column("File", style="bold", max_width=35)
        table.add_column("Entropy", justify="right", style="metric")
        table.add_column("Grade", justify="center")
        table.add_column("Perplexity", justify="right")
        table.add_column("Predict.", justify="right")
        table.add_column("Vocab Rich.", justify="right")

        for f in files:
            text = f.read_text(encoding="utf-8")
            cached_result = None if no_cache else cache.get(text, "analyze_entropy")
            if cached_result:
                m = cached_result["metrics"]
            else:
                report = full_entropy_analysis(text)
                m = {
                    "Shannon Entropy (bits)": report.entropy,
                    "Entropy Grade": report.entropy_grade,
                    "Perplexity": report.perplexity,
                    "Markov Predictability": report.markov.predictability,
                    "Vocabulary Richness": report.vocabulary_richness,
                }
                cache.put(text, "analyze_entropy", {"metrics": m, "patterns": []})
            table.add_row(
                f.name,
                f"{m['Shannon Entropy (bits)']:.2f}",
                m["Entropy Grade"],
                f"{m['Perplexity']:.1f}",
                f"{m['Markov Predictability']:.3f}",
                f"{m['Vocabulary Richness']:.3f}",
            )

        get_console().print(table)

    elif analysis == "readability":
        from krab_cli.core.readability import full_readability_analysis

        table = Table(
            title=f"Readability Analysis ({len(files)} files)",
            show_header=True,
            border_style="cyan",
        )
        table.add_column("File", style="bold", max_width=35)
        table.add_column("FK Grade", justify="right", style="metric")
        table.add_column("Ease", justify="right")
        table.add_column("Fog", justify="right")
        table.add_column("ARI", justify="right")
        table.add_column("Grade", justify="center")

        for f in files:
            text = f.read_text(encoding="utf-8")
            cached_result = None if no_cache else cache.get(text, "analyze_readability")
            if cached_result:
                m = cached_result["metrics"]
            else:
                report = full_readability_analysis(text)
                m = {
                    "Flesch-Kincaid Grade": report.flesch_kincaid_grade,
                    "Flesch Reading Ease": report.flesch_reading_ease,
                    "Gunning Fog Index": report.gunning_fog,
                    "ARI Score": report.ari,
                    "Overall Grade": report.overall_grade,
                }
                cache.put(
                    text,
                    "analyze_readability",
                    {"metrics": m, "recommendation": report.recommendation},
                )
            table.add_row(
                f.name,
                f"{m['Flesch-Kincaid Grade']:.1f}",
                f"{m['Flesch Reading Ease']:.1f}",
                f"{m['Gunning Fog Index']:.1f}",
                f"{m['ARI Score']:.1f}",
                m["Overall Grade"],
            )

        get_console().print(table)


# ═══════════════════════════════════════════════════════════════════════════
# SEARCH commands — Wave 2: BM25, MinHash LSH
# ═══════════════════════════════════════════════════════════════════════════


@search_app.command("bm25")
def search_bm25(
    directory: Annotated[Path, typer.Argument(help="Directory containing spec files")],
    query: Annotated[str, typer.Option("-q", "--query", help="Search query")],
    top: Annotated[int, typer.Option("--top")] = 10,
) -> None:
    """Search specs using BM25 ranking."""
    from rich.table import Table

    from krab_cli.core.bm25 import BM25Index
    from krab_cli.utils.display import get_console, print_header, print_info, print_metrics_table

    if not directory.is_dir():
        from krab_cli.utils.display import print_error

        print_error(f"Not a directory: {directory}")
        raise typer.Exit(code=1)

    # Load all spec files
    docs: dict[str, str] = {}
    for f in directory.glob("*.md"):
        docs[f.name] = f.read_text(encoding="utf-8")

    if not docs:
        print_info("No .md files found in directory.")
        raise typer.Exit()

    print_header("BM25 Search", f"Query: '{query}' in {len(docs)} specs")

    index = BM25Index()
    index.index(docs)
    results = index.search(query, top_k=top)

    print_metrics_table("Index Stats", index.get_stats())

    if results:
        table = Table(title="Search Results", show_header=True, border_style="cyan")
        table.add_column("Rank", style="dim", width=5)
        table.add_column("Spec", style="bold yellow", min_width=20)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Matched Terms", style="green")
        table.add_column("Length", justify="right", width=8)

        for r in results:
            table.add_row(
                str(r.rank),
                r.doc_id,
                f"{r.score:.3f}",
                ", ".join(r.matched_terms[:5]),
                str(r.doc_length),
            )
        get_console().print(table)
    else:
        print_info("No matching specs found.")


@search_app.command("duplicates")
def search_duplicates(
    directory: Annotated[Path, typer.Argument(help="Directory containing spec files")],
    threshold: Annotated[float, typer.Option("--threshold")] = 0.5,
) -> None:
    """Find near-duplicate specs using MinHash + LSH (scalable)."""
    from rich.table import Table

    from krab_cli.core.minhash import find_near_duplicates
    from krab_cli.utils.display import get_console, print_header, print_info

    if not directory.is_dir():
        from krab_cli.utils.display import print_error

        print_error(f"Not a directory: {directory}")
        raise typer.Exit(code=1)

    docs: dict[str, str] = {}
    for f in directory.glob("*.md"):
        docs[f.name] = f.read_text(encoding="utf-8")

    if len(docs) < 2:
        print_info("Need at least 2 spec files to compare.")
        raise typer.Exit()

    print_header("MinHash + LSH Duplicate Detection", f"{len(docs)} specs, threshold={threshold}")

    matches = find_near_duplicates(docs, threshold=threshold)

    if matches:
        table = Table(title="Near-Duplicate Pairs", show_header=True, border_style="yellow")
        table.add_column("Spec A", style="yellow", min_width=20)
        table.add_column("Spec B", style="yellow", min_width=20)
        table.add_column("Similarity", justify="right", style="bold")

        for m in matches:
            table.add_row(m.doc_a, m.doc_b, f"{m.estimated_similarity:.2%}")
        get_console().print(table)
    else:
        print_info("No near-duplicates found above threshold.")


@search_app.command("budget")
def search_budget(
    directory: Annotated[Path, typer.Argument(help="Directory containing spec files")],
    budget: Annotated[int, typer.Option("--budget", help="Token budget")] = 8192,
    strategy: Annotated[str, typer.Option("--strategy")] = "knapsack",
) -> None:
    """Optimize which specs to load within a token budget."""
    from rich.table import Table

    from krab_cli.core.budget import optimize_budget, score_sections
    from krab_cli.utils.display import get_console, print_header, print_info, print_metrics_table

    if not directory.is_dir():
        from krab_cli.utils.display import print_error

        print_error(f"Not a directory: {directory}")
        raise typer.Exit(code=1)

    docs: dict[str, str] = {}
    for f in directory.glob("*.md"):
        docs[f.name] = f.read_text(encoding="utf-8")

    if not docs:
        print_info("No .md files found.")
        raise typer.Exit()

    print_header("Token Budget Optimizer", f"Budget: {budget} tokens, Strategy: {strategy}")

    sections = score_sections(docs)
    result = optimize_budget(sections, budget=budget, strategy=strategy)

    print_metrics_table(
        "Budget Result",
        {
            "Budget": result.budget,
            "Used Tokens": result.total_tokens,
            "Utilization": f"{result.utilization_pct}%",
            "Total Value": result.total_value,
            "Selected Specs": len(result.selected),
            "Excluded Specs": len(result.excluded),
        },
    )

    table = Table(title="Selected Specs", show_header=True, border_style="green")
    table.add_column("Spec", style="bold green", min_width=20)
    table.add_column("Tokens", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Efficiency", justify="right")

    for s in sorted(result.selected, key=lambda x: -x.efficiency):
        table.add_row(s.name, str(s.token_cost), f"{s.info_value:.4f}", f"{s.efficiency:.4f}")
    get_console().print(table)

    if result.excluded:
        print_info(f"Excluded: {', '.join(s.name for s in result.excluded)}")


# ═══════════════════════════════════════════════════════════════════════════
# DIFF commands — Wave 2: Delta encoding
# ═══════════════════════════════════════════════════════════════════════════


@diff_app.command("versions")
def diff_versions(
    old_file: Annotated[Path, typer.Argument(help="Old spec version")],
    new_file: Annotated[Path, typer.Argument(help="New spec version")],
) -> None:
    """Compare two spec versions with delta encoding."""
    from rich.table import Table

    from krab_cli.core.delta import compute_delta, delta_token_savings
    from krab_cli.utils.display import get_console, print_header, print_metrics_table

    _check_file(old_file)
    _check_file(new_file)

    old_text = old_file.read_text(encoding="utf-8")
    new_text = new_file.read_text(encoding="utf-8")

    print_header("Spec Delta Analysis", f"{old_file.name} -> {new_file.name}")

    report = compute_delta(old_text, new_text)
    print_metrics_table(
        "Delta Summary",
        {
            "Lines Before": report.total_lines_before,
            "Lines After": report.total_lines_after,
            "Lines Added": report.lines_added,
            "Lines Removed": report.lines_removed,
            "Lines Modified": report.lines_modified,
            "Change Ratio": report.change_ratio,
        },
    )

    savings = delta_token_savings(old_text, new_text)
    print_metrics_table("Token Savings", savings)

    if report.changes:
        table = Table(title="Changes", show_header=True, border_style="cyan")
        table.add_column("Type", width=10)
        table.add_column("Section", style="bold", min_width=20)
        table.add_column("Lines", justify="right", width=8)
        table.add_column("Detail", max_width=50)

        for c in report.changes[:20]:
            color = {"added": "green", "removed": "red", "modified": "yellow"}.get(
                c.change_type.value, "dim"
            )
            detail = c.new_content[:50] if c.new_content else c.old_content[:50]
            table.add_row(
                f"[{color}]{c.change_type.value.upper()}[/]",
                c.section,
                f"{c.line_start}-{c.line_end}",
                detail,
            )
        get_console().print(table)


@diff_app.command("sections")
def diff_sections(
    old_file: Annotated[Path, typer.Argument(help="Old spec version")],
    new_file: Annotated[Path, typer.Argument(help="New spec version")],
) -> None:
    """Show section-level diff between two spec versions."""
    from rich.table import Table

    from krab_cli.core.delta import generate_section_delta
    from krab_cli.utils.display import get_console, print_header, print_info

    _check_file(old_file)
    _check_file(new_file)

    old_text = old_file.read_text(encoding="utf-8")
    new_text = new_file.read_text(encoding="utf-8")

    print_header("Section Delta", f"{old_file.name} -> {new_file.name}")

    deltas = generate_section_delta(old_text, new_text)

    if not deltas:
        print_info("No section-level changes detected.")
        return

    table = Table(title="Section Changes", show_header=True, border_style="cyan")
    table.add_column("Section", style="bold", min_width=25)
    table.add_column("Type", width=10)
    table.add_column("Detail", max_width=50)

    for d in deltas:
        color = {"added": "green", "removed": "red", "modified": "yellow"}.get(d["type"], "dim")
        detail = d.get("content", d.get("new_preview", ""))[:50]
        table.add_row(d["section"], f"[{color}]{d['type'].upper()}[/]", detail)

    get_console().print(table)


# ═══════════════════════════════════════════════════════════════════════════
# SPEC commands — Generate specs from templates
# ═══════════════════════════════════════════════════════════════════════════


@spec_app.command("new")
def spec_new(
    template_type: Annotated[
        str, typer.Argument(help="Template: task, architecture, plan, skill, refining")
    ],
    name: Annotated[str, typer.Option("--name", "-n", help="Spec name")] = "",
    description: Annotated[str, typer.Option("--desc", "-d")] = "",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Generate a new spec from a template."""
    # Import all templates to trigger registration
    import krab_cli.templates.architecture
    import krab_cli.templates.clarify
    import krab_cli.templates.constitution
    import krab_cli.templates.guardrails
    import krab_cli.templates.plan
    import krab_cli.templates.refining
    import krab_cli.templates.runbook
    import krab_cli.templates.skill
    import krab_cli.templates.task  # noqa: F401
    from krab_cli.memory import MemoryStore
    from krab_cli.templates import build_context, get_template
    from krab_cli.utils.display import print_header, print_info, print_success

    if not name:
        name = typer.prompt("Nome da spec")

    print_header("Spec Generator", f"type={template_type}")

    try:
        template = get_template(template_type)
    except ValueError as e:
        from krab_cli.utils.display import print_error

        print_error(str(e))
        raise typer.Exit(code=1) from e

    store = MemoryStore()
    ctx = build_context(name=name, description=description, store=store)

    content = template.render(ctx)
    filename = output or Path(template.suggested_filename(ctx))
    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text(content, encoding="utf-8")

    # Record in history
    if store.is_initialized:
        store.add_history_entry(
            {
                "action": "spec_new",
                "template": template_type,
                "name": name,
                "file": str(filename),
            }
        )

    print_success(f"Spec gerada: {filename}")
    print_info(f"Template: spec.{template_type} | {len(content)} chars")


@spec_app.command("refine")
def spec_refine(
    file: Annotated[Path, typer.Argument(help="Spec file to refine")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Analyze a spec with Tree-of-Thought and generate refinement plan."""
    import krab_cli.templates.refining  # noqa: F401
    from krab_cli.memory import MemoryStore
    from krab_cli.templates import build_context, get_template
    from krab_cli.utils.display import get_console, print_header, print_info, print_success

    _check_file(file)
    source_text = file.read_text(encoding="utf-8")

    print_header("Spec Refiner (Tree-of-Thought)", file.name)

    store = MemoryStore()
    ctx = build_context(
        name=file.stem,
        description=f"Refinamento de {file.name}",
        store=store,
        extra={"source_text": source_text},
    )

    template = get_template("refining")
    content = template.render(ctx)

    from krab_cli.memory import SPECS_DIR

    out_file = output or Path(f"{SPECS_DIR}/spec.refining.{file.stem}.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")

    # Show summary
    from krab_cli.templates.refining import analyze_spec_for_refinement

    plan = analyze_spec_for_refinement(source_text)

    print_info(f"Tipo detectado: spec.{plan.spec_type}")
    print_info(f"Perguntas geradas: {plan.total_questions}")
    print_info(f"Iterações estimadas: {plan.estimated_iterations}")

    if plan.critical_gaps:
        from krab_cli.utils.display import print_warning

        print_warning(f"Gaps críticos: {len(plan.critical_gaps)}")
        for gap in plan.critical_gaps:
            get_console().print(f"  [red]•[/red] {gap}")

    print_success(f"Refinamento salvo: {out_file}")


@spec_app.command("clarify")
def spec_clarify(
    file: Annotated[Path, typer.Argument(help="Spec file to clarify")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Interactive Q&A mode")
    ] = True,
    agent_mode: Annotated[
        bool, typer.Option("--agent", help="Generate Q&A for agent consumption (non-interactive)")
    ] = False,
) -> None:
    """Clarify a spec with interactive Q&A to enrich its content.

    Analyzes the spec, generates targeted questions, and (in interactive mode)
    prompts you to answer them. Answers are saved as a clarify document that
    can be used by agents to rewrite the spec with richer content.
    """
    import krab_cli.templates.clarify  # noqa: F401
    from krab_cli.memory import MemoryStore
    from krab_cli.templates import build_context, get_template
    from krab_cli.templates.clarify import generate_clarify_questions
    from krab_cli.utils.display import (
        get_console,
        print_header,
        print_info,
        print_success,
        print_warning,
    )

    _check_file(file)
    source_text = file.read_text(encoding="utf-8")

    print_header("Spec Clarify (Q&A)", file.name)

    session = generate_clarify_questions(source_text, spec_file=str(file))
    console = get_console()

    print_info(f"Tipo detectado: spec.{session.spec_type}")
    print_info(f"Perguntas geradas: {session.total_questions}")

    if not session.questions:
        print_success("Spec ja esta bem detalhada! Nenhuma pergunta gerada.")
        return

    # Interactive mode — ask questions and record answers
    if interactive and not agent_mode:
        console.print("\n[bold]Responda as perguntas para enriquecer a spec:[/bold]")
        console.print("[dim]Pressione Enter sem texto para pular uma pergunta[/dim]\n")

        priority_order = session.by_priority()
        for i, q in enumerate(priority_order, 1):
            priority_icon = {
                "critical": "[bold red][!!][/bold red]",
                "high": "[red][!][/red]",
                "medium": "[yellow][~][/yellow]",
                "low": "[dim][.][/dim]",
            }.get(q.priority, "[-]")

            console.print(
                f"\n  {priority_icon} [{i}/{len(priority_order)}] "
                f"[bold]{q.section}[/bold]\n"
                f"  {q.question}"
            )

            try:
                answer = input("  > ").strip()
                if answer:
                    q.answer = answer
                    q.answered = True
                    console.print("  [green]Registrado[/green]")
                else:
                    console.print("  [dim]Pulado[/dim]")
            except (EOFError, KeyboardInterrupt):
                print_warning("\nSessao interrompida. Salvando respostas parciais...")
                break

        print_info(
            f"Respondidas: {session.answered_count}/{session.total_questions} "
            f"({session.completion_pct:.0f}%)"
        )

    # Generate output document
    store = MemoryStore()
    ctx = build_context(
        name=file.stem,
        description=f"Clarify de {file.name}",
        store=store,
        extra={"session": session, "source_text": source_text},
    )

    template = get_template("clarify")
    content = template.render(ctx)

    from krab_cli.memory import SPECS_DIR

    out_file = output or Path(f"{SPECS_DIR}/spec.clarify.{file.stem}.md")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")

    # Record in history
    if store.is_initialized:
        store.add_history_entry(
            {
                "action": "spec_clarify",
                "template": "clarify",
                "name": file.stem,
                "file": str(out_file),
                "answered": session.answered_count,
                "total": session.total_questions,
            }
        )

    print_success(f"Documento de clarify salvo: {out_file}")

    if session.answered_count > 0:
        console.print(
            "\n[dim]Proximo passo: use o agente para incorporar as respostas na spec:[/dim]\n"
            f"  krab workflow run spec-create -s \"{file.stem}\" --agent claude\n"
        )


# ── Spec Archive ─────────────────────────────────────────────────────────


@spec_app.command("archive")
def spec_archive(
    specs: Annotated[
        list[str],
        typer.Argument(help="Spec file paths or names to archive"),
    ],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Archive without confirmation")
    ] = False,
) -> None:
    """Archive specs by moving them to .sdd/archived/.

    Moves spec files to .sdd/archived/ and updates project references
    to ignore them. Accepts one or more file paths or spec names.
    """
    import shutil

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_info,
        print_success,
        print_warning,
    )

    console = get_console()
    print_header("Spec Archive", f"{len(specs)} spec(s)")

    store = MemoryStore()

    # Ensure .sdd/archived/ exists
    archived_dir = store.sdd_path / "archived"
    archived_dir.mkdir(parents=True, exist_ok=True)

    # Resolve spec paths
    resolved: list[Path] = []
    for spec_ref in specs:
        spec_path = Path(spec_ref)
        # Try direct path first
        if spec_path.exists() and spec_path.is_file():
            resolved.append(spec_path)
            continue
        # Try inside .sdd/specs/
        sdd_path = store.sdd_path / "specs" / spec_ref
        if sdd_path.exists():
            resolved.append(sdd_path)
            continue
        # Try with spec. prefix
        if not spec_ref.startswith("spec."):
            prefixed = store.sdd_path / "specs" / f"spec.{spec_ref}.md"
            if prefixed.exists():
                resolved.append(prefixed)
                continue
        print_warning(f"Spec nao encontrada: {spec_ref}")

    if not resolved:
        print_error("Nenhuma spec encontrada para arquivar.")
        raise typer.Exit(code=1)

    # Show what will be archived
    from rich.table import Table

    table = Table(show_header=True, border_style="cyan", title="Specs para arquivar")
    table.add_column("#", style="dim", width=4)
    table.add_column("Spec", style="bold yellow")
    table.add_column("Size", style="cyan", justify="right")

    for i, spec_path in enumerate(resolved, 1):
        size_kb = spec_path.stat().st_size / 1024
        table.add_row(str(i), spec_path.name, f"{size_kb:.1f} KB")
    console.print(table)

    if not force:
        confirm = typer.confirm(
            f"\nArquivar {len(resolved)} spec(s)?", default=True
        )
        if not confirm:
            raise typer.Exit()

    # Move files to archived/
    archived_files: list[str] = []
    for spec_path in resolved:
        dest = archived_dir / spec_path.name
        # Handle name conflicts in archived/
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = archived_dir / f"{stem}.{counter}{suffix}"
                counter += 1
        shutil.move(str(spec_path), str(dest))
        archived_files.append(spec_path.name)
        print_info(f"  {spec_path.name} -> {dest}")

    # Update memory: remove from global_specs if present
    if store.is_initialized:
        memory = store.load_memory()
        updated = False
        for spec_name in archived_files:
            for key, filepath in list(memory.global_specs.items()):
                if spec_name in filepath:
                    del memory.global_specs[key]
                    updated = True
        if updated:
            store.save_memory(memory)

        # Record in history
        for spec_name in archived_files:
            store.add_history_entry(
                {
                    "action": "spec_archive",
                    "file": spec_name,
                    "destination": str(archived_dir / spec_name),
                }
            )

    print_success(f"Arquivadas {len(archived_files)} spec(s) em {archived_dir}/")


# ── Spec Delete ──────────────────────────────────────────────────────────


@spec_app.command("delete")
def spec_delete(
    specs: Annotated[
        list[str],
        typer.Argument(help="Spec file paths or names to delete"),
    ],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Delete without confirmation")
    ] = False,
) -> None:
    """Delete one or more spec files permanently.

    Accepts file paths or spec names. Will prompt for confirmation
    unless --force is used.
    """
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_info,
        print_success,
        print_warning,
    )

    console = get_console()
    print_header("Spec Delete", f"{len(specs)} spec(s)")

    store = MemoryStore()

    # Resolve spec paths
    resolved: list[Path] = []
    for spec_ref in specs:
        spec_path = Path(spec_ref)
        # Try direct path first
        if spec_path.exists() and spec_path.is_file():
            resolved.append(spec_path)
            continue
        # Try inside .sdd/specs/
        sdd_path = store.sdd_path / "specs" / spec_ref
        if sdd_path.exists():
            resolved.append(sdd_path)
            continue
        # Try with spec. prefix
        if not spec_ref.startswith("spec."):
            prefixed = store.sdd_path / "specs" / f"spec.{spec_ref}.md"
            if prefixed.exists():
                resolved.append(prefixed)
                continue
        # Try inside .sdd/archived/
        archived_path = store.sdd_path / "archived" / spec_ref
        if archived_path.exists():
            resolved.append(archived_path)
            continue
        print_warning(f"Spec nao encontrada: {spec_ref}")

    if not resolved:
        print_error("Nenhuma spec encontrada para excluir.")
        raise typer.Exit(code=1)

    # Show what will be deleted
    from rich.table import Table

    table = Table(show_header=True, border_style="red", title="Specs para excluir")
    table.add_column("#", style="dim", width=4)
    table.add_column("Spec", style="bold red")
    table.add_column("Location", style="dim")
    table.add_column("Size", style="cyan", justify="right")

    for i, spec_path in enumerate(resolved, 1):
        size_kb = spec_path.stat().st_size / 1024
        table.add_row(str(i), spec_path.name, str(spec_path.parent), f"{size_kb:.1f} KB")
    console.print(table)

    if not force:
        confirm = typer.confirm(
            f"\n[IRREVERSIVEL] Excluir {len(resolved)} spec(s) permanentemente?",
            default=False,
        )
        if not confirm:
            raise typer.Exit()

    # Delete files
    deleted_files: list[str] = []
    for spec_path in resolved:
        spec_name = spec_path.name
        spec_path.unlink()
        deleted_files.append(spec_name)
        print_info(f"  Excluida: {spec_name}")

    # Update memory: remove from global_specs if present
    if store.is_initialized:
        memory = store.load_memory()
        updated = False
        for spec_name in deleted_files:
            for key, filepath in list(memory.global_specs.items()):
                if spec_name in filepath:
                    del memory.global_specs[key]
                    updated = True
        if updated:
            store.save_memory(memory)

        # Record in history
        for spec_name in deleted_files:
            store.add_history_entry(
                {
                    "action": "spec_delete",
                    "file": spec_name,
                }
            )

    print_success(f"Excluidas {len(deleted_files)} spec(s) permanentemente.")


@spec_app.command("list")
def spec_list() -> None:
    """List all available spec templates."""
    from rich.table import Table

    # Import all templates to trigger registration
    import krab_cli.templates.architecture
    import krab_cli.templates.clarify
    import krab_cli.templates.constitution
    import krab_cli.templates.guardrails
    import krab_cli.templates.plan
    import krab_cli.templates.refining
    import krab_cli.templates.runbook
    import krab_cli.templates.skill
    import krab_cli.templates.task  # noqa: F401
    from krab_cli.templates import list_templates
    from krab_cli.utils.display import get_console, print_header

    print_header("Spec Templates", "Available templates")

    templates = list_templates()
    table = Table(show_header=True, border_style="cyan")
    table.add_column("Type", style="bold yellow", min_width=15)
    table.add_column("Command", style="green", min_width=30)
    table.add_column("Description")

    for t in templates:
        table.add_row(
            f"spec.{t['type']}",
            f'krab spec new {t["type"]} -n "nome"',
            t["description"],
        )

    get_console().print(table)


# ── Spec Import ──────────────────────────────────────────────────────────


@spec_app.command("import")
def spec_import(
    source: Annotated[
        str, typer.Argument(help="Git repo URL or registry alias")
    ],
    branch: Annotated[str, typer.Option("--branch", "-b", help="Branch/tag/ref")] = "",
    path: Annotated[str, typer.Option("--path", "-p", help="Subdirectory inside repo")] = "",
    all_specs: Annotated[
        bool, typer.Option("--all", "-a", help="Import all specs without prompting")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing specs")
    ] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output directory")
    ] = None,
) -> None:
    """Import specs from a remote Git repository."""
    import shutil
    import subprocess
    import tempfile

    from krab_cli.memory import SPECS_DIR, MemoryStore
    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_info,
        print_success,
        print_warning,
    )

    store = MemoryStore()
    url = source
    search_path = path

    # ── Resolve registry alias ────────────────────────────────────
    is_url = source.startswith(("http://", "https://", "git@", "ssh://"))
    is_path = source.startswith(("/", ".", "~")) or Path(source).exists()
    if not is_url and not is_path:
        if not store.is_initialized:
            print_error(
                f"'{source}' nao e uma URL Git. "
                "Para usar aliases, inicialize o projeto: `krab memory init`"
            )
            raise typer.Exit(code=1)
        registries = store.load_registries()
        if source not in registries:
            print_error(
                f"Registry '{source}' nao encontrado. "
                "Use `krab spec registry list` para ver registries disponiveis."
            )
            raise typer.Exit(code=1)
        reg = registries[source]
        url = reg.url
        if not search_path and reg.path:
            search_path = reg.path
        if not branch and reg.branch:
            branch = reg.branch

    print_header("Spec Import", url)

    # ── Clone repo ────────────────────────────────────────────────
    tmpdir = tempfile.mkdtemp(prefix="krab-import-")
    try:
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([url, tmpdir])

        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            print_error(f"Falha ao clonar repositorio: {stderr}")
            raise typer.Exit(code=1)

        print_info(f"Repositorio clonado: {url}" + (f" (branch: {branch})" if branch else ""))

        # ── Find specs ────────────────────────────────────────────
        repo_root = Path(tmpdir)
        spec_files: list[Path] = []

        if search_path:
            # User-specified path
            scan_dir = repo_root / search_path
            if scan_dir.is_dir():
                spec_files = sorted(scan_dir.glob("spec.*.md"))
        else:
            # Auto-detect: try .sdd/specs/ first, then scan entire repo
            sdd_specs = repo_root / ".sdd" / "specs"
            if sdd_specs.is_dir():
                spec_files = sorted(sdd_specs.glob("spec.*.md"))
            if not spec_files:
                spec_files = sorted(repo_root.rglob("spec.*.md"))
                # Exclude .git directory
                spec_files = [f for f in spec_files if ".git" not in f.parts]

        if not spec_files:
            print_warning(
                "Nenhuma spec encontrada"
                + (f" em '{search_path}'" if search_path else " no repositorio")
            )
            raise typer.Exit(code=0)

        # ── Display found specs ───────────────────────────────────
        from rich.table import Table

        table = Table(show_header=True, border_style="cyan", title="Specs encontradas")
        table.add_column("#", style="dim", width=4)
        table.add_column("Spec", style="bold yellow")
        table.add_column("Path", style="dim")
        table.add_column("Size", style="cyan", justify="right")

        for i, spec in enumerate(spec_files, 1):
            rel = spec.relative_to(repo_root)
            size_kb = spec.stat().st_size / 1024
            table.add_row(str(i), spec.name, str(rel.parent), f"{size_kb:.1f} KB")

        get_console().print(table)

        # ── Selection ─────────────────────────────────────────────
        if all_specs:
            selected = spec_files
        else:
            raw = typer.prompt(
                f"\nImportar quais specs? (1-{len(spec_files)}, separados por virgula, ou 'all')"
            )
            raw = raw.strip()
            if raw.lower() == "all":
                selected = spec_files
            else:
                indices: list[int] = []
                for part in raw.split(","):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part)
                        if 1 <= idx <= len(spec_files):
                            indices.append(idx - 1)
                if not indices:
                    print_warning("Nenhuma spec selecionada.")
                    raise typer.Exit(code=0)
                selected = [spec_files[i] for i in indices]

        # ── Copy specs ────────────────────────────────────────────
        dest_dir = output or Path(SPECS_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)

        imported: list[str] = []
        skipped: list[str] = []

        for spec in selected:
            dest = dest_dir / spec.name
            if dest.exists() and not force:
                print_warning(f"{spec.name} ja existe. Use --force para sobrescrever.")
                skipped.append(spec.name)
                continue
            shutil.copy2(spec, dest)
            imported.append(spec.name)

        # ── Record in history ─────────────────────────────────────
        if store.is_initialized and imported:
            for name in imported:
                store.add_history_entry(
                    {
                        "action": "spec_import",
                        "source": source,
                        "url": url,
                        "file": str(dest_dir / name),
                    }
                )

        # ── Summary ───────────────────────────────────────────────
        if imported:
            print_success(f"Importadas {len(imported)} specs de {source}")
            for name in imported:
                print_info(f"{name} -> {dest_dir / name}")
        if skipped:
            print_warning(f"{len(skipped)} specs ignoradas (ja existem)")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Spec Registry ────────────────────────────────────────────────────────


@registry_app.command("add")
def registry_add(
    name: Annotated[str, typer.Argument(help="Alias for this registry")],
    url: Annotated[str, typer.Argument(help="Git repository URL")],
    path: Annotated[str, typer.Option("--path", "-p", help="Default subdirectory")] = "",
    branch: Annotated[str, typer.Option("--branch", "-b", help="Default branch/tag")] = "",
) -> None:
    """Add a remote spec repository to the registry."""
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import print_error, print_info, print_success

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto nao inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    registries = store.load_registries()
    existed = name in registries
    registry = store.add_registry(name, url, path, branch)

    if existed:
        print_success(f"Registry '{name}' atualizado")
    else:
        print_success(f"Registry '{name}' adicionado")
    print_info(f"URL: {registry.url}")
    if registry.path:
        print_info(f"Path: {registry.path}")
    if registry.branch:
        print_info(f"Branch: {registry.branch}")


@registry_app.command("remove")
def registry_remove(
    name: Annotated[str, typer.Argument(help="Registry alias to remove")],
) -> None:
    """Remove a spec repository from the registry."""
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import print_error, print_success

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto nao inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    try:
        store.remove_registry(name)
        print_success(f"Registry '{name}' removido")
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e


@registry_app.command("list")
def registry_list() -> None:
    """List all saved spec registries."""
    from rich.table import Table

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import get_console, print_error, print_header, print_info

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto nao inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    registries = store.load_registries()

    print_header("Spec Registries", f"{len(registries)} registries")

    if not registries:
        print_info("Nenhum registry cadastrado. Use `krab spec registry add` para adicionar.")
        return

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Name", style="bold yellow", min_width=12)
    table.add_column("URL", style="green")
    table.add_column("Path", style="dim")
    table.add_column("Branch", style="dim")

    for reg in registries.values():
        table.add_row(reg.name, reg.url, reg.path or "-", reg.branch or "-")

    get_console().print(table)


# ═══════════════════════════════════════════════════════════════════════════
# MEMORY commands — Project context management
# ═══════════════════════════════════════════════════════════════════════════


@memory_app.command("init")
def memory_init(
    name: Annotated[str, typer.Option("--name", "-n")] = "",
    description: Annotated[str, typer.Option("--desc", "-d")] = "",
) -> None:
    """Initialize .sdd/ project memory."""
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import print_info, print_success

    if not name:
        name = typer.prompt("Nome do projeto")

    store = MemoryStore()
    memory = store.init(project_name=name, description=description)
    print_success(f"Projeto inicializado: {store.sdd_path}/")
    print_info(f"Nome: {memory.project_name}")
    print_info("Use `krab memory set` para configurar stack, convenções, etc.")


@memory_app.command("show")
def memory_show() -> None:
    """Show current project memory."""
    from rich.table import Table

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import get_console, print_error, print_header

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    memory = store.load_memory()
    print_header("Project Memory", memory.project_name or "unnamed")

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Campo", style="bold", min_width=20)
    table.add_column("Valor", max_width=60)

    table.add_row("project_name", memory.project_name)
    table.add_row("description", memory.description)
    table.add_row("architecture_style", memory.architecture_style)
    table.add_row("created_at", memory.created_at)
    table.add_row("updated_at", memory.updated_at)

    if memory.tech_stack:
        for k, v in memory.tech_stack.items():
            table.add_row(f"tech_stack.{k}", v)

    if memory.conventions:
        for k, v in memory.conventions.items():
            table.add_row(f"conventions.{k}", v)

    if memory.domain_terms:
        for k, v in memory.domain_terms.items():
            table.add_row(f"domain_terms.{k}", v)

    if memory.team_context:
        for k, v in memory.team_context.items():
            table.add_row(f"team_context.{k}", v)

    if memory.integrations:
        table.add_row("integrations", ", ".join(memory.integrations))

    if memory.constraints:
        table.add_row("constraints", ", ".join(memory.constraints))

    get_console().print(table)


@memory_app.command("set")
def memory_set(
    key: Annotated[
        str, typer.Argument(help="Field key (e.g. tech_stack.backend, architecture_style)")
    ],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a memory field (supports dot notation for nested dicts)."""
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import print_error, print_success

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    try:
        store.set_field(key, value)
        print_success(f"Configurado: {key} = {value}")
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e


@memory_app.command("skills")
def memory_skills() -> None:
    """List project skills."""
    from rich.table import Table

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import get_console, print_error, print_header, print_info

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    skills = store.load_skills()
    print_header("Project Skills", f"{len(skills)} skills")

    if not skills:
        print_info("Nenhuma skill registrada. Use `krab memory add-skill` para adicionar.")
        return

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Categoria", style="bold", min_width=12)
    table.add_column("Nome", style="yellow", min_width=15)
    table.add_column("Versão", width=10)
    table.add_column("Descrição", max_width=40)
    table.add_column("Tags", style="dim")

    for s in sorted(skills, key=lambda x: (x.category, x.name)):
        table.add_row(s.category, s.name, s.version, s.description, ", ".join(s.tags))

    get_console().print(table)


@memory_app.command("add-skill")
def memory_add_skill(
    name: Annotated[str, typer.Argument(help="Skill name")],
    category: Annotated[
        str,
        typer.Option(
            "--cat", "-c", help="Category: language, framework, tool, pattern, infra, service"
        ),
    ] = "tool",
    version: Annotated[str, typer.Option("--ver", "-v")] = "",
    description: Annotated[str, typer.Option("--desc", "-d")] = "",
    tags: Annotated[str, typer.Option("--tags", "-t", help="Comma-separated tags")] = "",
) -> None:
    """Add a skill to the project."""
    from krab_cli.memory import MemoryStore, ProjectSkill
    from krab_cli.utils.display import print_error, print_success

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    skill = ProjectSkill(
        name=name,
        category=category,
        version=version,
        description=description,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else [],
    )
    store.add_skill(skill)
    print_success(f"Skill adicionada: {skill.identifier}")


@memory_app.command("remove-skill")
def memory_remove_skill(
    name: Annotated[str, typer.Argument(help="Skill name to remove")],
) -> None:
    """Remove a skill from the project."""
    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import print_error, print_success

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    store.remove_skill(name)
    print_success(f"Skill removida: {name}")


@memory_app.command("history")
def memory_history(
    top: Annotated[int, typer.Option("--top")] = 20,
) -> None:
    """Show spec generation history."""
    from rich.table import Table

    from krab_cli.memory import MemoryStore
    from krab_cli.utils.display import get_console, print_error, print_header, print_info

    store = MemoryStore()
    if not store.is_initialized:
        print_error("Projeto não inicializado. Use `krab memory init` primeiro.")
        raise typer.Exit(code=1)

    history = store.load_history()
    print_header("Generation History", f"{len(history)} entries")

    if not history:
        print_info("Nenhum histórico ainda.")
        return

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Action", style="bold", width=12)
    table.add_column("Template", style="yellow", width=14)
    table.add_column("Name/File")

    for entry in history[-top:]:
        table.add_row(
            entry.get("timestamp", "")[:19],
            entry.get("action", ""),
            entry.get("template", ""),
            entry.get("name", entry.get("file", "")),
        )

    get_console().print(table)


# ═══════════════════════════════════════════════════════════════════════════
# AGENT commands — Generate instruction files for AI coding agents
# ═══════════════════════════════════════════════════════════════════════════


@agent_app.command("sync")
def agent_sync(
    target: Annotated[
        str,
        typer.Argument(help="Agent target: all, claude, copilot, codex"),
    ] = "all",
    no_commands: Annotated[
        bool,
        typer.Option("--no-commands", help="Skip slash command generation"),
    ] = False,
) -> None:
    """Generate instruction files + native slash commands for AI agents."""
    from krab_cli.agents import sync_agent, sync_all
    from krab_cli.utils.display import print_error, print_header, print_info, print_success

    print_header("Agent Sync", f"target={target}")

    try:
        if target == "all":
            results = sync_all()
            for agent_name, paths in results.items():
                for p in paths:
                    print_success(f"[{agent_name}] {p}")
            total = sum(len(v) for v in results.values())
            print_info(f"Generated {total} instruction files for {len(results)} agents")
        else:
            paths = sync_agent(target)
            for p in paths:
                print_success(f"[{target}] {p}")
            print_info(f"Generated {len(paths)} instruction file(s) for {target}")
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    # Also generate native slash commands
    if not no_commands:
        from krab_cli.workflows.commands import generate_all as gen_commands

        try:
            agent_filter = None if target == "all" else target
            cmd_results = gen_commands(root=Path.cwd(), agent=agent_filter)
            cmd_total = sum(len(v) for v in cmd_results.values())
            if cmd_total:
                for agent_name, paths in cmd_results.items():
                    for p in paths:
                        print_success(f"[{agent_name}/cmd] {p}")
                print_info(f"Generated {cmd_total} slash command files")
        except ValueError:
            pass  # Agent not supported for commands (e.g. codex) — skip silently


@agent_app.command("preview")
def agent_preview(
    target: Annotated[
        str,
        typer.Argument(help="Agent to preview: claude, copilot, codex"),
    ],
) -> None:
    """Preview generated content without writing files."""
    from rich.panel import Panel
    from rich.syntax import Syntax

    from krab_cli.agents import collect_context, get_generator
    from krab_cli.utils.display import get_console, print_error, print_header

    print_header("Agent Preview", target)

    try:
        gen = get_generator(target)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    ctx = collect_context()
    files = gen.generate(ctx, Path.cwd())

    for path, content in files:
        syntax = Syntax(content, "markdown", theme="monokai", line_numbers=False)
        get_console().print(Panel(syntax, title=str(path), border_style="cyan"))


@agent_app.command("status")
def agent_status() -> None:
    """Check which agent instruction files exist."""
    from rich.table import Table

    from krab_cli.utils.display import get_console, print_header

    print_header("Agent Status", "Instruction files")

    checks = [
        ("Claude Code", "CLAUDE.md"),
        ("Copilot", ".github/copilot-instructions.md"),
        ("Copilot (specs)", ".github/instructions/krab-specs.instructions.md"),
        ("Codex", "AGENTS.md"),
        ("Codex (skill)", ".agents/skills/krab-workflow/SKILL.md"),
        ("Krab Memory", ".sdd/memory.json"),
    ]

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Agent", style="bold", min_width=20)
    table.add_column("File", min_width=40)
    table.add_column("Status", width=10)

    for agent, filepath in checks:
        exists = Path(filepath).exists()
        status = "[green]+ exists[/green]" if exists else "[dim]- missing[/dim]"
        table.add_row(agent, filepath, status)

    get_console().print(table)
    get_console().print("\n[dim]Use `krab agent sync` to generate all files[/dim]")


@agent_app.command("diff")
def agent_diff(
    target: Annotated[
        str,
        typer.Argument(help="Agent to diff: claude, copilot, codex"),
    ],
) -> None:
    """Show what would change if sync is run (diff against existing files)."""
    import difflib

    from rich.syntax import Syntax

    from krab_cli.agents import collect_context, get_generator
    from krab_cli.utils.display import get_console, print_error, print_header, print_info

    print_header("Agent Diff", target)

    try:
        gen = get_generator(target)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    ctx = collect_context()
    files = gen.generate(ctx, Path.cwd())

    has_diff = False
    for path, new_content in files:
        if path.exists():
            old_content = path.read_text(encoding="utf-8")
            if old_content == new_content:
                print_info(f"{path}: no changes")
                continue

            diff = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"{path} (current)",
                tofile=f"{path} (new)",
            )
            diff_text = "".join(diff)
            if diff_text:
                has_diff = True
                syntax = Syntax(diff_text, "diff", theme="monokai")
                get_console().print(syntax)
        else:
            has_diff = True
            print_info(f"{path}: [green]new file[/green] ({len(new_content)} chars)")

    if not has_diff:
        print_info("No changes detected")


# ═══════════════════════════════════════════════════════════════════════════
# CACHE commands
# ═══════════════════════════════════════════════════════════════════════════


@cache_app.command("clear")
def cache_clear() -> None:
    """Remove all cached analysis results."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_info, print_success

    count = cache.clear()
    if count:
        print_success(f"Cleared {count} cached entries.")
    else:
        print_info("Cache is already empty.")


@cache_app.command("stats")
def cache_stats() -> None:
    """Show cache size and entry count."""
    from krab_cli.utils import cache
    from krab_cli.utils.display import print_header, print_metrics_table

    print_header("Cache Statistics")
    st = cache.stats()
    print_metrics_table(
        "Cache",
        {
            "Entries": st["entries"],
            "Disk Usage": st["size_human"],
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW commands — Multi-step SDD pipelines
# ═══════════════════════════════════════════════════════════════════════════


@workflow_app.command("list")
def workflow_list() -> None:
    """List all available workflows (built-in + custom)."""
    from rich.table import Table

    from krab_cli.utils.display import get_console, print_header
    from krab_cli.workflows import list_custom_workflows
    from krab_cli.workflows.builtins import list_builtins

    print_header("Workflows", "Built-in + custom")

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Name", style="bold yellow", min_width=15)
    table.add_column("Steps", justify="right", width=6)
    table.add_column("Type", width=10)
    table.add_column("Description")

    for wf in list_builtins():
        table.add_row(
            str(wf["name"]),
            str(wf["steps"]),
            "[green]built-in[/green]",
            str(wf["description"]),
        )

    for path in list_custom_workflows():
        try:
            from krab_cli.workflows import Workflow

            w = Workflow.load(path)
            table.add_row(w.name, str(len(w.steps)), "[cyan]custom[/cyan]", w.description)
        except Exception:
            table.add_row(path.stem, "?", "[red]error[/red]", f"Failed to load: {path.name}")

    get_console().print(table)


@workflow_app.command("show")
def workflow_show(
    name: Annotated[str, typer.Argument(help="Workflow name (built-in or custom)")],
) -> None:
    """Show the steps of a specific workflow."""
    from rich.table import Table

    from krab_cli.utils.display import get_console, print_error, print_header

    wf = _resolve_workflow(name)
    if not wf:
        print_error(f"Workflow not found: '{name}'")
        raise typer.Exit(code=1)

    print_header(f"Workflow: {wf.name}", wf.description)

    table = Table(show_header=True, border_style="cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Step", style="bold yellow", min_width=18)
    table.add_column("Type", width=8)
    table.add_column("Command / Prompt", max_width=55)
    table.add_column("On Fail", width=10)

    for i, step in enumerate(wf.steps, 1):
        detail = step.command or step.prompt or step.condition
        if len(detail) > 55:
            detail = detail[:52] + "..."

        fail_style = "[green]continue[/green]" if step.on_failure.value == "continue" else "stop"

        table.add_row(str(i), step.name, step.type.value, detail, fail_style)

    get_console().print(table)
    get_console().print(f"\n[dim]Default agent: {wf.default_agent}[/dim]")


@workflow_app.command("run")
def workflow_run(
    name: Annotated[str, typer.Argument(help="Workflow name")],
    spec: Annotated[str, typer.Option("--spec", "-s", help="Spec file path")] = "",
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent: claude, codex, copilot")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without executing")] = False,
) -> None:
    """Execute a workflow pipeline."""

    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_success,
    )
    from krab_cli.workflows import StepResult as WfStepResult
    from krab_cli.workflows import WorkflowRunner, WorkflowStep

    wf = _resolve_workflow(name)
    if not wf:
        print_error(f"Workflow not found: '{name}'")
        raise typer.Exit(code=1)

    mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]"
    print_header(
        f"Workflow: {wf.name}",
        f"{mode}  spec={spec or '(none)'}  agent={agent or wf.default_agent}",
    )

    step_results: list[tuple[WorkflowStep, WfStepResult]] = []

    def on_step(step: WorkflowStep, result: WfStepResult) -> None:
        step_results.append((step, result))
        icon = "[green]OK[/green]" if result.success else "[red]FAIL[/red]"
        if result.skipped:
            icon = "[yellow]SKIP[/yellow]"
        get_console().print(f"  {icon}  {step.name}: {result.output or result.error or 'done'}")

    runner = WorkflowRunner(
        spec=spec,
        agent=agent,
        dry_run=dry_run,
        on_step=on_step,
    )

    result = runner.run(wf)

    # Summary
    get_console().print()
    if result.success:
        print_success(
            f"Workflow '{wf.name}' completed: "
            f"{result.completed_count} passed, {result.skipped_count} skipped"
        )
    else:
        print_error(
            f"Workflow '{wf.name}' failed: "
            f"{result.completed_count} passed, {result.failed_count} failed, "
            f"{result.skipped_count} skipped"
        )
        raise typer.Exit(code=1)


@workflow_app.command("new")
def workflow_new(
    name: Annotated[str, typer.Argument(help="Workflow name")],
    desc: Annotated[str, typer.Option("--desc", "-d", help="Description")] = "",
) -> None:
    """Create a new custom workflow YAML template."""
    from krab_cli.utils.display import print_info, print_success
    from krab_cli.workflows import OnFailure, StepType, Workflow, WorkflowStep, get_workflows_dir

    wf_dir = get_workflows_dir()
    wf_dir.mkdir(parents=True, exist_ok=True)

    template = Workflow(
        name=name,
        description=desc or f"Custom workflow: {name}",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="check-spec",
                type=StepType.GATE,
                condition="file_exists:{spec}",
            ),
            WorkflowStep(
                name="analyze",
                type=StepType.KRAB,
                command="analyze risk {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="implement",
                type=StepType.AGENT,
                agent="{agent}",
                prompt="Implement the changes described in the specification.",
            ),
        ],
    )

    out_path = wf_dir / f"{name}.yaml"
    template.save(out_path)
    print_success(f"Created workflow template: {out_path}")
    print_info("Edit the YAML file to customize the workflow steps.")


@workflow_app.command("export")
def workflow_export(
    name: Annotated[str, typer.Argument(help="Built-in workflow name to export")],
) -> None:
    """Export a built-in workflow as YAML to stdout."""
    from krab_cli.utils.display import get_console, print_error
    from krab_cli.workflows.builtins import get_builtin

    try:
        wf = get_builtin(name)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    get_console().print(wf.to_yaml())


@workflow_app.command("agents-check")
def workflow_agents_check() -> None:
    """Check which AI agent CLIs are installed and available."""
    from rich.table import Table

    from krab_cli.utils.display import get_console, print_header
    from krab_cli.workflows.executor import list_agents

    print_header("Agent Availability", "CLI tools in PATH")

    table = Table(show_header=True, border_style="cyan")
    table.add_column("Agent", style="bold", min_width=18)
    table.add_column("Command", width=12)
    table.add_column("Status", width=12)
    table.add_column("Description")

    for agent in list_agents():
        status = "[green]installed[/green]" if agent["available"] else "[red]not found[/red]"
        table.add_row(
            str(agent["name"]),
            str(agent["command"]),
            status,
            str(agent["description"]),
        )

    get_console().print(table)


@workflow_app.command("commands")
def workflow_commands(
    agent: Annotated[
        str,
        typer.Option("--agent", "-a", help="Agent: claude, copilot (default: all)"),
    ] = "",
    workflow: Annotated[
        str,
        typer.Option("--workflow", "-w", help="Specific workflow name (default: all)"),
    ] = "",
    do_preview: Annotated[
        bool,
        typer.Option("--preview", help="Preview without writing files"),
    ] = False,
    do_clean: Annotated[
        bool,
        typer.Option("--clean", help="Remove all generated command files"),
    ] = False,
) -> None:
    """Generate native slash commands for AI agents from krab workflows."""
    from krab_cli.utils.display import (
        get_console,
        print_error,
        print_header,
        print_info,
        print_success,
    )
    from krab_cli.workflows.commands import clean, generate_all, preview

    if do_clean:
        print_header("Workflow Commands", "Cleaning generated files")
        removed = clean(root=Path.cwd())
        if removed:
            for p in removed:
                print_info(f"Removed: {p}")
            print_success(f"Cleaned {len(removed)} file(s)")
        else:
            print_info("No generated command files found")
        return

    agent_filter = agent or None
    wf_filter = workflow or None

    if do_preview:
        from rich.panel import Panel
        from rich.syntax import Syntax

        print_header("Workflow Commands", "Preview (no files written)")
        try:
            results = preview(root=Path.cwd(), agent=agent_filter, workflow=wf_filter)
        except ValueError as e:
            print_error(str(e))
            raise typer.Exit(code=1) from e

        for agent_name, files in results.items():
            for path, content in files:
                syntax = Syntax(content, "markdown", theme="monokai", line_numbers=False)
                get_console().print(
                    Panel(syntax, title=f"[{agent_name}] {path}", border_style="cyan")
                )
        total = sum(len(v) for v in results.values())
        print_info(f"Would generate {total} file(s)")
        return

    print_header("Workflow Commands", "Generating native slash commands")
    try:
        results = generate_all(root=Path.cwd(), agent=agent_filter, workflow=wf_filter)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    for agent_name, paths in results.items():
        for p in paths:
            print_success(f"[{agent_name}] {p}")

    total = sum(len(v) for v in results.values())
    print_info(f"Generated {total} slash command file(s)")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_workflow(name: str):
    """Resolve a workflow by name: try built-in first, then custom YAML."""
    from krab_cli.workflows import Workflow, list_custom_workflows
    from krab_cli.workflows.builtins import get_builtin

    # Try built-in
    try:
        return get_builtin(name)
    except ValueError:
        pass

    # Try custom
    for path in list_custom_workflows():
        if path.stem == name:
            try:
                return Workflow.load(path)
            except Exception:
                return None

    return None


def _check_file(path: Path) -> None:
    """Validate that a file exists and is readable."""
    if not path.exists():
        from krab_cli.utils.display import print_error

        print_error(f"File not found: {path}")
        raise typer.Exit(code=1)
    if not path.is_file():
        from krab_cli.utils.display import print_error

        print_error(f"Not a file: {path}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
