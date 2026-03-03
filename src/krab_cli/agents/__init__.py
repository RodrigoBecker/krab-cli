"""SDD Agents — Generate instruction files for AI coding agents.

Reads project memory (.sdd/) and spec files to generate optimized
instruction files for each agent's specific format:

- Claude Code  → CLAUDE.md (concise, progressive disclosure)
- Copilot      → .github/copilot-instructions.md + .github/instructions/*.instructions.md
- Codex        → AGENTS.md (hierarchical, with optional skills)

Design principles (from each agent's best practices):
- Keep instructions concise and universally applicable
- Use progressive disclosure (point to files, don't inline everything)
- Focus on what's unique to the project, not general knowledge
- Include commands, architecture, and conventions
"""

from __future__ import annotations

import glob
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from krab_cli.memory import SPECS_DIR, MemoryStore


@dataclass
class AgentContext:
    """Collected project context for agent file generation."""

    project_name: str = ""
    description: str = ""
    architecture_style: str = ""
    tech_stack: dict[str, str] = field(default_factory=dict)
    conventions: dict[str, str] = field(default_factory=dict)
    domain_terms: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    skills: list[dict[str, str]] = field(default_factory=list)
    spec_files: list[str] = field(default_factory=list)
    commands: dict[str, str] = field(default_factory=dict)
    directory_structure: str = ""


def collect_context(root: Path | None = None) -> AgentContext:
    """Collect all project context from .sdd/ and filesystem."""
    root = root or Path.cwd()
    store = MemoryStore(root=root)
    ctx = AgentContext()

    if store.is_initialized:
        memory = store.load_memory()
        ctx.project_name = memory.project_name
        ctx.description = memory.description
        ctx.architecture_style = memory.architecture_style
        ctx.tech_stack = dict(memory.tech_stack)
        ctx.conventions = dict(memory.conventions)
        ctx.domain_terms = dict(memory.domain_terms)
        ctx.constraints = list(memory.constraints)
        ctx.integrations = list(memory.integrations)

        for skill in store.load_skills():
            ctx.skills.append(
                {
                    "name": skill.name,
                    "category": skill.category,
                    "version": skill.version,
                    "description": skill.description,
                }
            )

    # Discover spec files
    for pattern in [f"{SPECS_DIR}/spec.*.md", "spec.*.md", "specs/*.md", "docs/specs/*.md"]:
        for f in glob.glob(str(root / pattern)):
            ctx.spec_files.append(str(Path(f).relative_to(root)))

    # Detect common commands
    ctx.commands = _detect_commands(root)

    # Build directory structure hint
    ctx.directory_structure = _build_structure_hint(root)

    return ctx


def _detect_commands(root: Path) -> dict[str, str]:
    """Auto-detect common development commands from project files."""
    commands: dict[str, str] = {}

    # Python / uv
    if (root / "pyproject.toml").exists():
        commands["test"] = "uv run pytest"
        commands["lint"] = "uv run ruff check src/ tests/"
        commands["format"] = "uv run ruff format src/ tests/"
        if (root / "Makefile").exists():
            commands["build"] = "make build"

    # Node.js
    if (root / "package.json").exists():
        import json

        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            for key in ["test", "lint", "build", "dev", "start", "format"]:
                if key in scripts:
                    commands[key] = f"npm run {key}"
        except Exception:
            pass

    # Docker
    if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
        commands["docker-up"] = "docker compose up -d"
        commands["docker-down"] = "docker compose down"

    # Krab CLI itself
    if any((root / f).exists() for f in ["spec.task.*.md", "spec.architecture.*.md"]):
        commands["krab-optimize"] = "krab optimize run <spec>.md"
        commands["krab-analyze"] = "krab analyze risk <spec>.md"

    return commands


def _build_structure_hint(root: Path) -> str:
    """Build a concise directory structure hint."""
    interesting_dirs: list[str] = []
    for d in sorted(root.iterdir()):
        if (
            d.is_dir()
            and not d.name.startswith(".")
            and d.name
            not in {
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                ".git",
                "dist",
                "build",
                ".sdd",
            }
        ):
            interesting_dirs.append(d.name + "/")
    return "\n".join(f"  {d}" for d in interesting_dirs[:15])


# ─── Base Generator ──────────────────────────────────────────────────────


class AgentGenerator(ABC):
    """Base class for agent instruction file generators."""

    agent_name: str = ""
    output_files: ClassVar[list[str]] = []

    @abstractmethod
    def generate(self, ctx: AgentContext, root: Path) -> list[tuple[Path, str]]:
        """Generate instruction file(s). Returns list of (path, content) tuples."""

    def write(self, ctx: AgentContext, root: Path) -> list[Path]:
        """Generate and write files to disk."""
        files = self.generate(ctx, root)
        written: list[Path] = []
        for path, content in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)
        return written


# ─── Claude Code Generator ───────────────────────────────────────────────


class ClaudeCodeGenerator(AgentGenerator):
    """Generate CLAUDE.md for Claude Code.

    Best practices (from Anthropic + community):
    - Keep concise, <150 instructions total
    - Use progressive disclosure (point to files)
    - Don't duplicate what linters do
    - Modular sections with clear headings
    - Commands, architecture, conventions, gotchas
    """

    agent_name = "Claude Code"
    output_files: ClassVar[list[str]] = ["CLAUDE.md"]

    def generate(self, ctx: AgentContext, root: Path) -> list[tuple[Path, str]]:
        sections: list[str] = []

        # Project identity
        if ctx.project_name:
            title = f"# {ctx.project_name}"
            if ctx.description:
                title += f"\n\n{ctx.description}"
            sections.append(title)

        # Architecture
        if ctx.architecture_style or ctx.tech_stack:
            arch_lines = ["## Architecture"]
            if ctx.architecture_style:
                arch_lines.append(f"\nStyle: **{ctx.architecture_style}**")
            if ctx.tech_stack:
                for k, v in ctx.tech_stack.items():
                    arch_lines.append(f"- {k}: {v}")
            sections.append("\n".join(arch_lines))

        # Directory structure
        if ctx.directory_structure:
            sections.append(f"## Structure\n\n```\n{ctx.directory_structure}\n```")

        # Commands
        if ctx.commands:
            cmd_lines = ["## Commands"]
            for name, cmd in ctx.commands.items():
                cmd_lines.append(f"- `{cmd}` — {name}")
            sections.append("\n".join(cmd_lines))

        # Conventions (concise)
        if ctx.conventions:
            conv_lines = ["## Conventions"]
            for k, v in ctx.conventions.items():
                conv_lines.append(f"- **{k}**: {v}")
            sections.append("\n".join(conv_lines))

        # Domain terms
        if ctx.domain_terms:
            terms = ", ".join(f"{k} ({v})" for k, v in ctx.domain_terms.items())
            sections.append(f"## Domain Terms\n\n{terms}")

        # Specs (progressive disclosure — point to files, don't inline)
        if ctx.spec_files:
            spec_lines = ["## Specs\n\nRead these for detailed requirements:"]
            for f in ctx.spec_files:
                spec_lines.append(f"- `{f}`")
            sections.append("\n".join(spec_lines))

        # Constraints / gotchas
        if ctx.constraints:
            gotcha_lines = ["## Important"]
            for c in ctx.constraints:
                gotcha_lines.append(f"- {c}")
            sections.append("\n".join(gotcha_lines))

        # Integrations
        if ctx.integrations:
            int_lines = ["## Integrations"]
            for i in ctx.integrations:
                int_lines.append(f"- {i}")
            sections.append("\n".join(int_lines))

        # SDD workflow hint
        sections.append(
            "## SDD Workflow\n\n"
            "This project uses Spec-Driven Development. Before implementing:\n"
            "1. Read the relevant `.sdd/specs/spec.task.*.md` for Gherkin scenarios\n"
            "2. Check `.sdd/specs/spec.architecture.*.md` for design constraints\n"
            "3. Run `krab analyze risk <spec>` to check hallucination risk\n"
            "4. After changes, run `krab optimize run <spec>` to keep specs lean"
        )

        content = "\n\n".join(sections) + "\n"
        return [(root / "CLAUDE.md", content)]


# ─── GitHub Copilot Generator ────────────────────────────────────────────


class CopilotGenerator(AgentGenerator):
    """Generate .github/copilot-instructions.md for GitHub Copilot.

    Best practices (from GitHub docs):
    - Short, self-contained statements
    - Add context that supplements chat questions
    - Don't reference external resources
    - Don't request specific response styles
    - Focus on coding standards and project specifics
    """

    agent_name = "GitHub Copilot"
    output_files: ClassVar[list[str]] = [".github/copilot-instructions.md"]

    def generate(self, ctx: AgentContext, root: Path) -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []

        # Main instructions file
        instructions: list[str] = []

        if ctx.project_name:
            instructions.append(f"This is the {ctx.project_name} project.")
        if ctx.description:
            instructions.append(ctx.description)

        # Architecture context
        if ctx.architecture_style:
            instructions.append(f"This project uses {ctx.architecture_style} architecture.")

        # Tech stack as context
        if ctx.tech_stack:
            stack_parts = [f"{k} ({v})" for k, v in ctx.tech_stack.items()]
            instructions.append(f"Tech stack: {', '.join(stack_parts)}.")

        # Conventions as short statements
        for k, v in ctx.conventions.items():
            instructions.append(f"For {k}: {v}.")

        # Domain terms
        if ctx.domain_terms:
            for term, definition in ctx.domain_terms.items():
                instructions.append(f'The term "{term}" means {definition}.')

        # Constraints
        for c in ctx.constraints:
            instructions.append(c)

        # Commands as context
        if ctx.commands:
            cmd_list = [f"`{cmd}` for {name}" for name, cmd in ctx.commands.items()]
            instructions.append(f"Development commands: {', '.join(cmd_list)}.")

        # SDD context
        if ctx.spec_files:
            instructions.append(
                "This project uses Spec-Driven Development (SDD). "
                "Feature specs use Gherkin format (Given/When/Then). "
                "Check .sdd/specs/spec.task.*.md files for detailed requirements before implementing features."
            )

        # Skills as context
        if ctx.skills:
            by_cat: dict[str, list[str]] = {}
            for s in ctx.skills:
                by_cat.setdefault(s["category"], []).append(s["name"])
            for cat, names in by_cat.items():
                instructions.append(f"Project {cat} skills: {', '.join(names)}.")

        main_content = "\n\n".join(instructions) + "\n"
        files.append((root / ".github" / "copilot-instructions.md", main_content))

        # Path-specific instructions for spec files
        if ctx.spec_files:
            spec_instructions = (
                "---\n"
                'applyTo: ".sdd/specs/spec.*.md"\n'
                "---\n\n"
                "These are SDD specification files using Spec-Driven Development methodology.\n\n"
                "When editing specs:\n"
                "- Maintain Gherkin format (Given/When/Then) for scenarios\n"
                "- Keep language precise — avoid vague terms like 'etc', 'TBD', 'various'\n"
                "- Include measurable acceptance criteria\n"
                "- Reference related specs by filename\n"
                "- Use Mermaid diagrams for architecture specs\n"
            )
            files.append(
                (root / ".github" / "instructions" / "krab-specs.instructions.md", spec_instructions)
            )

        return files


# ─── OpenAI Codex Generator ──────────────────────────────────────────────


class CodexGenerator(AgentGenerator):
    """Generate AGENTS.md for OpenAI Codex.

    Best practices (from OpenAI docs):
    - Standard Markdown, any headings
    - Include commands, coding conventions, project structure
    - Can include test instructions (Codex runs them)
    - Hierarchical: global → repo root → subdirs
    - Also supports .agents/skills/*/SKILL.md
    """

    agent_name = "OpenAI Codex"
    output_files: ClassVar[list[str]] = ["AGENTS.md"]

    def generate(self, ctx: AgentContext, root: Path) -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []
        sections: list[str] = []

        # Project overview
        header = "# Project Instructions"
        if ctx.project_name:
            header = f"# {ctx.project_name}"
        sections.append(header)

        if ctx.description:
            sections.append(ctx.description)

        # Codebase orientation
        if ctx.architecture_style or ctx.tech_stack:
            orient_lines = ["## Codebase Overview"]
            if ctx.architecture_style:
                orient_lines.append(f"\nArchitecture: {ctx.architecture_style}")
            if ctx.tech_stack:
                for k, v in ctx.tech_stack.items():
                    orient_lines.append(f"- **{k}**: {v}")
            sections.append("\n".join(orient_lines))

        if ctx.directory_structure:
            sections.append(f"## Directory Structure\n\n```\n{ctx.directory_structure}\n```")

        # Commands (Codex actually runs these)
        if ctx.commands:
            cmd_lines = ["## Commands\n\nRun these commands as needed:"]
            for name, cmd in ctx.commands.items():
                cmd_lines.append(f"- **{name}**: `{cmd}`")
            sections.append("\n".join(cmd_lines))

        # Coding conventions
        if ctx.conventions:
            conv_lines = ["## Coding Conventions"]
            for k, v in ctx.conventions.items():
                conv_lines.append(f"- **{k}**: {v}")
            sections.append("\n".join(conv_lines))

        # Domain glossary
        if ctx.domain_terms:
            terms_lines = ["## Domain Glossary"]
            for term, definition in ctx.domain_terms.items():
                terms_lines.append(f"- **{term}**: {definition}")
            sections.append("\n".join(terms_lines))

        # Constraints
        if ctx.constraints:
            const_lines = ["## Constraints and Rules"]
            for c in ctx.constraints:
                const_lines.append(f"- {c}")
            sections.append("\n".join(const_lines))

        # Integrations
        if ctx.integrations:
            int_lines = ["## External Integrations"]
            for i in ctx.integrations:
                int_lines.append(f"- {i}")
            sections.append("\n".join(int_lines))

        # Spec files as references
        if ctx.spec_files:
            spec_lines = [
                "## Specification Files (SDD)\n",
                "This project uses Spec-Driven Development. Read spec files before implementing:",
            ]
            for f in ctx.spec_files:
                spec_lines.append(f"- `{f}`")
            spec_lines.append(
                "\nSpec files use Gherkin scenarios (Given/When/Then) for acceptance criteria."
            )
            sections.append("\n".join(spec_lines))

        # Testing instructions (Codex runs tests)
        test_cmd = ctx.commands.get("test")
        lint_cmd = ctx.commands.get("lint")
        if test_cmd or lint_cmd:
            test_lines = ["## Testing\n\nAlways run tests after making changes:"]
            if test_cmd:
                test_lines.append(f"- Run `{test_cmd}` to verify all tests pass")
            if lint_cmd:
                test_lines.append(f"- Run `{lint_cmd}` to check for lint errors")
            sections.append("\n".join(test_lines))

        # PR conventions
        sections.append(
            "## Pull Request Guidelines\n\n"
            "- Use conventional commit format: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`\n"
            "- Reference spec files in PR description when implementing features\n"
            "- Ensure all tests pass before submitting"
        )

        content = "\n\n".join(sections) + "\n"
        files.append((root / "AGENTS.md", content))

        # Generate Codex skills from SDD specs
        if ctx.spec_files:
            skill_content = (
                "---\n"
                "name: krab-workflow\n"
                "description: Use SDD specs before implementing features. "
                "Read .sdd/specs/spec.task.*.md for Gherkin scenarios, "
                ".sdd/specs/spec.architecture.*.md for design decisions.\n"
                "---\n\n"
                "# SDD Workflow Skill\n\n"
                "Before implementing any feature:\n\n"
                "1. Find the relevant spec file: `ls .sdd/specs/spec.*.md`\n"
                "2. Read the spec thoroughly\n"
                "3. Follow Gherkin scenarios as test cases\n"
                "4. After implementation, run: `krab analyze risk <spec>`\n"
                "5. Optimize the spec: `krab optimize run <spec>`\n"
            )
            files.append((root / ".agents" / "skills" / "krab-workflow" / "SKILL.md", skill_content))

        return files


# ─── Registry ────────────────────────────────────────────────────────────

GENERATORS: dict[str, type[AgentGenerator]] = {
    "claude": ClaudeCodeGenerator,
    "copilot": CopilotGenerator,
    "codex": CodexGenerator,
}


def get_generator(name: str) -> AgentGenerator:
    """Get a generator by agent name."""
    cls = GENERATORS.get(name.lower())
    if not cls:
        available = ", ".join(sorted(GENERATORS.keys()))
        raise ValueError(f"Unknown agent: '{name}'. Available: {available}")
    return cls()


def sync_all(root: Path | None = None) -> dict[str, list[Path]]:
    """Generate instruction files for all agents."""
    root = root or Path.cwd()
    ctx = collect_context(root)
    results: dict[str, list[Path]] = {}
    for name, cls in GENERATORS.items():
        gen = cls()
        written = gen.write(ctx, root)
        results[name] = written
    return results


def sync_agent(agent_name: str, root: Path | None = None) -> list[Path]:
    """Generate instruction files for a specific agent."""
    root = root or Path.cwd()
    ctx = collect_context(root)
    gen = get_generator(agent_name)
    return gen.write(ctx, root)
