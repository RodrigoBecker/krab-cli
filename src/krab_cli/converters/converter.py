"""Unified format converter: Markdown ↔ JSON, Markdown ↔ YAML.

Provides a clean API for converting SDD specs between formats.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from krab_cli.converters.md_builder import build_markdown
from krab_cli.converters.md_parser import parse_markdown

# ─── Markdown → JSON ─────────────────────────────────────────────────────


def md_to_json(md_text: str, indent: int = 2) -> str:
    """Convert Markdown spec to JSON string."""
    data = parse_markdown(md_text)
    return json.dumps(data, indent=indent, ensure_ascii=False)


def md_file_to_json_file(md_path: str | Path, json_path: str | Path, indent: int = 2) -> None:
    """Convert a Markdown file to a JSON file."""
    md_text = Path(md_path).read_text(encoding="utf-8")
    json_str = md_to_json(md_text, indent=indent)
    Path(json_path).write_text(json_str, encoding="utf-8")


# ─── JSON → Markdown ─────────────────────────────────────────────────────


def json_to_md(json_text: str) -> str:
    """Convert JSON string to Markdown spec."""
    data = json.loads(json_text)
    return build_markdown(data)


def json_file_to_md_file(json_path: str | Path, md_path: str | Path) -> None:
    """Convert a JSON file to a Markdown file."""
    json_text = Path(json_path).read_text(encoding="utf-8")
    md_str = json_to_md(json_text)
    Path(md_path).write_text(md_str, encoding="utf-8")


# ─── Markdown → YAML ─────────────────────────────────────────────────────


def md_to_yaml(md_text: str) -> str:
    """Convert Markdown spec to YAML string."""
    data = parse_markdown(md_text)
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def md_file_to_yaml_file(md_path: str | Path, yaml_path: str | Path) -> None:
    """Convert a Markdown file to a YAML file."""
    md_text = Path(md_path).read_text(encoding="utf-8")
    yaml_str = md_to_yaml(md_text)
    Path(yaml_path).write_text(yaml_str, encoding="utf-8")


# ─── YAML → Markdown ─────────────────────────────────────────────────────


def yaml_to_md(yaml_text: str) -> str:
    """Convert YAML string to Markdown spec."""
    data = yaml.safe_load(yaml_text)
    if not isinstance(data, dict):
        raise ValueError("YAML content must be a mapping (dict) at the root level.")
    return build_markdown(data)


def yaml_file_to_md_file(yaml_path: str | Path, md_path: str | Path) -> None:
    """Convert a YAML file to a Markdown file."""
    yaml_text = Path(yaml_path).read_text(encoding="utf-8")
    md_str = yaml_to_md(yaml_text)
    Path(md_path).write_text(md_str, encoding="utf-8")


# ─── Generic dispatcher ──────────────────────────────────────────────────

FORMAT_MAP = {
    ("md", "json"): md_to_json,
    ("json", "md"): json_to_md,
    ("md", "yaml"): md_to_yaml,
    ("yaml", "md"): yaml_to_md,
    ("markdown", "json"): md_to_json,
    ("json", "markdown"): json_to_md,
    ("markdown", "yaml"): md_to_yaml,
    ("yaml", "markdown"): yaml_to_md,
    ("yml", "md"): yaml_to_md,
    ("md", "yml"): md_to_yaml,
}


def convert(text: str, from_fmt: str, to_fmt: str) -> str:
    """Convert spec text between formats.

    Supported conversions:
      - md/markdown → json
      - json → md/markdown
      - md/markdown → yaml/yml
      - yaml/yml → md/markdown
    """
    key = (from_fmt.lower(), to_fmt.lower())
    converter = FORMAT_MAP.get(key)
    if converter is None:
        supported = ", ".join(f"{a}→{b}" for a, b in FORMAT_MAP)
        raise ValueError(f"Unsupported conversion: {from_fmt}→{to_fmt}. Supported: {supported}")
    return converter(text)


def detect_format(file_path: str | Path) -> str:
    """Detect spec format from file extension."""
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".md": "md",
        ".markdown": "md",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    fmt = mapping.get(ext)
    if fmt is None:
        raise ValueError(f"Unrecognized file extension: {ext}")
    return fmt
