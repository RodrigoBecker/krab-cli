"""Rich console helpers for Krab CLI output.

Provides formatted tables, panels, and progress indicators.
Rich is lazy-loaded on first use to avoid ~90ms import overhead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

KRAB_LOGO = """
██╗  ██╗██████╗  █████╗ ██████╗      ██████╗██╗     ██╗
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗    ██╔════╝██║     ██║
█████╔╝ ██████╔╝███████║██████╔╝    ██║     ██║     ██║
██╔═██╗ ██╔══██╗██╔══██║██╔══██╗    ██║     ██║     ██║
██║  ██╗██║  ██║██║  ██║██████╔╝    ╚██████╗███████╗██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝      ╚═════╝╚══════╝╚═╝
"""

_KRAB_THEME_DICT = {
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "heading": "bold magenta",
    "metric": "bold cyan",
    "dim": "dim white",
}

_console: Console | None = None


def get_console() -> Console:
    """Return the shared themed Console instance (created on first call)."""
    global _console
    if _console is None:
        from rich.console import Console as _RichConsole
        from rich.theme import Theme

        _console = _RichConsole(theme=Theme(_KRAB_THEME_DICT))
    return _console


def __getattr__(name: str) -> Any:
    """Lazy access to module-level 'console' for backward compatibility."""
    if name == "console":
        return get_console()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def print_logo(version: str = "") -> None:
    """Print the Krab CLI ASCII logo."""
    from rich.panel import Panel

    logo = KRAB_LOGO.rstrip()
    if version:
        logo += f"\n        {version}"
    get_console().print(Panel(logo, border_style="bold red", padding=(0, 4)))


def print_header(title: str, subtitle: str = "") -> None:
    """Print a styled header panel."""
    from rich.panel import Panel

    content = f"[heading]{title}[/heading]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    get_console().print(Panel(content, border_style="cyan", padding=(1, 2)))


def print_success(msg: str) -> None:
    get_console().print(f"[success]+[/success] {msg}")


def print_warning(msg: str) -> None:
    get_console().print(f"[warning]![/warning] {msg}")


def print_error(msg: str) -> None:
    get_console().print(f"[error]x[/error] {msg}")


def print_info(msg: str) -> None:
    get_console().print(f"[info]i[/info] {msg}")


def print_metrics_table(title: str, metrics: dict[str, Any]) -> None:
    """Print a key-value metrics table."""
    from rich.table import Table

    table = Table(title=title, show_header=True, border_style="cyan")
    table.add_column("Metric", style="bold", min_width=25)
    table.add_column("Value", style="metric", justify="right")

    for key, value in metrics.items():
        display_key = key.replace("_", " ").title()
        if isinstance(value, float):
            display_value = f"{value:.4f}" if value < 1 else f"{value:.2f}"
        else:
            display_value = str(value)
        table.add_row(display_key, display_value)

    get_console().print(table)


def print_comparison_table(
    title: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    """Print a before/after comparison table."""
    from rich.table import Table

    table = Table(title=title, show_header=True, border_style="cyan")
    table.add_column("Metric", style="bold", min_width=25)
    table.add_column("Before", style="yellow", justify="right")
    table.add_column("After", style="green", justify="right")
    table.add_column("Delta", justify="right")

    all_keys = list(dict.fromkeys(list(before.keys()) + list(after.keys())))
    for key in all_keys:
        display_key = key.replace("_", " ").title()
        val_before = before.get(key, "—")
        val_after = after.get(key, "—")

        delta_str = ""
        if isinstance(val_before, (int, float)) and isinstance(val_after, (int, float)):
            delta = val_after - val_before
            if delta > 0:
                delta_str = f"[red]+{delta:.2f}[/red]"
            elif delta < 0:
                delta_str = f"[green]{delta:.2f}[/green]"
            else:
                delta_str = "[dim]0[/dim]"

        table.add_row(
            display_key,
            _format_value(val_before),
            _format_value(val_after),
            delta_str,
        )

    get_console().print(table)


def print_aliases_table(aliases: dict[str, str]) -> None:
    """Print the alias dictionary as a formatted table."""
    from rich.table import Table

    if not aliases:
        print_info("No aliases generated.")
        return

    table = Table(title="Alias Dictionary", show_header=True, border_style="cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Alias", style="bold green", min_width=8)
    table.add_column("Original Term", style="yellow")
    table.add_column("Savings/use", justify="right", style="metric")

    for i, (term, alias) in enumerate(sorted(aliases.items(), key=lambda x: x[1]), 1):
        savings = len(term) - len(alias)
        table.add_row(str(i), alias, term, f"{savings} chars")

    get_console().print(table)


def print_code(code: str, language: str = "markdown") -> None:
    """Print syntax-highlighted code."""
    from rich.syntax import Syntax

    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    get_console().print(syntax)


def print_duplicates(matches: list) -> None:
    """Print duplicate matches in a table."""
    from rich.table import Table

    if not matches:
        print_success("No duplicates found.")
        return

    table = Table(title="Duplicate Sections Found", show_header=True, border_style="yellow")
    table.add_column("#", style="dim", width=4)
    table.add_column("Source", style="yellow", max_width=35, overflow="ellipsis")
    table.add_column("Target", style="yellow", max_width=35, overflow="ellipsis")
    table.add_column("Score", style="metric", justify="right")
    table.add_column("Verdict", justify="center")

    for i, match in enumerate(matches, 1):
        if match.is_duplicate:
            verdict = "[red]DUPLICATE[/red]"
        elif match.is_near_duplicate:
            verdict = "[yellow]NEAR-DUP[/yellow]"
        else:
            verdict = "[green]SIMILAR[/green]"

        table.add_row(str(i), match.source, match.target, f"{match.score:.1f}%", verdict)

    get_console().print(table)


def _format_value(val: Any) -> str:
    """Format a value for display."""
    if isinstance(val, float):
        return f"{val:.4f}" if val < 1 else f"{val:.2f}"
    return str(val)
