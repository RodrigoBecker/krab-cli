"""Tests for the Slash Command Generator (workflows/commands.py)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from krab_cli.workflows import OnFailure, StepType, Workflow, WorkflowStep

runner = CliRunner()


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_workflow() -> Workflow:
    return Workflow(
        name="implement",
        description="Implement a feature from spec",
        default_agent="claude",
        steps=[
            WorkflowStep(name="check-spec", type=StepType.GATE, condition="file_exists:{spec}"),
            WorkflowStep(
                name="risk-check",
                type=StepType.KRAB,
                command="analyze risk {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="delegate",
                type=StepType.AGENT,
                agent="{agent}",
                prompt="Implement the feature described in the specification.",
            ),
            WorkflowStep(
                name="run-tests",
                type=StepType.SHELL,
                command="uv run pytest",
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


@pytest.fixture()
def sample_workflows(sample_workflow: Workflow) -> list[Workflow]:
    review = Workflow(
        name="review",
        description="Review code against spec",
        steps=[
            WorkflowStep(name="gate", type=StepType.GATE, condition="file_exists:{spec}"),
            WorkflowStep(
                name="review",
                type=StepType.AGENT,
                agent="claude",
                prompt="Review the implementation against the spec.",
            ),
        ],
    )
    return [sample_workflow, review]


@pytest.fixture()
def project_with_memory(tmp_path):
    """Create a project dir with .sdd/memory.json."""
    sdd = tmp_path / ".sdd"
    sdd.mkdir()
    memory = {
        "project_name": "TestProject",
        "description": "A test project",
        "tech_stack": {"backend": "Python/FastAPI", "db": "PostgreSQL"},
        "architecture_style": "hexagonal",
        "conventions": {"commits": "conventional"},
        "domain_terms": {},
        "team_context": {},
        "integrations": [],
        "constraints": ["No external APIs"],
        "decisions": [],
        "created_at": "",
        "updated_at": "",
    }
    (sdd / "memory.json").write_text(json.dumps(memory))
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


class TestHelpers:
    def test_build_context_block_with_memory(self, project_with_memory):
        from krab_cli.workflows.commands import _build_context_block

        ctx = _build_context_block(project_with_memory)
        assert "## Project Context" in ctx
        assert "TestProject" in ctx
        assert "Python/FastAPI" in ctx
        assert "hexagonal" in ctx
        assert "No external APIs" in ctx

    def test_build_context_block_no_memory(self, tmp_path):
        from krab_cli.workflows.commands import _build_context_block

        ctx = _build_context_block(tmp_path)
        assert ctx == ""

    def test_workflow_to_steps_markdown(self, sample_workflow):
        from krab_cli.workflows.commands import _workflow_to_steps_markdown

        md = _workflow_to_steps_markdown(sample_workflow)
        assert "**Gate**" in md
        assert "file_exists:{spec}" in md
        assert "`krab analyze risk {spec}`" in md
        assert "**Agent**" in md
        assert "**Shell**" in md
        assert "uv run pytest" in md
        assert "On failure: continue" in md
        # Agent step should include the FULL prompt, not truncated
        assert "Implement the feature described in the specification." in md
        # Agent step should include mode-specific instructions
        assert "Follow the specification" in md

    def test_workflow_to_steps_markdown_enrich_mode(self):
        from krab_cli.workflows.commands import _workflow_to_steps_markdown

        wf = Workflow(
            name="enrich-test",
            steps=[
                WorkflowStep(
                    name="enrich",
                    type=StepType.AGENT,
                    agent="claude",
                    prompt=(
                        "[mode:enrich]Leia o arquivo spec.md e reescreva "
                        "substituindo todos os placeholders."
                    ),
                ),
            ],
        )
        md = _workflow_to_steps_markdown(wf)
        # Should NOT contain raw [mode:enrich] prefix
        assert "[mode:enrich]" not in md
        # Should contain enrich-specific instructions
        assert "Enrich spec" in md
        assert "IN-PLACE" in md
        assert "placeholders" in md
        assert "pt-BR" in md
        assert "Gherkin" in md
        # Should contain the full clean prompt
        assert "Leia o arquivo spec.md" in md

    def test_parse_agent_prompt_with_mode(self):
        from krab_cli.workflows.commands import _parse_agent_prompt

        mode, prompt = _parse_agent_prompt("[mode:enrich]Rewrite the spec")
        assert mode == "enrich"
        assert prompt == "Rewrite the spec"

    def test_parse_agent_prompt_without_mode(self):
        from krab_cli.workflows.commands import _parse_agent_prompt

        mode, prompt = _parse_agent_prompt("Implement the feature")
        assert mode == "implement"
        assert prompt == "Implement the feature"

    def test_extract_krab_commands(self, sample_workflow):
        from krab_cli.workflows.commands import _extract_krab_commands

        cmds = _extract_krab_commands(sample_workflow)
        assert len(cmds) == 1
        assert "krab analyze risk {spec}" in cmds


# ═══════════════════════════════════════════════════════════════════════════
# Claude Code Generator
# ═══════════════════════════════════════════════════════════════════════════


class TestClaudeCommands:
    def test_generates_router(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        paths = [p for p, _ in files]
        router = tmp_path / ".claude" / "commands" / "krab.md"
        assert router in paths

    def test_generates_per_workflow(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        paths = [p for p, _ in files]
        assert tmp_path / ".claude" / "commands" / "krab-implement.md" in paths
        assert tmp_path / ".claude" / "commands" / "krab-review.md" in paths

    def test_router_has_frontmatter(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        router_content = files[0][1]
        assert router_content.startswith("---\n")
        assert "description:" in router_content
        assert "$ARGUMENTS" in router_content

    def test_workflow_command_has_frontmatter(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        # First per-workflow command (implement)
        impl_content = files[1][1]
        assert impl_content.startswith("---\n")
        assert "description:" in impl_content
        assert "$ARGUMENTS" in impl_content
        assert "implement" in impl_content.lower()

    def test_command_includes_steps(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        impl_content = files[1][1]
        assert "krab analyze risk" in impl_content
        assert "Gate" in impl_content

    def test_command_includes_krab_commands_section(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        impl_content = files[1][1]
        assert "## Krab Commands" in impl_content

    def test_with_memory_context(self, sample_workflows, project_with_memory):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, project_with_memory)
        router_content = files[0][1]
        assert "TestProject" in router_content

    def test_file_count(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_claude_commands

        files = generate_claude_commands(sample_workflows, tmp_path)
        # 1 router + 2 per-workflow
        assert len(files) == 3

    def test_enrich_workflow_has_full_prompt(self, tmp_path):
        """Claude command for spec-create must include full enrich instructions."""
        from krab_cli.workflows.builtins import get_builtin
        from krab_cli.workflows.commands import generate_claude_commands

        wf = get_builtin("spec-create")
        files = generate_claude_commands([wf], tmp_path)
        # Per-workflow command (index 1, after router)
        content = files[1][1]
        # Must contain enrich-specific instructions, not truncated
        assert "IN-PLACE" in content
        assert "pt-BR" in content
        assert "Gherkin" in content
        # Must NOT contain raw mode prefix
        assert "[mode:enrich]" not in content

    def test_implement_workflow_has_full_agent_prompt(self, tmp_path):
        """Claude command for implement must include full agent instructions."""
        from krab_cli.workflows.builtins import get_builtin
        from krab_cli.workflows.commands import generate_claude_commands

        wf = get_builtin("implement")
        files = generate_claude_commands([wf], tmp_path)
        content = files[1][1]
        assert "Implement the feature described in the specification" in content
        assert "Follow the specification" in content


# ═══════════════════════════════════════════════════════════════════════════
# Copilot Generator
# ═══════════════════════════════════════════════════════════════════════════


class TestCopilotFiles:
    def test_generates_agent(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        paths = [p for p, _ in files]
        agent = tmp_path / ".github" / "agents" / "krab.agent.md"
        assert agent in paths

    def test_agent_has_required_frontmatter(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        agent_content = files[0][1]
        assert "---" in agent_content
        assert "description:" in agent_content
        assert "tools:" in agent_content

    def test_agent_lists_workflows(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        agent_content = files[0][1]
        assert "implement" in agent_content
        assert "review" in agent_content

    def test_generates_prompts(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        paths = [str(p) for p, _ in files]
        assert any("krab-implement.prompt.md" in p for p in paths)
        assert any("krab-review.prompt.md" in p for p in paths)

    def test_prompt_has_agent_mode(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        # Find a prompt file
        prompt_files = [(p, c) for p, c in files if "prompt.md" in str(p)]
        assert len(prompt_files) > 0
        content = prompt_files[0][1]
        assert "agent: 'agent'" in content

    def test_prompt_has_input_variable(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        prompt_files = [(p, c) for p, c in files if "prompt.md" in str(p)]
        content = prompt_files[0][1]
        assert "${input:spec:" in content

    def test_generates_skills(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        paths = [str(p) for p, _ in files]
        assert any("krab-implement/SKILL.md" in p for p in paths)
        assert any("krab-review/SKILL.md" in p for p in paths)

    def test_skill_has_required_frontmatter(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        skill_files = [(p, c) for p, c in files if "SKILL.md" in str(p)]
        assert len(skill_files) > 0
        content = skill_files[0][1]
        assert "name:" in content
        assert "description:" in content

    def test_file_count(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_copilot_files

        files = generate_copilot_files(sample_workflows, tmp_path)
        # 1 agent + 2 prompts + 2 skills = 5
        assert len(files) == 5

    def test_enrich_workflow_prompt_has_full_instructions(self, tmp_path):
        """Copilot prompt for spec-create must include full enrich instructions."""
        from krab_cli.workflows.builtins import get_builtin
        from krab_cli.workflows.commands import generate_copilot_files

        wf = get_builtin("spec-create")
        files = generate_copilot_files([wf], tmp_path)
        # Find the prompt file for spec-create
        prompt_files = [(p, c) for p, c in files if "prompt.md" in str(p)]
        assert len(prompt_files) > 0
        content = prompt_files[0][1]
        # Must contain enrich-specific instructions
        assert "IN-PLACE" in content
        assert "pt-BR" in content
        assert "Gherkin" in content
        # Must NOT contain raw mode prefix
        assert "[mode:enrich]" not in content

    def test_enrich_workflow_skill_has_full_instructions(self, tmp_path):
        """Copilot skill for spec-create must include full enrich instructions."""
        from krab_cli.workflows.builtins import get_builtin
        from krab_cli.workflows.commands import generate_copilot_files

        wf = get_builtin("spec-create")
        files = generate_copilot_files([wf], tmp_path)
        skill_files = [(p, c) for p, c in files if "SKILL.md" in str(p)]
        assert len(skill_files) > 0
        content = skill_files[0][1]
        assert "IN-PLACE" in content
        assert "[mode:enrich]" not in content


# ═══════════════════════════════════════════════════════════════════════════
# Cross-Agent Skills
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossAgentSkills:
    def test_generates_skill_per_workflow(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_cross_agent_skills

        files = generate_cross_agent_skills(sample_workflows, tmp_path)
        assert len(files) == 2

    def test_skill_path_format(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_cross_agent_skills

        files = generate_cross_agent_skills(sample_workflows, tmp_path)
        paths = [str(p) for p, _ in files]
        assert any(".github/skills/krab-implement/SKILL.md" in p for p in paths)

    def test_skill_content(self, sample_workflows, tmp_path):
        from krab_cli.workflows.commands import generate_cross_agent_skills

        files = generate_cross_agent_skills(sample_workflows, tmp_path)
        content = files[0][1]
        assert "name: krab-implement" in content
        assert "Gherkin" in content


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


class TestGenerateAll:
    def test_generates_for_all_agents(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        results = generate_all(root=tmp_path)
        assert "claude" in results
        assert "copilot" in results
        assert len(results["claude"]) > 0
        assert len(results["copilot"]) > 0

    def test_files_are_written(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        results = generate_all(root=tmp_path)
        for paths in results.values():
            for p in paths:
                assert p.exists(), f"File not written: {p}"

    def test_filter_by_agent(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        results = generate_all(root=tmp_path, agent="claude")
        assert "claude" in results
        assert "copilot" not in results

    def test_filter_by_workflow(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        results = generate_all(root=tmp_path, workflow="implement")
        # Claude: 1 router + 1 workflow command + 13 CLI slash commands = 15
        assert len(results["claude"]) == 15
        # Copilot: 1 agent + 1 prompt + 1 skill + 13 CLI slash commands = 16
        assert len(results["copilot"]) == 16

    def test_unknown_agent_raises(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        with pytest.raises(ValueError, match="Unknown agent"):
            generate_all(root=tmp_path, agent="nonexistent")

    def test_unknown_workflow_raises(self, tmp_path):
        from krab_cli.workflows.commands import generate_all

        with pytest.raises(ValueError, match="Workflow not found"):
            generate_all(root=tmp_path, workflow="nonexistent-wf")


class TestPreview:
    def test_returns_content_without_writing(self, tmp_path):
        from krab_cli.workflows.commands import preview

        results = preview(root=tmp_path)
        assert "claude" in results
        assert "copilot" in results
        # Verify content is returned
        for files in results.values():
            for path, content in files:
                assert len(content) > 0
                # Files should NOT be written
                assert not path.exists(), f"Preview should not write: {path}"

    def test_filter_by_agent(self, tmp_path):
        from krab_cli.workflows.commands import preview

        results = preview(root=tmp_path, agent="copilot")
        assert "copilot" in results
        assert "claude" not in results


class TestClean:
    def test_removes_generated_files(self, tmp_path):
        from krab_cli.workflows.commands import clean, generate_all

        generate_all(root=tmp_path)
        # Verify files exist
        assert (tmp_path / ".claude" / "commands" / "krab.md").exists()
        assert (tmp_path / ".github" / "agents" / "krab.agent.md").exists()

        removed = clean(root=tmp_path)
        assert len(removed) > 0
        assert not (tmp_path / ".claude" / "commands" / "krab.md").exists()
        assert not (tmp_path / ".github" / "agents" / "krab.agent.md").exists()

    def test_clean_empty_dir(self, tmp_path):
        from krab_cli.workflows.commands import clean

        removed = clean(root=tmp_path)
        assert len(removed) == 0


# ═══════════════════════════════════════════════════════════════════════════
# CLI Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowCommandsCLI:
    def test_workflow_commands_generates(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["workflow", "commands"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "commands" / "krab.md").exists()
        assert (tmp_path / ".github" / "agents" / "krab.agent.md").exists()

    def test_workflow_commands_preview(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["workflow", "commands", "--preview"])
        assert result.exit_code == 0
        # Files should NOT be written in preview mode
        assert not (tmp_path / ".claude" / "commands" / "krab.md").exists()

    def test_workflow_commands_clean(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        # First generate
        runner.invoke(app, ["workflow", "commands"])
        assert (tmp_path / ".claude" / "commands" / "krab.md").exists()
        # Then clean
        result = runner.invoke(app, ["workflow", "commands", "--clean"])
        assert result.exit_code == 0
        assert not (tmp_path / ".claude" / "commands" / "krab.md").exists()

    def test_workflow_commands_filter_agent(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["workflow", "commands", "--agent", "claude"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "commands" / "krab.md").exists()
        # Copilot files should NOT exist
        assert not (tmp_path / ".github" / "agents" / "krab.agent.md").exists()

    def test_workflow_commands_filter_workflow(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["workflow", "commands", "--workflow", "implement"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "commands" / "krab-implement.md").exists()
        # review should NOT exist
        assert not (tmp_path / ".claude" / "commands" / "krab-review.md").exists()


class TestAgentSyncIncludesCommands:
    def test_agent_sync_generates_commands(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        # Init memory so agent sync works
        sdd = tmp_path / ".sdd"
        sdd.mkdir()
        memory = {
            "project_name": "Test",
            "description": "",
            "tech_stack": {},
            "architecture_style": "",
            "conventions": {},
            "domain_terms": {},
            "team_context": {},
            "integrations": [],
            "constraints": [],
            "decisions": [],
            "created_at": "",
            "updated_at": "",
        }
        (sdd / "memory.json").write_text(json.dumps(memory))

        result = runner.invoke(app, ["agent", "sync"])
        assert result.exit_code == 0
        # Should generate both instruction files AND command files
        assert "slash command" in result.output.lower() or "cmd" in result.output.lower()

    def test_agent_sync_no_commands_flag(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        sdd = tmp_path / ".sdd"
        sdd.mkdir()
        memory = {
            "project_name": "Test",
            "description": "",
            "tech_stack": {},
            "architecture_style": "",
            "conventions": {},
            "domain_terms": {},
            "team_context": {},
            "integrations": [],
            "constraints": [],
            "decisions": [],
            "created_at": "",
            "updated_at": "",
        }
        (sdd / "memory.json").write_text(json.dumps(memory))

        result = runner.invoke(app, ["agent", "sync", "--no-commands"])
        assert result.exit_code == 0
        # Command files should NOT be generated
        assert not (tmp_path / ".claude" / "commands" / "krab.md").exists()
