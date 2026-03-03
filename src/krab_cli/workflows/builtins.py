"""Built-in Workflow Definitions — Pre-defined SDD lifecycle pipelines.

Each workflow is a sequence of steps that chain krab commands, shell commands,
agent delegations, and gates together into a coherent pipeline.

Built-in workflows:
  - spec-create:  Create a new spec from template, refine, analyze, sync
  - implement:    Gate → risk check → sync agents → delegate to agent → test
  - review:       Gate → ambiguity check → agent reviews code vs spec
  - full-cycle:   Complete lifecycle from spec creation to review
  - verify:       Run all quality checks on a spec
  - agent-init:   Initialize agent instruction files from memory
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from krab_cli.workflows import OnFailure, StepType, Workflow, WorkflowStep

if TYPE_CHECKING:
    from collections.abc import Callable


def _spec_create() -> Workflow:
    """Create a new spec, refine it, analyze risk, and sync agents."""
    return Workflow(
        name="spec-create",
        description="Create a new spec from template, refine, analyze risk, and sync agents",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="create-spec",
                type=StepType.KRAB,
                command='spec new task -n "{spec}"',
            ),
            WorkflowStep(
                name="enrich-spec",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "[mode:enrich]"
                    "Leia o arquivo .sdd/specs/spec.task.{spec}.md que acabou de ser criado. "
                    "Ele contém um template com placeholders genéricos. "
                    "Reescreva o arquivo IN-PLACE substituindo TODOS os placeholders "
                    "(<!-- ... -->, <tipo de usuário>, <ação desejada>, etc.) "
                    "com conteúdo real e específico para a feature '{spec}'. "
                    "Use o contexto do projeto e a descrição da feature para gerar "
                    "cenários Gherkin concretos, critérios de aceitação reais, "
                    "e notas técnicas relevantes para a stack do projeto."
                ),
            ),
            WorkflowStep(
                name="refine-spec",
                type=StepType.KRAB,
                command="spec refine .sdd/specs/spec.task.{spec}.md",
            ),
            WorkflowStep(
                name="analyze-risk",
                type=StepType.KRAB,
                command="analyze risk .sdd/specs/spec.task.{spec}.md",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="sync-agents",
                type=StepType.KRAB,
                command="agent sync all",
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


def _implement() -> Workflow:
    """Gate on spec existence, check risk, sync agents, delegate implementation, run tests."""
    return Workflow(
        name="implement",
        description="Implement a feature from spec: gate, risk check, sync, agent delegate, test",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="check-spec-exists",
                type=StepType.GATE,
                condition="file_exists:{spec}",
            ),
            WorkflowStep(
                name="risk-check",
                type=StepType.KRAB,
                command="analyze risk {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="sync-agents",
                type=StepType.KRAB,
                command="agent sync all",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="delegate-to-agent",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "Implement the feature described in the specification. "
                    "Follow all Gherkin scenarios as acceptance criteria. "
                    "Create or update tests to match the scenarios."
                ),
            ),
            WorkflowStep(
                name="run-tests",
                type=StepType.SHELL,
                command="uv run pytest",
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


def _review() -> Workflow:
    """Gate on spec, check ambiguity, then agent reviews code against spec."""
    return Workflow(
        name="review",
        description="Review implementation against spec: gate, ambiguity check, agent review",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="check-spec-exists",
                type=StepType.GATE,
                condition="file_exists:{spec}",
            ),
            WorkflowStep(
                name="ambiguity-check",
                type=StepType.KRAB,
                command="analyze ambiguity {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="agent-review",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "Review the current implementation against the specification. "
                    "Check that all Gherkin scenarios are covered by tests. "
                    "Identify any deviations, missing edge cases, or spec violations. "
                    "Report findings as a structured review."
                ),
            ),
        ],
    )


def _full_cycle() -> Workflow:
    """Complete SDD lifecycle: create spec, refine, analyze, optimize, sync, implement, test, review."""
    return Workflow(
        name="full-cycle",
        description="Complete SDD lifecycle from spec creation through implementation and review",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="create-spec",
                type=StepType.KRAB,
                command='spec new task -n "{spec}"',
            ),
            WorkflowStep(
                name="enrich-spec",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "[mode:enrich]"
                    "Leia o arquivo .sdd/specs/spec.task.{spec}.md que acabou de ser criado. "
                    "Ele contém um template com placeholders genéricos. "
                    "Reescreva o arquivo IN-PLACE substituindo TODOS os placeholders "
                    "(<!-- ... -->, <tipo de usuário>, <ação desejada>, etc.) "
                    "com conteúdo real e específico para a feature '{spec}'. "
                    "Use o contexto do projeto e a descrição da feature para gerar "
                    "cenários Gherkin concretos, critérios de aceitação reais, "
                    "e notas técnicas relevantes para a stack do projeto."
                ),
            ),
            WorkflowStep(
                name="refine-spec",
                type=StepType.KRAB,
                command="spec refine .sdd/specs/spec.task.{spec}.md",
            ),
            WorkflowStep(
                name="risk-analysis",
                type=StepType.KRAB,
                command="analyze risk .sdd/specs/spec.task.{spec}.md",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="optimize-spec",
                type=StepType.KRAB,
                command="optimize run .sdd/specs/spec.task.{spec}.md",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="sync-agents",
                type=StepType.KRAB,
                command="agent sync all",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="implement",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "Implement the feature described in the specification. "
                    "Follow all Gherkin scenarios as acceptance criteria. "
                    "Create or update tests to match the scenarios."
                ),
            ),
            WorkflowStep(
                name="run-tests",
                type=StepType.SHELL,
                command="uv run pytest",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="review",
                type=StepType.AGENT,
                agent="{agent}",
                prompt=(
                    "Review the implementation against the specification. "
                    "Verify all Gherkin scenarios are covered. "
                    "Report any deviations or missing edge cases."
                ),
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


def _verify() -> Workflow:
    """Run all quality analysis checks on a spec file."""
    return Workflow(
        name="verify",
        description="Run all quality checks on a spec: risk, ambiguity, readability, entropy, refine",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="check-spec-exists",
                type=StepType.GATE,
                condition="file_exists:{spec}",
            ),
            WorkflowStep(
                name="risk-analysis",
                type=StepType.KRAB,
                command="analyze risk {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="ambiguity-check",
                type=StepType.KRAB,
                command="analyze ambiguity {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="readability-check",
                type=StepType.KRAB,
                command="analyze readability {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="entropy-analysis",
                type=StepType.KRAB,
                command="analyze entropy {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
            WorkflowStep(
                name="generate-refinement",
                type=StepType.KRAB,
                command="spec refine {spec}",
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


def _agent_init() -> Workflow:
    """Initialize agent instruction files from project memory."""
    return Workflow(
        name="agent-init",
        description="Initialize agent instruction files: check memory, sync all, show status",
        default_agent="claude",
        steps=[
            WorkflowStep(
                name="check-memory",
                type=StepType.GATE,
                condition="file_exists:{root}/.sdd/memory.json",
            ),
            WorkflowStep(
                name="sync-all-agents",
                type=StepType.KRAB,
                command="agent sync all",
            ),
            WorkflowStep(
                name="show-status",
                type=StepType.KRAB,
                command="agent status",
                on_failure=OnFailure.CONTINUE,
            ),
        ],
    )


# ─── Registry ────────────────────────────────────────────────────────────

_BUILTIN_FACTORIES: dict[str, Callable[[], Workflow]] = {
    "spec-create": _spec_create,
    "implement": _implement,
    "review": _review,
    "full-cycle": _full_cycle,
    "verify": _verify,
    "agent-init": _agent_init,
}


def get_builtin(name: str) -> Workflow:
    """Get a built-in workflow by name."""
    factory = _BUILTIN_FACTORIES.get(name)
    if not factory:
        available = ", ".join(sorted(_BUILTIN_FACTORIES.keys()))
        raise ValueError(f"Unknown built-in workflow: '{name}'. Available: {available}")
    return factory()


def list_builtins() -> list[dict[str, str | int]]:
    """List all built-in workflows with metadata."""
    results = []
    for _name, factory in _BUILTIN_FACTORIES.items():
        wf = factory()
        results.append(
            {
                "name": wf.name,
                "description": wf.description,
                "steps": len(wf.steps),
                "default_agent": wf.default_agent,
            }
        )
    return results


def get_all_builtins() -> dict[str, Workflow]:
    """Get all built-in workflows as a dict."""
    return {name: factory() for name, factory in _BUILTIN_FACTORIES.items()}
