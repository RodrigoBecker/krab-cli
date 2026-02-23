"""Delta encoding for spec version management.

Computes minimal diffs between spec versions, enabling agents to receive
only the changes rather than the full spec on each iteration.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import StrEnum


class ChangeType(StrEnum):
    """Types of changes between spec versions."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    UNCHANGED = "unchanged"


@dataclass
class DeltaChange:
    """A single change between two spec versions."""

    change_type: ChangeType
    section: str
    old_content: str = ""
    new_content: str = ""
    line_start: int = 0
    line_end: int = 0
    similarity: float = 0.0


@dataclass
class DeltaReport:
    """Complete delta analysis between two versions."""

    changes: list[DeltaChange] = field(default_factory=list)
    total_lines_before: int = 0
    total_lines_after: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0
    change_ratio: float = 0.0
    compact_delta: str = ""

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    @property
    def is_minor(self) -> bool:
        return self.change_ratio < 0.1

    @property
    def summary(self) -> str:
        parts = []
        if self.lines_added:
            parts.append(f"+{self.lines_added} added")
        if self.lines_removed:
            parts.append(f"-{self.lines_removed} removed")
        if self.lines_modified:
            parts.append(f"~{self.lines_modified} modified")
        return ", ".join(parts) if parts else "No changes"


def compute_delta(old_text: str, new_text: str) -> DeltaReport:
    """Compute a structured delta between two spec versions.

    Produces both line-level and section-level change analysis.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    differ = difflib.SequenceMatcher(None, old_lines, new_lines)
    changes: list[DeltaChange] = []
    lines_added = 0
    lines_removed = 0
    lines_modified = 0

    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == "equal":
            continue

        old_chunk = "".join(old_lines[i1:i2]).strip()
        new_chunk = "".join(new_lines[j1:j2]).strip()
        section = _detect_section(old_lines, new_lines, i1, j1)

        if tag == "replace":
            sim = difflib.SequenceMatcher(None, old_chunk, new_chunk).ratio()
            changes.append(
                DeltaChange(
                    change_type=ChangeType.MODIFIED,
                    section=section,
                    old_content=old_chunk[:200],
                    new_content=new_chunk[:200],
                    line_start=j1 + 1,
                    line_end=j2,
                    similarity=round(sim, 4),
                )
            )
            lines_modified += max(i2 - i1, j2 - j1)

        elif tag == "insert":
            changes.append(
                DeltaChange(
                    change_type=ChangeType.ADDED,
                    section=section,
                    new_content=new_chunk[:200],
                    line_start=j1 + 1,
                    line_end=j2,
                )
            )
            lines_added += j2 - j1

        elif tag == "delete":
            changes.append(
                DeltaChange(
                    change_type=ChangeType.REMOVED,
                    section=section,
                    old_content=old_chunk[:200],
                    line_start=i1 + 1,
                    line_end=i2,
                )
            )
            lines_removed += i2 - i1

    total_lines = max(len(old_lines), len(new_lines), 1)
    changed_lines = lines_added + lines_removed + lines_modified
    change_ratio = round(changed_lines / total_lines, 4)

    compact = generate_compact_delta(old_text, new_text)

    return DeltaReport(
        changes=changes,
        total_lines_before=len(old_lines),
        total_lines_after=len(new_lines),
        lines_added=lines_added,
        lines_removed=lines_removed,
        lines_modified=lines_modified,
        change_ratio=change_ratio,
        compact_delta=compact,
    )


def generate_compact_delta(old_text: str, new_text: str) -> str:
    """Generate a compact, agent-friendly delta representation.

    Produces a minimal diff that an agent can apply to reconstruct
    the new version from the old one. Much smaller than sending
    the full new spec.
    """
    diff = difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile="old",
        tofile="new",
        lineterm="",
        n=1,  # Minimal context lines
    )
    return "\n".join(diff)


def generate_section_delta(old_text: str, new_text: str) -> list[dict[str, str]]:
    """Generate section-level delta (heading by heading).

    Compares sections independently, useful for agents that need to
    know which parts of the spec changed.
    """
    old_sections = _split_sections(old_text)
    new_sections = _split_sections(new_text)

    all_headings = list(dict.fromkeys(list(old_sections.keys()) + list(new_sections.keys())))
    deltas: list[dict[str, str]] = []

    for heading in all_headings:
        old_content = old_sections.get(heading, "")
        new_content = new_sections.get(heading, "")

        if old_content == new_content:
            continue
        elif not old_content:
            deltas.append({"section": heading, "type": "added", "content": new_content[:200]})
        elif not new_content:
            deltas.append({"section": heading, "type": "removed", "content": old_content[:200]})
        else:
            sim = difflib.SequenceMatcher(None, old_content, new_content).ratio()
            deltas.append(
                {
                    "section": heading,
                    "type": "modified",
                    "similarity": str(round(sim, 4)),
                    "old_preview": old_content[:100],
                    "new_preview": new_content[:100],
                }
            )

    return deltas


def delta_token_savings(old_text: str, new_text: str) -> dict:
    """Calculate token savings from using delta vs full spec."""
    compact = generate_compact_delta(old_text, new_text)

    full_tokens = len(new_text) // 4
    delta_tokens = len(compact) // 4

    return {
        "full_spec_tokens": full_tokens,
        "delta_tokens": delta_tokens,
        "savings_tokens": full_tokens - delta_tokens,
        "savings_pct": round((1 - delta_tokens / full_tokens) * 100, 2) if full_tokens > 0 else 0,
        "recommendation": (
            "Use delta — significant savings"
            if delta_tokens < full_tokens * 0.5
            else "Send full spec — delta is not significantly smaller"
        ),
    }


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown text into sections by heading."""
    sections: dict[str, str] = {}
    current_heading = "_preamble"
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            if current_lines:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = heading_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections


def _detect_section(old_lines: list[str], new_lines: list[str], old_idx: int, new_idx: int) -> str:
    """Detect which section a change belongs to by scanning for headings."""
    # Look backwards from the change location for the nearest heading
    lines = new_lines if new_idx > 0 else old_lines
    idx = new_idx if new_idx > 0 else old_idx

    for i in range(min(idx, len(lines) - 1), -1, -1):
        match = re.match(r"^(#{1,6})\s+(.+)", lines[i])
        if match:
            return match.group(2).strip()

    return "_root"
