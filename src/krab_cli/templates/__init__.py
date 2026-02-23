"""SDD Template Engine — Base class and registry for spec templates.

Each template type (task, architecture, plan, skill, refining) has its own
renderer that combines project memory + user input to produce a well-structured
Markdown spec ready for AI agent consumption.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from krab_cli.memory import MemoryStore, ProjectMemory  # noqa: TC001


@dataclass
class TemplateContext:
    """Input context for template rendering."""

    name: str
    description: str = ""
    memory: ProjectMemory | None = None
    skills_block: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Generate a filename-safe slug."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")

    @property
    def timestamp(self) -> str:
        return datetime.now(tz=UTC).strftime("%Y-%m-%d")


class SpecTemplate(ABC):
    """Base class for all spec templates."""

    template_type: str = ""
    file_suffix: str = ".md"
    description: str = ""

    @abstractmethod
    def render(self, ctx: TemplateContext) -> str:
        """Render the template to Markdown string."""

    def suggested_filename(self, ctx: TemplateContext) -> str:
        """Suggest a filename for the generated spec."""
        return f"spec.{self.template_type}.{ctx.slug}{self.file_suffix}"

    def _header(self, ctx: TemplateContext) -> str:
        """Generate standard YAML front-matter header."""
        lines = [
            "---",
            f"title: {ctx.name}",
            f"type: spec.{self.template_type}",
            f"date: {ctx.timestamp}",
        ]
        if ctx.memory and ctx.memory.project_name:
            lines.append(f"project: {ctx.memory.project_name}")
        lines.append("status: draft")
        lines.append("---")
        return "\n".join(lines)

    def _project_context_section(self, ctx: TemplateContext) -> str:
        """Generate project context section from memory."""
        if not ctx.memory:
            return ""

        block = ctx.memory.to_context_block()
        if not block:
            return ""

        lines = [
            "## Contexto do Projeto",
            "",
            "```",
            block,
        ]
        if ctx.skills_block:
            lines.append(f"Skills:\n{ctx.skills_block}")
        lines.extend(["```", ""])
        return "\n".join(lines)


# ─── Template Registry ────────────────────────────────────────────────────

_REGISTRY: dict[str, type[SpecTemplate]] = {}


def register_template(cls: type[SpecTemplate]) -> type[SpecTemplate]:
    """Decorator to register a template class."""
    _REGISTRY[cls.template_type] = cls
    return cls


def get_template(template_type: str) -> SpecTemplate:
    """Get a template instance by type name."""
    cls = _REGISTRY.get(template_type)
    if not cls:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(f"Unknown template type: '{template_type}'. Available: {available}")
    return cls()


def list_templates() -> list[dict[str, str]]:
    """List all registered templates."""
    return [{"type": t, "description": cls.description} for t, cls in sorted(_REGISTRY.items())]


def build_context(
    name: str,
    description: str = "",
    store: MemoryStore | None = None,
    extra: dict | None = None,
) -> TemplateContext:
    """Build a TemplateContext from a MemoryStore."""
    memory = None
    skills_block = ""

    if store and store.is_initialized:
        memory = store.load_memory()
        skills_block = store.skills_context_block()

    return TemplateContext(
        name=name,
        description=description,
        memory=memory,
        skills_block=skills_block,
        extra=extra or {},
    )
