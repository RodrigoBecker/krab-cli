"""Krab Workflow Engine — Define and run multi-step SDD pipelines.

Workflows are sequences of steps that chain SDD operations together.
Each step can be a krab command, shell command, agent delegation, gate, or prompt.

Workflow definitions are YAML files stored in .sdd/workflows/ or built-in defaults.
Variables like {spec}, {agent}, {root} are resolved at runtime.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class StepType(str, Enum):
    """Types of workflow steps."""

    KRAB = "krab"
    SHELL = "shell"
    AGENT = "agent"
    GATE = "gate"
    PROMPT = "prompt"


class OnFailure(str, Enum):
    """Behavior when a step fails."""

    STOP = "stop"
    CONTINUE = "continue"


@dataclass
class WorkflowStep:
    """A single step in a workflow pipeline."""

    name: str
    type: StepType
    command: str = ""
    prompt: str = ""
    agent: str = ""
    condition: str = ""
    on_failure: OnFailure = OnFailure.STOP

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "type": self.type.value}
        if self.command:
            d["command"] = self.command
        if self.prompt:
            d["prompt"] = self.prompt
        if self.agent:
            d["agent"] = self.agent
        if self.condition:
            d["condition"] = self.condition
        if self.on_failure != OnFailure.STOP:
            d["on_failure"] = self.on_failure.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowStep:
        return cls(
            name=data["name"],
            type=StepType(data["type"]),
            command=data.get("command", ""),
            prompt=data.get("prompt", ""),
            agent=data.get("agent", ""),
            condition=data.get("condition", ""),
            on_failure=OnFailure(data.get("on_failure", "stop")),
        )


@dataclass
class Workflow:
    """A complete workflow definition with ordered steps."""

    name: str
    description: str = ""
    default_agent: str = "claude"
    steps: list[WorkflowStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "default_agent": self.default_agent,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workflow:
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            default_agent=data.get("default_agent", "claude"),
            steps=steps,
        )

    def to_yaml(self) -> str:
        return yaml.dump(
            self.to_dict(), default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    @classmethod
    def from_yaml(cls, content: str) -> Workflow:
        data = yaml.safe_load(content)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Workflow:
        content = path.read_text(encoding="utf-8")
        return cls.from_yaml(content)


@dataclass
class StepResult:
    """Result of executing a single workflow step."""

    step_name: str
    success: bool
    output: str = ""
    skipped: bool = False
    error: str = ""


@dataclass
class WorkflowResult:
    """Result of executing an entire workflow."""

    workflow_name: str
    success: bool
    steps: list[StepResult] = field(default_factory=list)

    @property
    def completed_count(self) -> int:
        return sum(1 for s in self.steps if s.success and not s.skipped)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.steps if not s.success and not s.skipped)

    @property
    def skipped_count(self) -> int:
        return sum(1 for s in self.steps if s.skipped)


def resolve_variables(text: str, context: dict[str, str]) -> str:
    """Replace {var} placeholders with context values."""
    result = text
    for key, value in context.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def _evaluate_gate(condition: str, context: dict[str, str]) -> bool:
    """Evaluate a gate condition. Supports file_exists:{path} and env:{VAR}."""
    import os

    resolved = resolve_variables(condition, context)

    if resolved.startswith("file_exists:"):
        path = resolved[len("file_exists:") :]
        return Path(path).exists()

    if resolved.startswith("env:"):
        var = resolved[len("env:") :]
        return bool(os.environ.get(var))

    return bool(resolved and resolved.lower() not in ("false", "0", "no", ""))


class WorkflowRunner:
    """Executes workflow steps in sequence."""

    def __init__(
        self,
        root: Path | None = None,
        spec: str = "",
        agent: str = "",
        dry_run: bool = False,
        on_step: Any = None,
    ):
        self.root = root or Path.cwd()
        self.spec = spec
        self.agent = agent
        self.dry_run = dry_run
        self.on_step = on_step

    def _build_context(self, workflow: Workflow) -> dict[str, str]:
        agent = self.agent or workflow.default_agent
        return {
            "spec": self.spec,
            "agent": agent,
            "root": str(self.root),
        }

    def run(self, workflow: Workflow) -> WorkflowResult:
        """Execute all steps in a workflow."""
        context = self._build_context(workflow)
        result = WorkflowResult(workflow_name=workflow.name, success=True)

        for step in workflow.steps:
            step_result = self._run_step(step, context, workflow)
            result.steps.append(step_result)

            if self.on_step:
                self.on_step(step, step_result)

            if (
                not step_result.success
                and not step_result.skipped
                and step.on_failure == OnFailure.STOP
            ):
                result.success = False
                break

        return result

    def _run_step(
        self, step: WorkflowStep, context: dict[str, str], workflow: Workflow
    ) -> StepResult:
        if self.dry_run:
            return self._dry_run_step(step, context)

        handlers = {
            StepType.GATE: self._run_gate,
            StepType.KRAB: self._run_krab,
            StepType.SHELL: self._run_shell,
            StepType.PROMPT: self._run_prompt,
        }

        if step.type == StepType.AGENT:
            return self._run_agent(step, context, workflow)

        handler = handlers.get(step.type)
        if handler:
            return handler(step, context)

        return StepResult(
            step_name=step.name, success=False, error=f"Unknown step type: {step.type}"
        )

    def _dry_run_step(self, step: WorkflowStep, context: dict[str, str]) -> StepResult:
        resolved_cmd = resolve_variables(step.command, context)
        resolved_prompt = resolve_variables(step.prompt, context)
        resolved_condition = resolve_variables(step.condition, context)

        detail = ""
        if step.type == StepType.KRAB:
            detail = f"Would run: krab {resolved_cmd}"
        elif step.type == StepType.SHELL:
            detail = f"Would run: {resolved_cmd}"
        elif step.type == StepType.AGENT:
            agent = step.agent or context.get("agent", "claude")
            detail = f"Would delegate to {agent}: {resolved_prompt[:80]}..."
        elif step.type == StepType.GATE:
            detail = f"Would check: {resolved_condition}"
        elif step.type == StepType.PROMPT:
            detail = f"Would ask: {resolved_prompt}"

        return StepResult(step_name=step.name, success=True, output=f"[dry-run] {detail}")

    def _run_gate(self, step: WorkflowStep, context: dict[str, str]) -> StepResult:
        passed = _evaluate_gate(step.condition, context)
        if passed:
            return StepResult(step_name=step.name, success=True, output="Gate passed")
        return StepResult(step_name=step.name, success=False, error="Gate condition failed")

    def _run_krab(self, step: WorkflowStep, context: dict[str, str]) -> StepResult:
        resolved = resolve_variables(step.command, context)
        krab_bin = shutil.which("krab") or "krab"
        cmd = f"{krab_bin} {resolved}"
        return self._exec_shell(step.name, cmd)

    def _run_shell(self, step: WorkflowStep, context: dict[str, str]) -> StepResult:
        resolved = resolve_variables(step.command, context)
        return self._exec_shell(step.name, resolved)

    def _run_agent(
        self, step: WorkflowStep, context: dict[str, str], workflow: Workflow
    ) -> StepResult:
        from krab_cli.workflows.executor import AgentExecutor

        agent_name = step.agent or context.get("agent", workflow.default_agent)
        resolved_prompt = resolve_variables(step.prompt, context)

        executor = AgentExecutor(root=self.root, spec_path=self.spec)
        return executor.execute(agent_name, resolved_prompt, step.name)

    def _run_prompt(self, step: WorkflowStep, context: dict[str, str]) -> StepResult:
        resolved = resolve_variables(step.prompt, context)
        try:
            answer = input(f"\n  {resolved}\n  > ")
            return StepResult(step_name=step.name, success=True, output=answer.strip())
        except (EOFError, KeyboardInterrupt):
            return StepResult(step_name=step.name, success=False, error="User cancelled prompt")

    def _exec_shell(self, step_name: str, cmd: str) -> StepResult:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.root),
            )
            if proc.returncode == 0:
                return StepResult(step_name=step_name, success=True, output=proc.stdout.strip())
            return StepResult(
                step_name=step_name,
                success=False,
                error=proc.stderr.strip() or f"Exit code {proc.returncode}",
                output=proc.stdout.strip(),
            )
        except subprocess.TimeoutExpired:
            return StepResult(step_name=step_name, success=False, error="Command timed out (300s)")
        except Exception as e:
            return StepResult(step_name=step_name, success=False, error=str(e))


def get_workflows_dir(root: Path | None = None) -> Path:
    """Get the custom workflows directory (.sdd/workflows/)."""
    root = root or Path.cwd()
    return root / ".sdd" / "workflows"


def list_custom_workflows(root: Path | None = None) -> list[Path]:
    """List custom workflow YAML files."""
    wf_dir = get_workflows_dir(root)
    if not wf_dir.exists():
        return []
    return sorted(wf_dir.glob("*.yaml")) + sorted(wf_dir.glob("*.yml"))
