"""Markdown parser for SDD specs.

Parses structured Markdown (headings, lists, code blocks, metadata)
into a normalized dictionary representation that can be serialized to JSON/YAML.
"""

from __future__ import annotations

import re
from typing import Any


def parse_markdown(text: str) -> dict[str, Any]:
    """Parse a Markdown spec into a structured dictionary.

    Handles:
      - YAML front-matter (--- delimited)
      - Headings (h1-h6) as nested keys
      - Bullet/numbered lists as arrays
      - Code blocks with language annotation
      - Paragraphs as text content
    """
    result: dict[str, Any] = {}
    lines = text.strip().split("\n")
    idx = 0

    # Parse front-matter
    if lines and lines[0].strip() == "---":
        idx = 1
        front_matter_lines: list[str] = []
        while idx < len(lines) and lines[idx].strip() != "---":
            front_matter_lines.append(lines[idx])
            idx += 1
        idx += 1  # skip closing ---
        if front_matter_lines:
            result["_meta"] = _parse_yaml_like(front_matter_lines)

    # Parse body
    sections = _parse_sections(lines[idx:])
    result["sections"] = sections

    return result


def _parse_sections(lines: list[str]) -> list[dict[str, Any]]:
    """Parse lines into a flat list of section dicts."""
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    content_buffer: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []

    for line in lines:
        # Code block toggle
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line.strip().lstrip("`").strip()
                code_lines = []
                continue
            else:
                in_code_block = False
                block = {
                    "type": "code_block",
                    "language": code_lang,
                    "content": "\n".join(code_lines),
                }
                if current_section is not None:
                    current_section.setdefault("content", []).append(block)
                else:
                    sections.append({"heading": "", "level": 0, "content": [block]})
                continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Flush buffer
            if current_section is not None and content_buffer:
                _flush_buffer(current_section, content_buffer)
                content_buffer = []

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            current_section = {"heading": title, "level": level, "content": []}
            sections.append(current_section)
            continue

        # List item
        list_match = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
        num_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", line)

        if list_match or num_match:
            match = list_match or num_match
            item_text = match.group(2).strip()
            depth = len(match.group(1)) // 2

            if current_section is None:
                current_section = {"heading": "", "level": 0, "content": []}
                sections.append(current_section)

            # Check if last content is a list
            contents = current_section.setdefault("content", [])
            list_type = "unordered" if list_match else "ordered"
            if contents and isinstance(contents[-1], dict) and contents[-1].get("type") == "list":
                contents[-1]["items"].append({"text": item_text, "depth": depth})
            else:
                contents.append(
                    {
                        "type": "list",
                        "list_type": list_type,
                        "items": [{"text": item_text, "depth": depth}],
                    }
                )
            continue

        # Regular text
        if line.strip():
            content_buffer.append(line.strip())
        elif content_buffer:
            if current_section is None:
                current_section = {"heading": "", "level": 0, "content": []}
                sections.append(current_section)
            _flush_buffer(current_section, content_buffer)
            content_buffer = []

    # Final flush
    if content_buffer and current_section is not None:
        _flush_buffer(current_section, content_buffer)

    return sections


def _flush_buffer(section: dict[str, Any], buffer: list[str]) -> None:
    """Flush accumulated text lines as a paragraph block."""
    text = " ".join(buffer)
    section.setdefault("content", []).append({"type": "paragraph", "text": text})
    buffer.clear()


def _parse_yaml_like(lines: list[str]) -> dict[str, str]:
    """Simple YAML-like key: value parser for front-matter."""
    result: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result
