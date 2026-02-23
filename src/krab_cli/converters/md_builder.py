"""Markdown builder — converts structured dicts (from JSON/YAML) back to Markdown.

Produces clean, readable Markdown output from the normalized dict representation.
"""

from __future__ import annotations

from typing import Any


def build_markdown(data: dict[str, Any]) -> str:
    """Convert a structured spec dict back to Markdown.

    Args:
        data: Dict with optional '_meta' (front-matter) and 'sections' list.

    Returns:
        Formatted Markdown string.
    """
    parts: list[str] = []

    # Front-matter
    meta = data.get("_meta")
    if meta:
        parts.append("---")
        for key, value in meta.items():
            parts.append(f"{key}: {value}")
        parts.append("---")
        parts.append("")

    # Sections
    sections = data.get("sections", [])
    if not sections and not meta:
        # If data is just a flat dict, build from keys
        sections = _dict_to_sections(data)

    for section in sections:
        section_md = _build_section(section)
        if section_md:
            parts.append(section_md)

    return "\n".join(parts).strip() + "\n"


def _build_section(section: dict[str, Any]) -> str:
    """Build Markdown for a single section."""
    lines: list[str] = []

    heading = section.get("heading", "")
    level = section.get("level", 1)

    if heading:
        prefix = "#" * level
        lines.append(f"{prefix} {heading}")
        lines.append("")

    for block in section.get("content", []):
        if isinstance(block, str):
            lines.append(block)
            lines.append("")
            continue

        block_type = block.get("type", "")

        if block_type == "paragraph":
            lines.append(block.get("text", ""))
            lines.append("")

        elif block_type == "list":
            for item in block.get("items", []):
                depth = item.get("depth", 0)
                indent = "  " * depth
                prefix = "-" if block.get("list_type") == "unordered" else "1."
                lines.append(f"{indent}{prefix} {item.get('text', '')}")
            lines.append("")

        elif block_type == "code_block":
            lang = block.get("language", "")
            lines.append(f"```{lang}")
            lines.append(block.get("content", ""))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def _dict_to_sections(data: dict[str, Any], level: int = 1) -> list[dict[str, Any]]:
    """Convert a flat dict into section format for Markdown generation."""
    sections: list[dict[str, Any]] = []

    for key, value in data.items():
        if key.startswith("_"):
            continue

        section: dict[str, Any] = {"heading": _key_to_heading(key), "level": level, "content": []}

        if isinstance(value, str):
            section["content"].append({"type": "paragraph", "text": value})

        elif isinstance(value, list):
            items = [{"text": str(item), "depth": 0} for item in value]
            section["content"].append({"type": "list", "list_type": "unordered", "items": items})

        elif isinstance(value, dict):
            section["content"].append({"type": "paragraph", "text": _format_dict_as_text(value)})
            # Recurse for nested dicts
            sub_sections = _dict_to_sections(value, level + 1)
            sections.append(section)
            sections.extend(sub_sections)
            continue

        sections.append(section)

    return sections


def _key_to_heading(key: str) -> str:
    """Convert a dict key to a human-readable heading."""
    return key.replace("_", " ").replace("-", " ").title()


def _format_dict_as_text(d: dict) -> str:
    """Format a simple dict as descriptive text."""
    parts = []
    for k, v in d.items():
        if isinstance(v, (str, int, float, bool)):
            parts.append(f"**{k}**: {v}")
    return " | ".join(parts) if parts else ""
