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
memory_app = typer.Typer(help="Manage project memory (.sdd/)", no_args_is_help=True)
agent_app = typer.Typer(
    help="Generate instruction files for AI agents (Claude Code, Copilot, Codex)",
    no_args_is_help=True,
)
cache_app = typer.Typer(help="Manage analysis result cache", no_args_is_help=True)

app.add_typer(optimize_app, name="optimize")
app.add_typer(convert_app, name="convert")
app.add_typer(analyze_app, name="analyze")
app.add_typer(search_app, name="search")
app.add_typer(diff_app, name="diff")
app.add_typer(spec_app, name="spec")
app.add_typer(memory_app, name="memory")
app.add_typer(agent_app, name="agent")
app.add_typer(cache_app, name="cache")


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

    cache.put(text, "analyze_readability", {
        "metrics": metrics,
        "recommendation": report.recommendation,
    })


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
        str, typer.Option("-a", "--analysis", help="Analysis type: tokens, quality, entropy, readability")
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

        table = Table(title=f"Token Analysis ({len(files)} files)", show_header=True, border_style="cyan")
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
            table.add_row(f.name, str(s["characters"]), str(s["words"]),
                          str(s["tokens"]), f"{s['chars_per_token']:.1f}", f"${c['total_cost_usd']:.4f}")

        get_console().print(table)
        print_info(f"Total tokens: {total_tokens:,}")

    elif analysis == "quality":
        from krab_cli.core.similarity import context_quality_score

        table = Table(title=f"Quality Analysis ({len(files)} files)", show_header=True, border_style="cyan")
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
            table.add_row(f.name, str(q["word_count"]), str(q["estimated_tokens"]),
                          f"{q['utilization_pct']:.1f}", f"{q['information_density']:.3f}",
                          f"{q['redundancy_ratio']:.3f}", q["density_grade"])

        get_console().print(table)

    elif analysis == "entropy":
        from krab_cli.core.entropy import full_entropy_analysis

        table = Table(title=f"Entropy Analysis ({len(files)} files)", show_header=True, border_style="cyan")
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
            table.add_row(f.name, f"{m['Shannon Entropy (bits)']:.2f}", m["Entropy Grade"],
                          f"{m['Perplexity']:.1f}", f"{m['Markov Predictability']:.3f}",
                          f"{m['Vocabulary Richness']:.3f}")

        get_console().print(table)

    elif analysis == "readability":
        from krab_cli.core.readability import full_readability_analysis

        table = Table(title=f"Readability Analysis ({len(files)} files)", show_header=True, border_style="cyan")
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
                cache.put(text, "analyze_readability", {"metrics": m, "recommendation": report.recommendation})
            table.add_row(f.name, f"{m['Flesch-Kincaid Grade']:.1f}", f"{m['Flesch Reading Ease']:.1f}",
                          f"{m['Gunning Fog Index']:.1f}", f"{m['ARI Score']:.1f}", m["Overall Grade"])

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
    import krab_cli.templates.plan
    import krab_cli.templates.refining
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

    out_file = output or Path(f"spec.refining.{file.stem}.md")
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


@spec_app.command("list")
def spec_list() -> None:
    """List all available spec templates."""
    from rich.table import Table

    # Import all templates to trigger registration
    import krab_cli.templates.architecture
    import krab_cli.templates.plan
    import krab_cli.templates.refining
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
) -> None:
    """Generate instruction files for AI agents from SDD memory + specs."""
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
            print_info(f"Generated {total} files for {len(results)} agents")
        else:
            paths = sync_agent(target)
            for p in paths:
                print_success(f"[{target}] {p}")
            print_info(f"Generated {len(paths)} file(s) for {target}")
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e


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
    print_metrics_table("Cache", {
        "Entries": st["entries"],
        "Disk Usage": st["size_human"],
    })


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


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
