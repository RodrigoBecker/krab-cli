"""Agent Executor — Wraps Claude Code, Codex, and Copilot CLIs.

Builds structured prompts from spec content + project memory, then
delegates execution to the appropriate agent's CLI tool.

Agent commands:
  - Claude Code: claude -p "<prompt>"
  - Codex:       codex exec "<prompt>"
  - Copilot:     gh issue create --body "<prompt>" --label copilot
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from krab_cli.workflows import StepResult


@dataclass
class AgentInfo:
    """Metadata about a supported agent."""

    name: str
    cli_command: str
    check_command: str
    description: str


# ─── Supported agents ────────────────────────────────────────────────────

AGENTS: dict[str, AgentInfo] = {
    "claude": AgentInfo(
        name="Claude Code",
        cli_command="claude",
        check_command="claude --version",
        description="Anthropic's Claude Code CLI — interactive coding agent",
    ),
    "codex": AgentInfo(
        name="OpenAI Codex CLI",
        cli_command="codex",
        check_command="codex --version",
        description="OpenAI Codex CLI — autonomous coding agent",
    ),
    "copilot": AgentInfo(
        name="GitHub Copilot",
        cli_command="gh",
        check_command="gh --version",
        description="GitHub Copilot — delegates via gh issue with copilot label",
    ),
}


def check_agent_available(agent_name: str) -> bool:
    """Check if an agent's CLI tool is installed and accessible."""
    info = AGENTS.get(agent_name)
    if not info:
        return False
    return shutil.which(info.cli_command) is not None


def list_agents() -> list[dict[str, object]]:
    """List all supported agents with availability status."""
    results = []
    for key, info in AGENTS.items():
        results.append(
            {
                "key": key,
                "name": info.name,
                "command": info.cli_command,
                "available": check_agent_available(key),
                "description": info.description,
            }
        )
    return results


# ─── Prompt Builder ──────────────────────────────────────────────────────


def build_agent_prompt(
    task_prompt: str,
    spec_path: str = "",
    root: Path | None = None,
    mode: str = "implement",
) -> str:
    """Build a structured prompt for an agent from spec + memory context.

    The prompt includes:
    - Project context from .sdd/memory.json (if available)
    - Spec file content (if spec_path points to a real file)
    - The task-specific prompt from the workflow step

    Args:
        mode: "implement" (default) for implementation instructions,
              "enrich" for spec rewrite instructions.
    """
    root = root or Path.cwd()
    sections: list[str] = []

    # 1. Project context from memory
    try:
        from krab_cli.memory import MemoryStore

        store = MemoryStore(root=root)
        if store.is_initialized:
            memory = store.load_memory()
            ctx_lines: list[str] = []

            if memory.project_name:
                ctx_lines.append(f"Project: {memory.project_name}")
            if memory.description:
                ctx_lines.append(f"Description: {memory.description}")
            if memory.architecture_style:
                ctx_lines.append(f"Architecture: {memory.architecture_style}")
            if memory.tech_stack:
                stack = ", ".join(f"{k}: {v}" for k, v in memory.tech_stack.items())
                ctx_lines.append(f"Tech stack: {stack}")
            if memory.conventions:
                convs = "; ".join(f"{k}: {v}" for k, v in memory.conventions.items())
                ctx_lines.append(f"Conventions: {convs}")
            if memory.constraints:
                ctx_lines.append(f"Constraints: {'; '.join(memory.constraints)}")

            if ctx_lines:
                sections.append("## Project Context\n" + "\n".join(ctx_lines))
    except Exception:
        pass  # Memory not available; continue without context

    # 2. Spec file content
    if spec_path:
        spec_file = Path(spec_path)
        if not spec_file.is_absolute():
            spec_file = root / spec_file
        if spec_file.exists() and spec_file.is_file():
            content = spec_file.read_text(encoding="utf-8")
            sections.append(f"## Specification ({spec_file.name})\n\n{content}")

    # 3. Task prompt
    if task_prompt:
        sections.append(f"## Task\n\n{task_prompt}")

    # 4. Instructions (mode-dependent)
    if mode == "enrich":
        sections.append(
            "## Instructions\n\n"
            "- Leia o arquivo spec indicado acima\n"
            "- Reescreva o arquivo IN-PLACE mantendo a estrutura de headings\n"
            "- Substitua TODOS os placeholders (<!-- ... -->, <tipo de usuário>, "
            "<ação desejada>, etc.) por conteúdo real e específico\n"
            "- Use o contexto do projeto (tech_stack, conventions) para gerar "
            "conteúdo relevante\n"
            "- Escreva cenários Gherkin concretos para a feature descrita\n"
            "- Gere critérios de aceitação reais e notas técnicas relevantes\n"
            "- Escreva em pt-BR"
        )
    else:
        sections.append(
            "## Instructions\n\n"
            "- Follow the specification above precisely\n"
            "- Implement all Gherkin scenarios as tests\n"
            "- Respect project conventions and constraints\n"
            "- Run existing tests after changes to verify nothing breaks"
        )

    return "\n\n".join(sections)


# ─── Agent Executor ──────────────────────────────────────────────────────


class AgentExecutor:
    """Execute tasks by delegating to external AI agent CLIs."""

    def __init__(
        self,
        root: Path | None = None,
        spec_path: str = "",
        timeout: int = 600,
    ):
        self.root = root or Path.cwd()
        self.spec_path = spec_path
        self.timeout = timeout

    def execute(
        self,
        agent_name: str,
        task_prompt: str,
        step_name: str = "agent",
        mode: str = "implement",
    ) -> StepResult:
        """Execute a task with the specified agent."""
        if agent_name not in AGENTS:
            available = ", ".join(sorted(AGENTS.keys()))
            return StepResult(
                step_name=step_name,
                success=False,
                error=f"Unknown agent: '{agent_name}'. Available: {available}",
            )

        if not check_agent_available(agent_name):
            info = AGENTS[agent_name]
            return StepResult(
                step_name=step_name,
                success=False,
                error=(
                    f"Agent '{info.name}' not found. "
                    f"Install it first: {info.cli_command} must be in PATH."
                ),
            )

        prompt = build_agent_prompt(
            task_prompt=task_prompt,
            spec_path=self.spec_path,
            root=self.root,
            mode=mode,
        )

        dispatch = {
            "claude": self._exec_claude,
            "codex": self._exec_codex,
            "copilot": self._exec_copilot,
        }

        handler = dispatch.get(agent_name)
        if handler:
            return handler(prompt, step_name)

        return StepResult(
            step_name=step_name,
            success=False,
            error=f"No executor implemented for agent: {agent_name}",
        )

    def _exec_claude(self, prompt: str, step_name: str) -> StepResult:
        """Execute via Claude Code CLI: claude -p '<prompt>'."""
        claude_bin = shutil.which("claude") or "claude"
        cmd = [claude_bin, "-p", prompt]
        return self._run_subprocess(cmd, step_name)

    def _exec_codex(self, prompt: str, step_name: str) -> StepResult:
        """Execute via Codex CLI: codex exec '<prompt>'."""
        codex_bin = shutil.which("codex") or "codex"
        cmd = [codex_bin, "exec", prompt]
        return self._run_subprocess(cmd, step_name)

    def _exec_copilot(self, prompt: str, step_name: str) -> StepResult:
        """Execute via GitHub CLI: gh issue create with copilot label."""
        gh_bin = shutil.which("gh") or "gh"
        title = prompt.split("\n")[0][:80] if prompt else "Copilot task"
        cmd = [
            gh_bin,
            "issue",
            "create",
            "--title",
            title,
            "--body",
            prompt,
            "--label",
            "copilot",
        ]
        return self._run_subprocess(cmd, step_name)

    def _run_subprocess(self, cmd: list[str], step_name: str) -> StepResult:
        """Run a subprocess and return a StepResult."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.root),
            )
            if proc.returncode == 0:
                return StepResult(
                    step_name=step_name,
                    success=True,
                    output=proc.stdout.strip(),
                )
            return StepResult(
                step_name=step_name,
                success=False,
                error=proc.stderr.strip() or f"Exit code {proc.returncode}",
                output=proc.stdout.strip(),
            )
        except subprocess.TimeoutExpired:
            return StepResult(
                step_name=step_name,
                success=False,
                error=f"Agent timed out ({self.timeout}s)",
            )
        except FileNotFoundError as e:
            return StepResult(
                step_name=step_name,
                success=False,
                error=f"Agent CLI not found: {e}",
            )
        except Exception as e:
            return StepResult(
                step_name=step_name,
                success=False,
                error=str(e),
            )
