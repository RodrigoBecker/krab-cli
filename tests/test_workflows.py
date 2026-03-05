"""Tests for the Krab Workflow Engine, Agent Executor, Built-in Workflows, and CLI commands."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from krab_cli.workflows import (
    OnFailure,
    StepResult,
    StepType,
    Workflow,
    WorkflowResult,
    WorkflowRunner,
    WorkflowStep,
    resolve_variables,
)

runner = CliRunner()


# ═══════════════════════════════════════════════════════════════════════════
# WorkflowStep & Workflow — Serialization
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowStep:
    def test_to_dict_minimal(self):
        step = WorkflowStep(name="check", type=StepType.GATE, condition="file_exists:x")
        d = step.to_dict()
        assert d["name"] == "check"
        assert d["type"] == "gate"
        assert d["condition"] == "file_exists:x"
        assert "command" not in d
        assert "on_failure" not in d  # default is stop, omitted

    def test_to_dict_full(self):
        step = WorkflowStep(
            name="run-tests",
            type=StepType.SHELL,
            command="pytest",
            on_failure=OnFailure.CONTINUE,
        )
        d = step.to_dict()
        assert d["on_failure"] == "continue"
        assert d["command"] == "pytest"

    def test_from_dict_roundtrip(self):
        step = WorkflowStep(
            name="agent-step",
            type=StepType.AGENT,
            agent="claude",
            prompt="Implement the feature",
            on_failure=OnFailure.CONTINUE,
        )
        d = step.to_dict()
        restored = WorkflowStep.from_dict(d)
        assert restored.name == step.name
        assert restored.type == step.type
        assert restored.agent == step.agent
        assert restored.prompt == step.prompt
        assert restored.on_failure == step.on_failure

    def test_from_dict_defaults(self):
        d = {"name": "test", "type": "krab", "command": "analyze risk x.md"}
        step = WorkflowStep.from_dict(d)
        assert step.on_failure == OnFailure.STOP
        assert step.agent == ""
        assert step.condition == ""


class TestWorkflow:
    def test_to_dict(self):
        wf = Workflow(
            name="test-wf",
            description="Test workflow",
            steps=[
                WorkflowStep(name="s1", type=StepType.KRAB, command="analyze risk x"),
            ],
        )
        d = wf.to_dict()
        assert d["name"] == "test-wf"
        assert len(d["steps"]) == 1

    def test_yaml_roundtrip(self):
        wf = Workflow(
            name="roundtrip",
            description="YAML round-trip test",
            default_agent="codex",
            steps=[
                WorkflowStep(name="gate", type=StepType.GATE, condition="file_exists:spec.md"),
                WorkflowStep(
                    name="impl",
                    type=StepType.AGENT,
                    agent="codex",
                    prompt="Do the thing",
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )
        yaml_text = wf.to_yaml()
        restored = Workflow.from_yaml(yaml_text)
        assert restored.name == "roundtrip"
        assert restored.default_agent == "codex"
        assert len(restored.steps) == 2
        assert restored.steps[1].agent == "codex"
        assert restored.steps[1].on_failure == OnFailure.CONTINUE

    def test_save_and_load(self, tmp_path):
        wf = Workflow(
            name="persist-test",
            description="Save/load test",
            steps=[
                WorkflowStep(name="step1", type=StepType.SHELL, command="echo hello"),
            ],
        )
        path = tmp_path / "wf.yaml"
        wf.save(path)
        assert path.exists()

        loaded = Workflow.load(path)
        assert loaded.name == "persist-test"
        assert len(loaded.steps) == 1
        assert loaded.steps[0].command == "echo hello"

    def test_from_dict_no_steps(self):
        wf = Workflow.from_dict({"name": "empty"})
        assert wf.name == "empty"
        assert wf.steps == []
        assert wf.default_agent == "claude"


# ═══════════════════════════════════════════════════════════════════════════
# resolve_variables
# ═══════════════════════════════════════════════════════════════════════════


class TestResolveVariables:
    def test_basic_substitution(self):
        result = resolve_variables("analyze risk {spec}", {"spec": ".sdd/specs/spec.task.auth.md"})
        assert result == "analyze risk .sdd/specs/spec.task.auth.md"

    def test_multiple_variables(self):
        result = resolve_variables(
            "{agent} runs on {root}/{spec}",
            {"agent": "claude", "root": "/home/user", "spec": "spec.md"},
        )
        assert result == "claude runs on /home/user/spec.md"

    def test_missing_variable_left_as_is(self):
        result = resolve_variables("file_exists:{spec}", {"root": "/tmp"})
        assert result == "file_exists:{spec}"

    def test_empty_context(self):
        result = resolve_variables("hello {world}", {})
        assert result == "hello {world}"


# ═══════════════════════════════════════════════════════════════════════════
# Gate evaluation
# ═══════════════════════════════════════════════════════════════════════════


class TestGateEvaluation:
    def test_file_exists_true(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("content", encoding="utf-8")
        from krab_cli.workflows import _evaluate_gate

        assert _evaluate_gate(f"file_exists:{spec}", {}) is True

    def test_file_exists_false(self):
        from krab_cli.workflows import _evaluate_gate

        assert _evaluate_gate("file_exists:/nonexistent/file.md", {}) is False

    def test_env_var_true(self):
        from krab_cli.workflows import _evaluate_gate

        os.environ["_KRAB_TEST_VAR"] = "1"
        try:
            assert _evaluate_gate("env:_KRAB_TEST_VAR", {}) is True
        finally:
            del os.environ["_KRAB_TEST_VAR"]

    def test_env_var_false(self):
        from krab_cli.workflows import _evaluate_gate

        assert _evaluate_gate("env:_KRAB_NONEXISTENT_VAR_XYZ", {}) is False

    def test_truthy_string(self):
        from krab_cli.workflows import _evaluate_gate

        assert _evaluate_gate("true", {}) is True
        assert _evaluate_gate("yes", {}) is True

    def test_falsy_string(self):
        from krab_cli.workflows import _evaluate_gate

        assert _evaluate_gate("false", {}) is False
        assert _evaluate_gate("0", {}) is False
        assert _evaluate_gate("no", {}) is False
        assert _evaluate_gate("", {}) is False

    def test_variable_resolution_in_gate(self, tmp_path):
        from krab_cli.workflows import _evaluate_gate

        spec = tmp_path / "spec.md"
        spec.write_text("x", encoding="utf-8")
        assert _evaluate_gate("file_exists:{spec}", {"spec": str(spec)}) is True


# ═══════════════════════════════════════════════════════════════════════════
# WorkflowRunner
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowRunner:
    def test_dry_run_krab_step(self):
        wf = Workflow(
            name="dry",
            steps=[
                WorkflowStep(name="s1", type=StepType.KRAB, command="analyze risk {spec}"),
            ],
        )
        runner = WorkflowRunner(spec="spec.md", dry_run=True)
        result = runner.run(wf)
        assert result.success
        assert len(result.steps) == 1
        assert "[dry-run]" in result.steps[0].output
        assert "krab analyze risk spec.md" in result.steps[0].output

    def test_dry_run_agent_step(self):
        wf = Workflow(
            name="dry-agent",
            steps=[
                WorkflowStep(name="s1", type=StepType.AGENT, agent="claude", prompt="Do something"),
            ],
        )
        runner = WorkflowRunner(dry_run=True)
        result = runner.run(wf)
        assert result.success
        assert "claude" in result.steps[0].output

    def test_dry_run_gate_step(self, tmp_path):
        wf = Workflow(
            name="dry-gate",
            steps=[
                WorkflowStep(name="gate", type=StepType.GATE, condition="file_exists:{spec}"),
            ],
        )
        runner = WorkflowRunner(spec=str(tmp_path / "x.md"), dry_run=True)
        result = runner.run(wf)
        assert result.success
        assert "Would check" in result.steps[0].output

    def test_gate_pass(self, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("content", encoding="utf-8")
        wf = Workflow(
            name="gate-pass",
            steps=[
                WorkflowStep(name="gate", type=StepType.GATE, condition=f"file_exists:{spec}"),
            ],
        )
        runner = WorkflowRunner()
        result = runner.run(wf)
        assert result.success
        assert result.steps[0].output == "Gate passed"

    def test_gate_fail_stops_workflow(self):
        wf = Workflow(
            name="gate-fail",
            steps=[
                WorkflowStep(name="gate", type=StepType.GATE, condition="file_exists:/nonexistent"),
                WorkflowStep(name="never-reached", type=StepType.SHELL, command="echo hi"),
            ],
        )
        runner = WorkflowRunner()
        result = runner.run(wf)
        assert not result.success
        assert len(result.steps) == 1  # Second step never executed

    def test_shell_step_success(self, tmp_path):
        wf = Workflow(
            name="shell",
            steps=[
                WorkflowStep(name="echo", type=StepType.SHELL, command="echo hello-krab"),
            ],
        )
        runner = WorkflowRunner(root=tmp_path)
        result = runner.run(wf)
        assert result.success
        assert "hello-krab" in result.steps[0].output

    def test_shell_step_failure(self, tmp_path):
        wf = Workflow(
            name="shell-fail",
            steps=[
                WorkflowStep(name="fail", type=StepType.SHELL, command="exit 42"),
            ],
        )
        runner = WorkflowRunner(root=tmp_path)
        result = runner.run(wf)
        assert not result.success
        assert "42" in result.steps[0].error

    def test_on_failure_continue(self, tmp_path):
        wf = Workflow(
            name="continue",
            steps=[
                WorkflowStep(
                    name="fail-ok",
                    type=StepType.SHELL,
                    command="exit 1",
                    on_failure=OnFailure.CONTINUE,
                ),
                WorkflowStep(name="echo", type=StepType.SHELL, command="echo reached"),
            ],
        )
        runner = WorkflowRunner(root=tmp_path)
        result = runner.run(wf)
        # Workflow succeeds overall because the failing step had on_failure=continue
        assert result.success
        assert len(result.steps) == 2
        assert not result.steps[0].success
        assert result.steps[1].success

    def test_on_step_callback(self):
        wf = Workflow(
            name="callback",
            steps=[
                WorkflowStep(name="s1", type=StepType.SHELL, command="echo a"),
            ],
        )
        captured = []
        runner = WorkflowRunner(
            on_step=lambda step, result: captured.append((step.name, result.success))
        )
        result = runner.run(wf)
        assert result.success
        assert len(captured) == 1
        assert captured[0] == ("s1", True)

    def test_result_counts(self, tmp_path):
        wf = Workflow(
            name="counts",
            steps=[
                WorkflowStep(name="pass", type=StepType.SHELL, command="echo ok"),
                WorkflowStep(
                    name="fail",
                    type=StepType.SHELL,
                    command="exit 1",
                    on_failure=OnFailure.CONTINUE,
                ),
                WorkflowStep(name="pass2", type=StepType.SHELL, command="echo ok2"),
            ],
        )
        runner = WorkflowRunner(root=tmp_path)
        result = runner.run(wf)
        assert result.completed_count == 2
        assert result.failed_count == 1
        assert result.skipped_count == 0

    def test_context_resolution(self):
        wf = Workflow(
            name="ctx",
            default_agent="codex",
            steps=[
                WorkflowStep(name="s1", type=StepType.SHELL, command="echo {agent}"),
            ],
        )
        runner = WorkflowRunner(agent="claude", dry_run=True)
        result = runner.run(wf)
        # Agent should be overridden by runner's agent param
        assert "claude" in result.steps[0].output


# ═══════════════════════════════════════════════════════════════════════════
# Agent Executor
# ═══════════════════════════════════════════════════════════════════════════


class TestAgentExecutor:
    def test_unknown_agent(self):
        from krab_cli.workflows.executor import AgentExecutor

        executor = AgentExecutor()
        result = executor.execute("unknown-agent", "do something")
        assert not result.success
        assert "Unknown agent" in result.error

    def test_agent_not_available(self):
        from krab_cli.workflows.executor import AgentExecutor

        with patch("krab_cli.workflows.executor.check_agent_available", return_value=False):
            executor = AgentExecutor()
            result = executor.execute("claude", "do something")
            assert not result.success
            assert "not found" in result.error

    @patch("krab_cli.workflows.executor.check_agent_available", return_value=True)
    @patch("subprocess.run")
    def test_exec_claude_success(self, mock_run, mock_avail):
        from krab_cli.workflows.executor import AgentExecutor

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Implementation complete.",
            stderr="",
        )
        executor = AgentExecutor()
        result = executor.execute("claude", "implement auth feature")
        assert result.success
        assert "Implementation complete." in result.output
        # Verify claude was called with -p flag
        call_args = mock_run.call_args[0][0]
        assert call_args[1] == "-p"

    @patch("krab_cli.workflows.executor.check_agent_available", return_value=True)
    @patch("subprocess.run")
    def test_exec_codex_success(self, mock_run, mock_avail):
        from krab_cli.workflows.executor import AgentExecutor

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Done.",
            stderr="",
        )
        executor = AgentExecutor()
        result = executor.execute("codex", "implement feature")
        assert result.success
        call_args = mock_run.call_args[0][0]
        assert "exec" in call_args

    @patch("krab_cli.workflows.executor.check_agent_available", return_value=True)
    @patch("subprocess.run")
    def test_exec_copilot_success(self, mock_run, mock_avail):
        from krab_cli.workflows.executor import AgentExecutor

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/org/repo/issues/42",
            stderr="",
        )
        executor = AgentExecutor()
        result = executor.execute("copilot", "implement feature")
        assert result.success
        call_args = mock_run.call_args[0][0]
        assert "issue" in call_args
        assert "create" in call_args
        assert "--label" in call_args

    @patch("krab_cli.workflows.executor.check_agent_available", return_value=True)
    @patch("subprocess.run")
    def test_exec_agent_failure(self, mock_run, mock_avail):
        from krab_cli.workflows.executor import AgentExecutor

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: authentication failed",
        )
        executor = AgentExecutor()
        result = executor.execute("claude", "do something")
        assert not result.success
        assert "authentication failed" in result.error

    @patch("krab_cli.workflows.executor.check_agent_available", return_value=True)
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=600))
    def test_exec_agent_timeout(self, mock_run, mock_avail):
        from krab_cli.workflows.executor import AgentExecutor

        executor = AgentExecutor(timeout=600)
        result = executor.execute("claude", "long task")
        assert not result.success
        assert "timed out" in result.error


class TestCheckAgentAvailable:
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_available(self, mock_which):
        from krab_cli.workflows.executor import check_agent_available

        assert check_agent_available("claude") is True

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        from krab_cli.workflows.executor import check_agent_available

        assert check_agent_available("claude") is False

    def test_unknown_agent(self):
        from krab_cli.workflows.executor import check_agent_available

        assert check_agent_available("nonexistent") is False


class TestListAgents:
    def test_returns_all_agents(self):
        from krab_cli.workflows.executor import list_agents

        agents = list_agents()
        keys = [a["key"] for a in agents]
        assert "claude" in keys
        assert "codex" in keys
        assert "copilot" in keys
        assert len(agents) == 3

    def test_agent_fields(self):
        from krab_cli.workflows.executor import list_agents

        agents = list_agents()
        for agent in agents:
            assert "key" in agent
            assert "name" in agent
            assert "command" in agent
            assert "available" in agent
            assert "description" in agent


class TestBuildAgentPrompt:
    def test_basic_prompt(self):
        from krab_cli.workflows.executor import build_agent_prompt

        prompt = build_agent_prompt("Implement the auth feature")
        assert "## Task" in prompt
        assert "Implement the auth feature" in prompt
        assert "## Instructions" in prompt

    def test_prompt_with_spec(self, tmp_path):
        from krab_cli.workflows.executor import build_agent_prompt

        spec = tmp_path / "spec.task.auth.md"
        spec.write_text("# Auth\nGiven a user exists\nWhen they login\nThen they get a token")
        prompt = build_agent_prompt("Implement this", spec_path=str(spec), root=tmp_path)
        assert "## Specification" in prompt
        assert "Given a user exists" in prompt

    def test_prompt_with_memory(self, tmp_path):
        from krab_cli.workflows.executor import build_agent_prompt

        # Create a minimal .sdd/memory.json
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        import json

        memory = {
            "project_name": "TestProject",
            "description": "A test project",
            "tech_stack": {"backend": "Python"},
            "architecture_style": "hexagonal",
            "conventions": {},
            "domain_terms": {},
            "team_context": {},
            "integrations": [],
            "constraints": ["No external APIs"],
            "decisions": [],
            "created_at": "",
            "updated_at": "",
        }
        (sdd_dir / "memory.json").write_text(json.dumps(memory))

        prompt = build_agent_prompt("Do something", root=tmp_path)
        assert "Project: TestProject" in prompt
        assert "Python" in prompt
        assert "No external APIs" in prompt

    def test_prompt_without_memory(self, tmp_path):
        from krab_cli.workflows.executor import build_agent_prompt

        # No .sdd directory — should still produce a prompt
        prompt = build_agent_prompt("Do it", root=tmp_path)
        assert "## Task" in prompt
        assert "Do it" in prompt

    def test_prompt_with_nonexistent_spec(self, tmp_path):
        from krab_cli.workflows.executor import build_agent_prompt

        prompt = build_agent_prompt("Do it", spec_path="nonexistent.md", root=tmp_path)
        # Should not crash, just omit the spec section
        assert "## Task" in prompt
        assert "## Specification" not in prompt


# ═══════════════════════════════════════════════════════════════════════════
# Built-in Workflows
# ═══════════════════════════════════════════════════════════════════════════


class TestBuiltinWorkflows:
    def test_list_builtins(self):
        from krab_cli.workflows.builtins import list_builtins

        builtins = list_builtins()
        names = [b["name"] for b in builtins]
        assert "spec-create" in names
        assert "implement" in names
        assert "review" in names
        assert "full-cycle" in names
        assert "verify" in names
        assert "agent-init" in names
        assert "sdd-lifecycle" in names
        assert len(builtins) == 7

    def test_get_builtin(self):
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("implement")
        assert wf.name == "implement"
        assert len(wf.steps) >= 3

    def test_get_builtin_unknown(self):
        from krab_cli.workflows.builtins import get_builtin

        with pytest.raises(ValueError, match="Unknown built-in"):
            get_builtin("nonexistent-workflow")

    def test_get_all_builtins(self):
        from krab_cli.workflows.builtins import get_all_builtins

        all_wfs = get_all_builtins()
        assert len(all_wfs) == 7
        assert all(isinstance(w, Workflow) for w in all_wfs.values())

    def test_all_builtins_have_valid_steps(self):
        from krab_cli.workflows.builtins import get_all_builtins

        for name, wf in get_all_builtins().items():
            assert wf.name, f"Workflow {name} has no name"
            assert wf.description, f"Workflow {name} has no description"
            assert len(wf.steps) > 0, f"Workflow {name} has no steps"
            for step in wf.steps:
                assert step.name, f"Step in {name} has no name"
                assert isinstance(step.type, StepType), f"Step {step.name} has invalid type"

    def test_all_builtins_yaml_roundtrip(self):
        from krab_cli.workflows.builtins import get_all_builtins

        for name, wf in get_all_builtins().items():
            yaml_text = wf.to_yaml()
            restored = Workflow.from_yaml(yaml_text)
            assert restored.name == wf.name, f"YAML roundtrip failed for {name}"
            assert len(restored.steps) == len(wf.steps), f"Step count mismatch for {name}"

    def test_implement_workflow_structure(self):
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("implement")
        step_types = [s.type for s in wf.steps]
        assert StepType.GATE in step_types
        assert StepType.AGENT in step_types

    def test_full_cycle_workflow_structure(self):
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("full-cycle")
        assert len(wf.steps) == 9
        step_types = [s.type for s in wf.steps]
        assert StepType.AGENT in step_types
        assert StepType.KRAB in step_types

    def test_verify_workflow_all_continue(self):
        """Verify workflow should continue on failures (quality checks are advisory)."""
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("verify")
        # All steps after the gate should have on_failure=continue
        for step in wf.steps:
            if step.type != StepType.GATE:
                assert step.on_failure == OnFailure.CONTINUE, (
                    f"Step '{step.name}' in verify should have on_failure=continue"
                )

    def test_spec_create_has_enrich_step(self):
        """enrich-spec must sit between create-spec and refine-spec."""
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("spec-create")
        names = [s.name for s in wf.steps]
        assert "enrich-spec" in names
        idx = names.index("enrich-spec")
        assert names[idx - 1] == "create-spec"
        assert names[idx + 1] == "refine-spec"

    def test_enrich_step_is_agent_type(self):
        """enrich-spec must be AGENT type with [mode:enrich] prefix."""
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("spec-create")
        enrich = next(s for s in wf.steps if s.name == "enrich-spec")
        assert enrich.type == StepType.AGENT
        assert enrich.prompt.startswith("[mode:enrich]")

    def test_full_cycle_has_enrich_step(self):
        """full-cycle must also contain enrich-spec between create and refine."""
        from krab_cli.workflows.builtins import get_builtin

        wf = get_builtin("full-cycle")
        names = [s.name for s in wf.steps]
        assert "enrich-spec" in names
        idx = names.index("enrich-spec")
        assert names[idx - 1] == "create-spec"
        assert names[idx + 1] == "refine-spec"


class TestEnrichMode:
    def test_build_agent_prompt_enrich_mode(self):
        """Enrich mode must produce pt-BR rewrite instructions."""
        from krab_cli.workflows.executor import build_agent_prompt

        prompt = build_agent_prompt("Enrich this spec", mode="enrich")
        assert "## Instructions" in prompt
        assert "IN-PLACE" in prompt
        assert "pt-BR" in prompt
        assert "placeholders" in prompt

    def test_build_agent_prompt_default_mode(self):
        """Default mode must produce implementation instructions (backward compat)."""
        from krab_cli.workflows.executor import build_agent_prompt

        prompt = build_agent_prompt("Implement feature")
        assert "## Instructions" in prompt
        assert "Follow the specification" in prompt
        assert "Gherkin scenarios as tests" in prompt
        # Must NOT contain enrich-specific content
        assert "IN-PLACE" not in prompt
        assert "pt-BR" not in prompt

    def test_run_agent_detects_enrich_mode(self):
        """Dry-run with enrich-spec step should appear in output."""
        wf = Workflow(
            name="dry-enrich",
            steps=[
                WorkflowStep(
                    name="enrich-spec",
                    type=StepType.AGENT,
                    agent="claude",
                    prompt="[mode:enrich]Rewrite the spec",
                ),
            ],
        )
        wr = WorkflowRunner(spec="auth", dry_run=True)
        result = wr.run(wf)
        assert result.success
        assert "enrich-spec" in result.steps[0].step_name
        assert "claude" in result.steps[0].output


# ═══════════════════════════════════════════════════════════════════════════
# CLI Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowCLI:
    def test_workflow_list(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "list"])
        assert result.exit_code == 0
        assert "implement" in result.output
        assert "spec-create" in result.output
        assert "full-cycle" in result.output

    def test_workflow_show(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "show", "implement"])
        assert result.exit_code == 0
        assert "check-spec-exists" in result.output
        assert "delegate-to-agent" in result.output

    def test_workflow_show_unknown(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "show", "nonexistent"])
        assert result.exit_code != 0

    def test_workflow_run_dry_run(self, tmp_path):
        from krab_cli.cli import app

        spec = tmp_path / "spec.md"
        spec.write_text("# Test spec")
        result = runner.invoke(app, ["workflow", "run", "verify", "--spec", str(spec), "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()

    def test_workflow_run_unknown(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "run", "nonexistent"])
        assert result.exit_code != 0

    def test_workflow_export(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "export", "implement"])
        assert result.exit_code == 0
        assert "implement" in result.output
        assert "steps:" in result.output

    def test_workflow_export_unknown(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "export", "nonexistent"])
        assert result.exit_code != 0

    def test_workflow_new(self, tmp_path, monkeypatch):
        from krab_cli.cli import app

        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["workflow", "new", "my-deploy", "--desc", "Deploy to staging"])
        assert result.exit_code == 0
        wf_file = tmp_path / ".sdd" / "workflows" / "my-deploy.yaml"
        assert wf_file.exists()
        content = wf_file.read_text()
        assert "my-deploy" in content

    def test_workflow_agents_check(self):
        from krab_cli.cli import app

        result = runner.invoke(app, ["workflow", "agents-check"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "Codex" in result.output or "OpenAI" in result.output
        assert "Copilot" in result.output or "GitHub" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# WorkflowResult properties
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkflowResult:
    def test_empty_result(self):
        r = WorkflowResult(workflow_name="test", success=True)
        assert r.completed_count == 0
        assert r.failed_count == 0
        assert r.skipped_count == 0

    def test_mixed_results(self):
        r = WorkflowResult(
            workflow_name="test",
            success=True,
            steps=[
                StepResult(step_name="a", success=True),
                StepResult(step_name="b", success=False, error="failed"),
                StepResult(step_name="c", success=True, skipped=True),
            ],
        )
        assert r.completed_count == 1
        assert r.failed_count == 1
        assert r.skipped_count == 1
