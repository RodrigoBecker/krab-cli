"""Spec data models for structured representation and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SpecMetadata:
    """Metadata about a spec document."""

    title: str = ""
    version: str = "1.0.0"
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    format: str = "md"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at,
            "tags": self.tags,
            "format": self.format,
        }


@dataclass
class SpecSection:
    """A section within a spec."""

    heading: str
    level: int = 1
    content: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "heading": self.heading,
            "level": self.level,
            "content": self.content,
        }

    @property
    def text(self) -> str:
        """Extract plain text from all content blocks."""
        parts: list[str] = []
        for block in self.content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "paragraph":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "list":
                    for item in block.get("items", []):
                        parts.append(item.get("text", ""))
                elif block.get("type") == "code_block":
                    parts.append(block.get("content", ""))
        return "\n".join(parts)


@dataclass
class Spec:
    """Complete SDD spec document."""

    metadata: SpecMetadata = field(default_factory=SpecMetadata)
    sections: list[SpecSection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "_meta": self.metadata.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
        }

    @property
    def full_text(self) -> str:
        """Get all text content concatenated."""
        return "\n\n".join(s.text for s in self.sections)

    @property
    def section_count(self) -> int:
        return len(self.sections)

    def get_section(self, heading: str) -> SpecSection | None:
        """Find a section by heading (case-insensitive)."""
        heading_lower = heading.lower()
        for section in self.sections:
            if section.heading.lower() == heading_lower:
                return section
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Spec:
        """Create a Spec from a parsed dict."""
        meta_data = data.get("_meta", {})
        metadata = SpecMetadata(
            title=meta_data.get("title", ""),
            version=meta_data.get("version", "1.0.0"),
            author=meta_data.get("author", ""),
            tags=meta_data.get("tags", []),
        )
        sections = [
            SpecSection(
                heading=s.get("heading", ""),
                level=s.get("level", 1),
                content=s.get("content", []),
            )
            for s in data.get("sections", [])
        ]
        return cls(metadata=metadata, sections=sections)
