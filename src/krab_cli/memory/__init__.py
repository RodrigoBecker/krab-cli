"""SDD Memory — Persistent project context for spec generation.

Stores project-level information (skills, architecture decisions, conventions,
tech stack) in a `.sdd/` directory. Templates and refinement use this context
to generate specs that are consistent with the project's reality.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SDD_DIR = ".sdd"
MEMORY_FILE = "memory.json"
SKILLS_FILE = "skills.json"
HISTORY_FILE = "history.json"
SPECS_DIR = ".sdd/specs"


@dataclass
class ProjectSkill:
    """A capability or technology the project uses."""

    name: str
    category: str  # language, framework, tool, pattern, infra, service
    version: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def identifier(self) -> str:
        return f"{self.category}/{self.name}"


@dataclass
class ArchitectureDecision:
    """An architecture decision record (lightweight ADR)."""

    title: str
    status: str  # proposed, accepted, deprecated, superseded
    context: str
    decision: str
    consequences: str = ""
    date: str = ""
    supersedes: str = ""


@dataclass
class ProjectMemory:
    """Complete project memory — persisted in .sdd/memory.json."""

    project_name: str = ""
    description: str = ""
    tech_stack: dict[str, str] = field(default_factory=dict)
    architecture_style: str = ""  # monolith, microservices, hexagonal, etc
    conventions: dict[str, str] = field(default_factory=dict)
    domain_terms: dict[str, str] = field(default_factory=dict)
    team_context: dict[str, str] = field(default_factory=dict)
    integrations: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    decisions: list[ArchitectureDecision] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_context_block(self) -> str:
        """Generate a context block for spec templates."""
        parts: list[str] = []

        if self.project_name:
            parts.append(f"Project: {self.project_name}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.architecture_style:
            parts.append(f"Architecture: {self.architecture_style}")

        if self.tech_stack:
            stack_str = ", ".join(f"{k}: {v}" for k, v in self.tech_stack.items())
            parts.append(f"Stack: {stack_str}")

        if self.domain_terms:
            terms_str = ", ".join(f"{k} ({v})" for k, v in self.domain_terms.items())
            parts.append(f"Domain: {terms_str}")

        if self.constraints:
            parts.append(f"Constraints: {'; '.join(self.constraints)}")

        if self.integrations:
            parts.append(f"Integrations: {', '.join(self.integrations)}")

        return "\n".join(parts)


class MemoryStore:
    """Manages .sdd/ directory and persistence."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path.cwd()
        self.sdd_path = self.root / SDD_DIR

    @property
    def is_initialized(self) -> bool:
        return self.sdd_path.exists()

    def init(self, project_name: str = "", description: str = "") -> ProjectMemory:
        """Initialize .sdd/ directory with default memory."""
        self.sdd_path.mkdir(parents=True, exist_ok=True)

        now = datetime.now(tz=UTC).isoformat()
        memory = ProjectMemory(
            project_name=project_name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self._save_memory(memory)
        self._save_skills([])
        self._save_history([])
        return memory

    # ── Memory ────────────────────────────────────────────────────────

    def load_memory(self) -> ProjectMemory:
        """Load project memory from disk."""
        path = self.sdd_path / MEMORY_FILE
        if not path.exists():
            return ProjectMemory()

        data = json.loads(path.read_text(encoding="utf-8"))

        # Reconstruct decisions
        decisions = []
        for d in data.pop("decisions", []):
            decisions.append(ArchitectureDecision(**d))
        data["decisions"] = decisions

        return ProjectMemory(**data)

    def save_memory(self, memory: ProjectMemory) -> None:
        """Save project memory to disk."""
        memory.updated_at = datetime.now(tz=UTC).isoformat()
        self._save_memory(memory)

    def _save_memory(self, memory: ProjectMemory) -> None:
        path = self.sdd_path / MEMORY_FILE
        data = asdict(memory)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_field(self, key: str, value: str) -> ProjectMemory:
        """Set a top-level memory field."""
        memory = self.load_memory()

        # Handle nested dict fields
        if "." in key:
            parts = key.split(".", 1)
            parent = parts[0]
            child = parts[1]
            current = getattr(memory, parent, None)
            if isinstance(current, dict):
                current[child] = value
            else:
                raise ValueError(f"Field '{parent}' is not a dict, cannot set '{child}'")
        elif key == "integrations" or key == "constraints":
            current = getattr(memory, key, [])
            current.append(value)
        elif hasattr(memory, key):
            setattr(memory, key, value)
        else:
            raise ValueError(f"Unknown field: {key}")

        self.save_memory(memory)
        return memory

    # ── Skills ────────────────────────────────────────────────────────

    def load_skills(self) -> list[ProjectSkill]:
        """Load project skills from disk."""
        path = self.sdd_path / SKILLS_FILE
        if not path.exists():
            return []

        data = json.loads(path.read_text(encoding="utf-8"))
        return [ProjectSkill(**s) for s in data]

    def add_skill(self, skill: ProjectSkill) -> list[ProjectSkill]:
        """Add a skill to the project."""
        skills = self.load_skills()
        # Update if exists
        skills = [s for s in skills if s.identifier != skill.identifier]
        skills.append(skill)
        self._save_skills(skills)
        return skills

    def remove_skill(self, name: str) -> list[ProjectSkill]:
        """Remove a skill by name."""
        skills = self.load_skills()
        skills = [s for s in skills if s.name != name]
        self._save_skills(skills)
        return skills

    def _save_skills(self, skills: list[ProjectSkill]) -> None:
        path = self.sdd_path / SKILLS_FILE
        data = [asdict(s) for s in skills]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def skills_context_block(self) -> str:
        """Generate skills context for templates."""
        skills = self.load_skills()
        if not skills:
            return ""

        by_category: dict[str, list[ProjectSkill]] = {}
        for s in skills:
            by_category.setdefault(s.category, []).append(s)

        lines: list[str] = []
        for cat, items in sorted(by_category.items()):
            names = ", ".join(f"{s.name}" + (f" {s.version}" if s.version else "") for s in items)
            lines.append(f"  {cat}: {names}")

        return "\n".join(lines)

    # ── History ───────────────────────────────────────────────────────

    def load_history(self) -> list[dict]:
        """Load spec generation history."""
        path = self.sdd_path / HISTORY_FILE
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def add_history_entry(self, entry: dict) -> None:
        """Add an entry to generation history."""
        history = self.load_history()
        entry["timestamp"] = datetime.now(tz=UTC).isoformat()
        history.append(entry)
        self._save_history(history)

    def _save_history(self, history: list[dict]) -> None:
        path = self.sdd_path / HISTORY_FILE
        path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
