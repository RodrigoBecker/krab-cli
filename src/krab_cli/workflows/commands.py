"""Slash Command Generator — Transforms krab workflows into native agent commands.

Generates native slash command files for each AI coding agent:
  - Claude Code:  .claude/commands/*.md  (/project:krab-implement, /project:krab-spec, etc.)
  - Copilot:      .github/agents/*.agent.md (@krab)
                  .github/prompts/*.prompt.md (/krab-implement)
                  .github/skills/*/SKILL.md (auto-loaded)
  - Cross-agent:  .github/skills/*/SKILL.md (Agent Skills standard)

Also generates CLI-to-slash-command mappings so all krab commands are
accessible natively within each agent's interface.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from krab_cli.workflows import Workflow, WorkflowStep


# ─── Helpers ─────────────────────────────────────────────────────────────


def _build_context_block(root: Path) -> str:
    """Load project memory and return a markdown context block."""
    try:
        from krab_cli.memory import MemoryStore

        store = MemoryStore(root=root)
        if not store.is_initialized:
            return ""
        memory = store.load_memory()
        lines: list[str] = []
        if memory.project_name:
            lines.append(f"- **Project**: {memory.project_name}")
        if memory.description:
            lines.append(f"- **Description**: {memory.description}")
        if memory.architecture_style:
            lines.append(f"- **Architecture**: {memory.architecture_style}")
        if memory.tech_stack:
            stack = ", ".join(f"{k}: {v}" for k, v in memory.tech_stack.items())
            lines.append(f"- **Tech stack**: {stack}")
        if memory.conventions:
            convs = "; ".join(f"{k}: {v}" for k, v in memory.conventions.items())
            lines.append(f"- **Conventions**: {convs}")
        if memory.constraints:
            lines.append(f"- **Constraints**: {'; '.join(memory.constraints)}")
        if not lines:
            return ""
        return "## Project Context\n\n" + "\n".join(lines) + "\n"
    except Exception:
        return ""


def _parse_agent_prompt(raw_prompt: str) -> tuple[str, str]:
    """Parse an agent step prompt, extracting mode prefix if present.

    Returns (mode, clean_prompt) where mode is "implement" by default
    or the value from a ``[mode:<value>]`` prefix.
    """
    mode = "implement"
    prompt = raw_prompt
    if prompt.startswith("[mode:"):
        end = prompt.index("]")
        mode = prompt[6:end]
        prompt = prompt[end + 1:].strip()
    return mode, prompt


def _agent_step_to_markdown(
    index: int,
    step: WorkflowStep,
) -> list[str]:
    """Render an agent step as detailed markdown instructions.

    Instead of truncating the prompt to 80 chars, this emits:
    - A summary line identifying the agent and mode
    - The full task prompt so the AI agent has complete instructions
    - Mode-specific guidance (e.g. enrich → rewrite rules)
    """
    mode, clean_prompt = _parse_agent_prompt(step.prompt)
    agent_label = step.agent or "default"
    lines: list[str] = []

    if mode == "enrich":
        lines.append(
            f"{index}. **Agent** ({agent_label}) — **Enrich spec** (rewrite in-place):"
        )
        lines.append(f"   > {clean_prompt}")
        lines.append("")
        lines.append("   **Enrich rules for the agent:**")
        lines.append("   - Read the spec file indicated above")
        lines.append(
            "   - Rewrite the file **IN-PLACE**, keeping the heading structure"
        )
        lines.append(
            "   - Replace **ALL** placeholders "
            "(`<!-- ... -->`, `<tipo de usuário>`, `<ação desejada>`, etc.) "
            "with real, specific content"
        )
        lines.append(
            "   - Use the project context (tech_stack, conventions) "
            "to generate relevant content"
        )
        lines.append(
            "   - Write concrete Gherkin scenarios for the described feature"
        )
        lines.append(
            "   - Generate real acceptance criteria and relevant technical notes"
        )
        lines.append("   - Write in **pt-BR**")
    else:
        lines.append(f"{index}. **Agent** ({agent_label}) — **{mode.capitalize()}**:")
        lines.append(f"   > {clean_prompt}")
        lines.append("")
        lines.append("   **Instructions for the agent:**")
        lines.append("   - Follow the specification above precisely")
        lines.append("   - Implement all Gherkin scenarios as tests")
        lines.append("   - Respect project conventions and constraints")
        lines.append(
            "   - Run existing tests after changes to verify nothing breaks"
        )

    return lines


def _workflow_to_steps_markdown(wf: Workflow) -> str:
    """Convert workflow steps into numbered markdown instructions.

    Agent steps are expanded with their full prompt and mode-specific
    instructions so that external AI agents (Copilot, Claude Code) have
    all the context they need to execute the task.
    """
    lines: list[str] = []
    for i, step in enumerate(wf.steps, 1):
        step_type = step.type.value
        if step_type == "gate":
            lines.append(f"{i}. **Gate**: Check condition `{step.condition}`")
        elif step_type == "krab":
            lines.append(f"{i}. **Run**: `krab {step.command}`")
        elif step_type == "shell":
            lines.append(f"{i}. **Shell**: `{step.command}`")
        elif step_type == "agent":
            lines.extend(_agent_step_to_markdown(i, step))
        elif step_type == "prompt":
            lines.append(f"{i}. **Prompt user**: {step.prompt}")
        else:
            lines.append(f"{i}. **{step_type}**: {step.command or step.prompt or step.condition}")

        if step.on_failure.value == "continue":
            lines.append("   - On failure: continue to next step")
    return "\n".join(lines)


def _extract_krab_commands(wf: Workflow) -> list[str]:
    """Extract krab CLI commands from workflow steps."""
    cmds: list[str] = []
    for step in wf.steps:
        if step.type.value == "krab" and step.command:
            cmds.append(f"krab {step.command}")
    return cmds


# ─── Claude Code Generator ──────────────────────────────────────────────


def _claude_router(workflows: list[Workflow], root: Path) -> str:
    """Generate the /project:krab router command content."""
    ctx = _build_context_block(root)

    wf_list = "\n".join(
        f"- **{wf.name}**: {wf.description} ({len(wf.steps)} steps)" for wf in workflows
    )

    return f"""---
description: "Krab SDD workflow router \u2014 run any krab workflow by name"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

{ctx}## Available Workflows

{wf_list}

## Instructions

1. Parse `$ARGUMENTS` to identify the workflow name and optional spec file path.
   - Example: `implement spec.task.auth.md` \u2192 workflow=implement, spec=spec.task.auth.md
   - Example: `verify spec.task.auth.md` \u2192 workflow=verify, spec=spec.task.auth.md
   - If only a workflow name is given, ask for the spec file.

2. Execute the workflow by running `krab workflow run <name> --spec <spec>` in the terminal.
   - If the workflow includes agent steps, you ARE the agent \u2014 execute those tasks directly.
   - For krab/shell steps, run the commands in the terminal.
   - For gate steps, check the condition and proceed or stop.

3. If the spec file contains Gherkin scenarios (Given/When/Then), treat them as acceptance criteria.

4. After completing all steps, provide a summary of what was done.

**Tip**: Use `/project:krab-implement`, `/project:krab-review`, etc. for direct access to specific workflows.
"""


def _claude_workflow_command(wf: Workflow, root: Path) -> str:
    """Generate a per-workflow Claude Code command."""
    ctx = _build_context_block(root)
    steps = _workflow_to_steps_markdown(wf)
    krab_cmds = _extract_krab_commands(wf)

    cmds_section = ""
    if krab_cmds:
        cmds_list = "\n".join(f"- `{c}`" for c in krab_cmds)
        cmds_section = f"\n## Krab Commands\n\nRun these in the terminal:\n\n{cmds_list}\n"

    return f"""---
description: "Krab workflow: {wf.name} \u2014 {wf.description}"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
If `$ARGUMENTS` contains a file path, use it as the spec file.

{ctx}## Workflow: {wf.name}

{wf.description}

## Steps

{steps}
{cmds_section}
## Execution Rules

- For **krab** and **shell** steps: run the command in the terminal.
- For **agent** steps: you ARE the agent \u2014 execute the task directly using your tools.
- For **gate** steps: check the condition (e.g., file existence) and stop if it fails.
- Steps with "on failure: continue" should not block the pipeline.
- If the spec contains Gherkin scenarios (Given/When/Then), treat them as acceptance criteria.
- After completion, summarize what was done and any issues encountered.
"""


def generate_claude_commands(
    workflows: list[Workflow],
    root: Path,
) -> list[tuple[Path, str]]:
    """Generate Claude Code command files (.claude/commands/*.md)."""
    commands_dir = root / ".claude" / "commands"
    files: list[tuple[Path, str]] = []

    # Router command
    files.append((commands_dir / "krab.md", _claude_router(workflows, root)))

    # Per-workflow commands
    for wf in workflows:
        filename = f"krab-{wf.name}.md"
        files.append((commands_dir / filename, _claude_workflow_command(wf, root)))

    return files


# ─── Copilot Generator ──────────────────────────────────────────────────


def _copilot_agent(workflows: list[Workflow], root: Path) -> str:
    """Generate the @krab custom agent for Copilot."""
    ctx = _build_context_block(root)

    wf_descriptions = "\n".join(f"- **{wf.name}**: {wf.description}" for wf in workflows)

    all_krab_cmds: list[str] = []
    for wf in workflows:
        all_krab_cmds.extend(_extract_krab_commands(wf))
    unique_cmds = sorted(set(all_krab_cmds))
    cmds_block = "\n".join(f"- `{c}`" for c in unique_cmds) if unique_cmds else "- (none)"

    return f"""---
description: "Krab SDD assistant \u2014 executes spec-driven development workflows including spec creation, analysis, implementation, and review."
tools: ['read', 'search', 'edit', 'execute']
---

You are the **Krab** assistant, an AI agent specialized in Spec-Driven Development (SDD).

{ctx}## Capabilities

You know how to execute these krab workflows:

{wf_descriptions}

## Krab CLI Commands

Use the terminal to run these krab commands:

{cmds_block}

## How to Work

1. When the user describes a task, identify which workflow applies.
2. If a spec file is referenced, read it first to understand the requirements.
3. Execute krab CLI commands in the terminal for analysis/optimization steps.
4. For implementation and review steps, use your own tools (read, edit, search) directly.
5. If the spec contains Gherkin scenarios (Given/When/Then), treat them as acceptance criteria.
6. After completing a workflow, summarize what was done.

## Workflow Execution

For each workflow step:
- **gate**: Check the condition (e.g., file existence). Stop if it fails.
- **krab**: Run `krab <command>` in the terminal.
- **shell**: Run the shell command in the terminal.
- **agent**: Execute the task directly using your tools.
- Steps with `on_failure: continue` should not block the pipeline.
"""


def _copilot_prompt(wf: Workflow, root: Path) -> str:
    """Generate a Copilot prompt file (.github/prompts/*.prompt.md)."""
    ctx = _build_context_block(root)
    steps = _workflow_to_steps_markdown(wf)
    krab_cmds = _extract_krab_commands(wf)

    cmds_block = ""
    if krab_cmds:
        cmds_list = "\n".join(f"- `{c}`" for c in krab_cmds)
        cmds_block = f"\nRun in terminal:\n\n{cmds_list}\n"

    return f"""---
agent: 'agent'
description: "Krab workflow: {wf.name} \u2014 {wf.description}"
---

Spec file: ${{input:spec:Path to spec file (e.g. spec.task.auth.md)}}

{ctx}## Workflow: {wf.name}

{wf.description}

## Steps

{steps}
{cmds_block}
## Rules

- Run krab/shell commands in the terminal.
- For agent steps, execute the task directly.
- For gate steps, check the condition and stop if it fails.
- If the spec contains Gherkin scenarios, treat them as acceptance criteria.
"""


def _copilot_skill(wf: Workflow, _root: Path) -> str:
    """Generate a Copilot/cross-agent skill (SKILL.md)."""
    steps = _workflow_to_steps_markdown(wf)
    krab_cmds = _extract_krab_commands(wf)

    cmds_block = ""
    if krab_cmds:
        cmds_list = "\n".join(f"- `{c}`" for c in krab_cmds)
        cmds_block = f"\nKrab CLI commands to run:\n\n{cmds_list}\n"

    return f"""---
name: krab-{wf.name}
description: "{wf.description}"
---

## Workflow: {wf.name}

{steps}
{cmds_block}
Execute krab and shell commands in the terminal. For agent steps, perform the task directly.
If the spec contains Gherkin scenarios (Given/When/Then), treat them as acceptance criteria.
"""


def generate_copilot_files(
    workflows: list[Workflow],
    root: Path,
) -> list[tuple[Path, str]]:
    """Generate all Copilot files: agent, prompts, and skills."""
    files: list[tuple[Path, str]] = []

    # @krab custom agent
    agent_dir = root / ".github" / "agents"
    files.append((agent_dir / "krab.agent.md", _copilot_agent(workflows, root)))

    for wf in workflows:
        # Prompt files (/krab-{name} in chat)
        prompts_dir = root / ".github" / "prompts"
        files.append(
            (
                prompts_dir / f"krab-{wf.name}.prompt.md",
                _copilot_prompt(wf, root),
            )
        )

        # Skills (auto-loaded contextually)
        skills_dir = root / ".github" / "skills" / f"krab-{wf.name}"
        files.append((skills_dir / "SKILL.md", _copilot_skill(wf, root)))

    return files


# ─── Cross-Agent Skills ─────────────────────────────────────────────────


def generate_cross_agent_skills(
    workflows: list[Workflow],
    root: Path,
) -> list[tuple[Path, str]]:
    """Generate cross-agent skills in .github/skills/ (Agent Skills standard)."""
    files: list[tuple[Path, str]] = []
    for wf in workflows:
        skills_dir = root / ".github" / "skills" / f"krab-{wf.name}"
        files.append((skills_dir / "SKILL.md", _copilot_skill(wf, root)))
    return files


# ─── CLI-to-Slash Command Mappings ──────────────────────────────────────

# All krab CLI commands that should be exposed as slash commands
_CLI_COMMANDS: list[dict[str, str]] = [
    {
        "name": "spec-new",
        "cli": "krab spec new {type} -n {name}",
        "description": "Create a new spec from template (task, architecture, plan, constitution, guardrails, runbook, clarify)",
        "prompt_hint": "Template type and spec name (e.g. 'task user-auth')",
    },
    {
        "name": "spec-refine",
        "cli": "krab spec refine {spec}",
        "description": "Analyze a spec with Tree-of-Thought and generate refinement plan",
        "prompt_hint": "Path to spec file",
    },
    {
        "name": "spec-clarify",
        "cli": "krab spec clarify {spec}",
        "description": "Interactive Q&A to enrich and clarify a spec",
        "prompt_hint": "Path to spec file",
    },
    {
        "name": "spec-import",
        "cli": "krab spec import {source}",
        "description": "Import specs from a remote Git repository",
        "prompt_hint": "Git repo URL or registry alias",
    },
    {
        "name": "spec-archive",
        "cli": "krab spec archive {specs}",
        "description": "Archive specs by moving them to .sdd/archived/",
        "prompt_hint": "Spec file paths or names to archive (e.g. 'spec.task.user-auth.md')",
    },
    {
        "name": "spec-delete",
        "cli": "krab spec delete {specs}",
        "description": "Delete one or more spec files permanently",
        "prompt_hint": "Spec file paths or names to delete (e.g. 'spec.task.old-feature.md')",
    },
    {
        "name": "analyze-risk",
        "cli": "krab analyze risk {spec}",
        "description": "Assess hallucination risk score for a spec",
        "prompt_hint": "Path to spec file",
    },
    {
        "name": "analyze-ambiguity",
        "cli": "krab analyze ambiguity {spec}",
        "description": "Detect vague/ambiguous terms that increase hallucination risk",
        "prompt_hint": "Path to spec file",
    },
    {
        "name": "optimize",
        "cli": "krab optimize run {spec}",
        "description": "Optimize a spec for token efficiency",
        "prompt_hint": "Path to spec file",
    },
    {
        "name": "memory-show",
        "cli": "krab memory show",
        "description": "Show current project memory (stack, conventions, etc.)",
        "prompt_hint": "",
    },
    {
        "name": "memory-set",
        "cli": "krab memory set {key} {value}",
        "description": "Set a memory field (e.g. tech_stack.backend, conventions.naming)",
        "prompt_hint": "Key and value (e.g. 'tech_stack.backend Python')",
    },
    {
        "name": "agent-sync",
        "cli": "krab agent sync {target}",
        "description": "Generate instruction files for AI agents (all, claude, copilot, codex)",
        "prompt_hint": "Target agent (all, claude, copilot, codex)",
    },
    {
        "name": "workflow-run",
        "cli": "krab workflow run {name} --spec {spec}",
        "description": "Execute a workflow pipeline (sdd-lifecycle, spec-create, implement, review)",
        "prompt_hint": "Workflow name and spec (e.g. 'sdd-lifecycle user-auth')",
    },
]


def _generate_cli_slash_command_claude(cmd: dict[str, str], root: Path) -> str:
    """Generate a Claude Code slash command for a krab CLI command."""
    ctx = _build_context_block(root)

    prompt_section = ""
    if cmd["prompt_hint"]:
        prompt_section = f"""
## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Parse `$ARGUMENTS` to extract: {cmd['prompt_hint']}
"""
    else:
        prompt_section = """
## User Input

```text
$ARGUMENTS
```
"""

    return f"""---
description: "Krab CLI: {cmd['description']}"
---
{prompt_section}
{ctx}## Command

Run this krab CLI command in the terminal:

```bash
{cmd['cli']}
```

## Instructions

1. Parse `$ARGUMENTS` to fill in the command parameters.
2. Run the krab command in the terminal.
3. Read and interpret the output.
4. If the command generates a spec file, read it and offer to enrich it with project context.
5. If the command shows analysis results, summarize findings and suggest improvements.
6. For spec creation commands, after creating the spec, offer to run `krab spec clarify` to enrich it.
"""


def _generate_cli_slash_command_copilot(cmd: dict[str, str], root: Path) -> str:
    """Generate a Copilot prompt for a krab CLI command."""
    ctx = _build_context_block(root)

    input_var = ""
    if cmd["prompt_hint"]:
        input_var = f"\nInput: ${{input:args:{cmd['prompt_hint']}}}\n"

    return f"""---
agent: 'agent'
description: "Krab CLI: {cmd['description']}"
---
{input_var}
{ctx}## Command

Run this command in the terminal:

```bash
{cmd['cli']}
```

## Instructions

1. Fill in command parameters from user input.
2. Run the command in the terminal.
3. Interpret the output and summarize results.
4. Suggest next steps based on the output.
"""


def generate_cli_commands_claude(root: Path) -> list[tuple[Path, str]]:
    """Generate Claude Code slash commands for all krab CLI commands."""
    commands_dir = root / ".claude" / "commands"
    files: list[tuple[Path, str]] = []

    for cmd in _CLI_COMMANDS:
        filename = f"krab-{cmd['name']}.md"
        content = _generate_cli_slash_command_claude(cmd, root)
        files.append((commands_dir / filename, content))

    return files


def generate_cli_commands_copilot(root: Path) -> list[tuple[Path, str]]:
    """Generate Copilot prompt files for all krab CLI commands."""
    prompts_dir = root / ".github" / "prompts"
    files: list[tuple[Path, str]] = []

    for cmd in _CLI_COMMANDS:
        filename = f"krab-{cmd['name']}.prompt.md"
        content = _generate_cli_slash_command_copilot(cmd, root)
        files.append((prompts_dir / filename, content))

    return files


# ─── Public API ──────────────────────────────────────────────────────────


def generate_all(
    root: Path | None = None,
    agent: str | None = None,
    workflow: str | None = None,
) -> dict[str, list[Path]]:
    """Generate native slash commands for all (or filtered) agents and workflows.

    Returns a dict of agent_name -> list of written file paths.
    Also generates CLI-to-slash-command mappings for each agent.
    """
    root = root or Path.cwd()
    workflows = _get_workflows(workflow)

    results: dict[str, list[Path]] = {}

    generators = {
        "claude": generate_claude_commands,
        "copilot": generate_copilot_files,
    }

    # CLI command generators (per agent)
    cli_generators = {
        "claude": generate_cli_commands_claude,
        "copilot": generate_cli_commands_copilot,
    }

    # Filter by agent if specified
    if agent:
        if agent not in generators:
            available = ", ".join(sorted(generators.keys()))
            msg = f"Unknown agent: '{agent}'. Available: {available}"
            raise ValueError(msg)
        generators = {agent: generators[agent]}
        cli_generators = {k: v for k, v in cli_generators.items() if k == agent}

    for agent_name, gen_fn in generators.items():
        files = gen_fn(workflows, root)
        written: list[Path] = []
        for path, content in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)

        # Also generate CLI slash commands
        cli_gen = cli_generators.get(agent_name)
        if cli_gen:
            cli_files = cli_gen(root)
            for path, content in cli_files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                written.append(path)

        results[agent_name] = written

    return results


def preview(
    root: Path | None = None,
    agent: str | None = None,
    workflow: str | None = None,
) -> dict[str, list[tuple[Path, str]]]:
    """Preview what would be generated without writing files.

    Returns a dict of agent_name -> list of (path, content) tuples.
    """
    root = root or Path.cwd()
    workflows = _get_workflows(workflow)

    results: dict[str, list[tuple[Path, str]]] = {}

    generators = {
        "claude": generate_claude_commands,
        "copilot": generate_copilot_files,
    }

    if agent:
        if agent not in generators:
            available = ", ".join(sorted(generators.keys()))
            msg = f"Unknown agent: '{agent}'. Available: {available}"
            raise ValueError(msg)
        generators = {agent: generators[agent]}

    for agent_name, gen_fn in generators.items():
        results[agent_name] = gen_fn(workflows, root)

    return results


def clean(root: Path | None = None) -> list[Path]:
    """Remove all generated krab command files."""
    root = root or Path.cwd()
    removed: list[Path] = []

    # Claude commands
    claude_dir = root / ".claude" / "commands"
    if claude_dir.exists():
        for f in claude_dir.glob("krab*.md"):
            f.unlink()
            removed.append(f)

    # Copilot agent
    agent_file = root / ".github" / "agents" / "krab.agent.md"
    if agent_file.exists():
        agent_file.unlink()
        removed.append(agent_file)

    # Copilot prompts
    prompts_dir = root / ".github" / "prompts"
    if prompts_dir.exists():
        for f in prompts_dir.glob("krab-*.prompt.md"):
            f.unlink()
            removed.append(f)

    # Skills (both .github/skills/ and .agents/skills/)
    for skills_root in [root / ".github" / "skills", root / ".agents" / "skills"]:
        if skills_root.exists():
            for skill_dir in skills_root.glob("krab-*"):
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skill_file.unlink()
                        removed.append(skill_file)
                    # Remove empty dir
                    if not any(skill_dir.iterdir()):
                        skill_dir.rmdir()

    return removed


# ─── Internal ────────────────────────────────────────────────────────────


def _get_workflows(workflow: str | None = None) -> list[Workflow]:
    """Load built-in + custom workflows, optionally filtered by name."""
    from krab_cli.workflows import Workflow as WfClass
    from krab_cli.workflows import list_custom_workflows
    from krab_cli.workflows.builtins import get_all_builtins, get_builtin

    if workflow:
        # Try built-in first
        try:
            return [get_builtin(workflow)]
        except ValueError:
            pass
        # Try custom
        for path in list_custom_workflows():
            if path.stem == workflow:
                return [WfClass.load(path)]
        msg = f"Workflow not found: '{workflow}'"
        raise ValueError(msg)

    # All workflows
    wfs = list(get_all_builtins().values())
    for path in list_custom_workflows():
        with contextlib.suppress(Exception):
            wfs.append(WfClass.load(path))
    return wfs
