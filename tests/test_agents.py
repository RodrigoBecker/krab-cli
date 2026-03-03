"""Tests for agent integration — Claude Code, Copilot, Codex generators."""

import json
import os

import pytest

from krab_cli.agents import (
    AgentContext,
    ClaudeCodeGenerator,
    CodexGenerator,
    CopilotGenerator,
    collect_context,
    get_generator,
    sync_agent,
    sync_all,
)
from krab_cli.memory import MemoryStore, ProjectSkill

# ─── Context Collection ──────────────────────────────────────────────────


class TestCollectContext:
    def test_empty_project(self, tmp_path):
        ctx = collect_context(tmp_path)
        assert ctx.project_name == ""
        assert ctx.tech_stack == {}

    def test_with_memory(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="TestProject", description="A test")
        store.set_field("tech_stack.backend", "Python")
        store.set_field("architecture_style", "hexagonal")
        store.add_skill(ProjectSkill(name="Python", category="language", version="3.12"))

        ctx = collect_context(tmp_path)
        assert ctx.project_name == "TestProject"
        assert ctx.tech_stack["backend"] == "Python"
        assert ctx.architecture_style == "hexagonal"
        assert len(ctx.skills) == 1

    def test_detects_python_commands(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        ctx = collect_context(tmp_path)
        assert "test" in ctx.commands
        assert "uv run pytest" in ctx.commands["test"]

    def test_detects_node_commands(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest", "lint": "eslint ."}})
        )
        ctx = collect_context(tmp_path)
        assert ctx.commands["test"] == "npm run test"
        assert ctx.commands["lint"] == "npm run lint"

    def test_discovers_spec_files(self, tmp_path):
        specs_dir = tmp_path / ".sdd" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.task.auth.md").write_text("# Auth spec")
        (specs_dir / "spec.architecture.api.md").write_text("# API arch")
        ctx = collect_context(tmp_path)
        assert len(ctx.spec_files) >= 2

    def test_directory_structure(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / ".git").mkdir()  # should be excluded
        ctx = collect_context(tmp_path)
        assert "src/" in ctx.directory_structure
        assert "tests/" in ctx.directory_structure
        assert ".git" not in ctx.directory_structure


# ─── Claude Code Generator ───────────────────────────────────────────────


class TestClaudeCodeGenerator:
    def test_generates_claude_md(self, tmp_path):
        ctx = AgentContext(
            project_name="Builder",
            description="Integration platform",
            architecture_style="hexagonal",
            tech_stack={"backend": "Python", "db": "PostgreSQL"},
            conventions={"commits": "conventional commits"},
            constraints=["REST API only"],
        )
        gen = ClaudeCodeGenerator()
        files = gen.generate(ctx, tmp_path)

        assert len(files) == 1
        path, content = files[0]
        assert path.name == "CLAUDE.md"
        assert "Builder" in content
        assert "hexagonal" in content
        assert "Python" in content
        assert "REST API only" in content
        assert "SDD Workflow" in content

    def test_includes_progressive_disclosure(self, tmp_path):
        ctx = AgentContext(
            spec_files=[".sdd/specs/spec.task.auth.md", ".sdd/specs/spec.architecture.api.md"],
        )
        gen = ClaudeCodeGenerator()
        files = gen.generate(ctx, tmp_path)
        _, content = files[0]
        assert ".sdd/specs/spec.task.auth.md" in content
        assert "Read these" in content or "requirements" in content.lower()

    def test_includes_commands(self, tmp_path):
        ctx = AgentContext(
            commands={"test": "uv run pytest", "lint": "uv run ruff check"},
        )
        gen = ClaudeCodeGenerator()
        _, content = gen.generate(ctx, tmp_path)[0]
        assert "uv run pytest" in content
        assert "uv run ruff check" in content

    def test_writes_file(self, tmp_path):
        ctx = AgentContext(project_name="Test")
        gen = ClaudeCodeGenerator()
        gen.write(ctx, tmp_path)
        # File was written
        assert (tmp_path / "CLAUDE.md").exists()


# ─── Copilot Generator ───────────────────────────────────────────────────


class TestCopilotGenerator:
    def test_generates_instructions(self, tmp_path):
        ctx = AgentContext(
            project_name="Builder",
            architecture_style="hexagonal",
            tech_stack={"backend": "Node.js"},
            conventions={"commits": "conventional"},
            domain_terms={"pedido": "sales order"},
        )
        gen = CopilotGenerator()
        files = gen.generate(ctx, tmp_path)

        assert len(files) >= 1
        main_path, main_content = files[0]
        assert ".github/copilot-instructions.md" in str(main_path)
        assert "Builder" in main_content
        assert "hexagonal" in main_content
        assert "Node.js" in main_content
        assert "pedido" in main_content

    def test_generates_path_specific_for_specs(self, tmp_path):
        ctx = AgentContext(
            spec_files=[".sdd/specs/spec.task.auth.md"],
        )
        gen = CopilotGenerator()
        files = gen.generate(ctx, tmp_path)

        assert len(files) == 2
        spec_path, spec_content = files[1]
        assert "instructions" in str(spec_path)
        assert "applyTo" in spec_content
        assert "Gherkin" in spec_content

    def test_short_statements(self, tmp_path):
        ctx = AgentContext(
            project_name="Test",
            tech_stack={"backend": "Python"},
            constraints=["Max 200ms latency"],
        )
        gen = CopilotGenerator()
        _, content = gen.generate(ctx, tmp_path)[0]
        # Copilot instructions should be short paragraphs
        lines = content.strip().split("\n\n")
        assert all(len(line) < 500 for line in lines)

    def test_writes_files(self, tmp_path):
        ctx = AgentContext(project_name="Test", spec_files=[".sdd/specs/spec.task.md"])
        gen = CopilotGenerator()
        gen.write(ctx, tmp_path)
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()
        assert (tmp_path / ".github" / "instructions" / "krab-specs.instructions.md").exists()


# ─── Codex Generator ─────────────────────────────────────────────────────


class TestCodexGenerator:
    def test_generates_agents_md(self, tmp_path):
        ctx = AgentContext(
            project_name="Builder",
            description="Integration platform",
            architecture_style="hexagonal",
            tech_stack={"backend": "Python"},
            commands={"test": "uv run pytest"},
            constraints=["REST only"],
        )
        gen = CodexGenerator()
        files = gen.generate(ctx, tmp_path)

        assert len(files) >= 1
        path, content = files[0]
        assert path.name == "AGENTS.md"
        assert "Builder" in content
        assert "hexagonal" in content
        assert "uv run pytest" in content
        assert "REST only" in content

    def test_includes_testing_section(self, tmp_path):
        ctx = AgentContext(
            commands={"test": "npm test", "lint": "npm run lint"},
        )
        gen = CodexGenerator()
        _, content = gen.generate(ctx, tmp_path)[0]
        assert "Testing" in content
        assert "npm test" in content

    def test_generates_skill(self, tmp_path):
        ctx = AgentContext(
            spec_files=[".sdd/specs/spec.task.auth.md"],
        )
        gen = CodexGenerator()
        files = gen.generate(ctx, tmp_path)

        skill_files = [f for f in files if "SKILL.md" in str(f[0])]
        assert len(skill_files) == 1
        _, skill_content = skill_files[0]
        assert "krab-workflow" in skill_content
        assert "krab analyze risk" in skill_content

    def test_writes_files(self, tmp_path):
        ctx = AgentContext(project_name="Test", spec_files=[".sdd/specs/spec.md"])
        gen = CodexGenerator()
        gen.write(ctx, tmp_path)
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / ".agents" / "skills" / "krab-workflow" / "SKILL.md").exists()

    def test_includes_pr_guidelines(self, tmp_path):
        ctx = AgentContext()
        gen = CodexGenerator()
        _, content = gen.generate(ctx, tmp_path)[0]
        assert "Pull Request" in content
        assert "conventional commit" in content.lower()


# ─── Registry ────────────────────────────────────────────────────────────


class TestRegistry:
    def test_get_claude(self):
        gen = get_generator("claude")
        assert isinstance(gen, ClaudeCodeGenerator)

    def test_get_copilot(self):
        gen = get_generator("copilot")
        assert isinstance(gen, CopilotGenerator)

    def test_get_codex(self):
        gen = get_generator("codex")
        assert isinstance(gen, CodexGenerator)

    def test_unknown(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            get_generator("unknown")


# ─── Sync Functions ──────────────────────────────────────────────────────


class TestSync:
    def test_sync_all(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="SyncTest")
        store.set_field("tech_stack.backend", "Python")

        results = sync_all(tmp_path)
        assert "claude" in results
        assert "copilot" in results
        assert "codex" in results
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "AGENTS.md").exists()
        assert (tmp_path / ".github" / "copilot-instructions.md").exists()

    def test_sync_single(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="SyncSingle")

        paths = sync_agent("claude", tmp_path)
        assert len(paths) == 1
        assert (tmp_path / "CLAUDE.md").exists()
        # Others should NOT exist
        assert not (tmp_path / "AGENTS.md").exists()


# ─── CLI Commands ─────────────────────────────────────────────────────────


class TestAgentCLI:
    def test_agent_sync_all(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)

        # Init memory first
        runner.invoke(app, ["memory", "init", "--name", "CLITest"])
        runner.invoke(app, ["memory", "set", "tech_stack.backend", "Python"])

        result = runner.invoke(app, ["agent", "sync"])
        assert result.exit_code == 0
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "AGENTS.md").exists()

    def test_agent_sync_single(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])

        result = runner.invoke(app, ["agent", "sync", "claude"])
        assert result.exit_code == 0
        assert (tmp_path / "CLAUDE.md").exists()

    def test_agent_status(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)

        result = runner.invoke(app, ["agent", "status"])
        assert result.exit_code == 0
        assert "missing" in result.output or "exists" in result.output

    def test_agent_preview(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Preview"])

        result = runner.invoke(app, ["agent", "preview", "claude"])
        assert result.exit_code == 0

    def test_agent_diff_new(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Diff"])

        result = runner.invoke(app, ["agent", "diff", "claude"])
        assert result.exit_code == 0
        assert "new file" in result.output

    def test_agent_invalid_target(self, tmp_path):
        from typer.testing import CliRunner

        from krab_cli.cli import app

        runner = CliRunner()
        os.chdir(tmp_path)

        result = runner.invoke(app, ["agent", "sync", "invalid"])
        assert result.exit_code == 1
