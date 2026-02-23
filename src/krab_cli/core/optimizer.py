"""Unified spec optimizer pipeline.

Combines Huffman alias compression, fuzzy deduplication, and similarity analysis
into a single optimization pass for SDD specs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from krab_cli.core.fuzzy import deduplicate_sections, find_duplicates
from krab_cli.core.huffman import (
    analyze_compression,
    build_frequency_table,
    build_glossary_header,
    compress_spec,
    create_alias_dictionary,
)
from krab_cli.core.similarity import context_quality_score


@dataclass
class OptimizationResult:
    """Result of running the full optimization pipeline on a spec."""

    original_text: str
    optimized_text: str
    glossary: str
    aliases: dict[str, str]
    compression_metrics: dict[str, Any]
    quality_before: dict[str, Any]
    quality_after: dict[str, Any]
    duplicates_found: int
    sections_removed: int

    @property
    def final_output(self) -> str:
        """Compressed spec with glossary header."""
        if self.glossary:
            return self.glossary + self.optimized_text
        return self.optimized_text

    @property
    def total_savings_pct(self) -> float:
        return self.compression_metrics.get("savings_pct", 0.0)


def split_into_sections(text: str) -> list[str]:
    """Split a markdown spec into sections by headings."""
    parts = re.split(r"(?=^#{1,4}\s)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def reassemble_sections(sections: list[str]) -> str:
    """Reassemble sections into a single document."""
    return "\n\n".join(sections)


def optimize_spec(
    text: str,
    *,
    deduplicate: bool = True,
    compress: bool = True,
    dedup_threshold: float = 90.0,
    min_freq: int = 3,
    max_aliases: int = 50,
    context_window: int = 8192,
) -> OptimizationResult:
    """Run the full optimization pipeline on a spec.

    Steps:
      1. Analyze quality before optimization
      2. Split into sections and deduplicate (fuzzy)
      3. Build frequency table and alias dictionary (Huffman-inspired)
      4. Compress using aliases
      5. Analyze quality after optimization
      6. Return comprehensive result

    Args:
        text: Raw spec markdown text.
        deduplicate: Whether to run fuzzy deduplication.
        compress: Whether to apply Huffman-style alias compression.
        dedup_threshold: Similarity threshold for deduplication (0-100).
        min_freq: Minimum frequency for a term to be aliased.
        max_aliases: Maximum number of aliases to create.
        context_window: Target context window size for quality analysis.
    """
    quality_before = context_quality_score(text, context_window)

    # Step 1: Deduplicate sections
    sections = split_into_sections(text)
    original_section_count = len(sections)
    duplicates_found = 0

    if deduplicate and len(sections) > 1:
        dupes = find_duplicates(sections, threshold=dedup_threshold)
        duplicates_found = len(dupes)
        sections = deduplicate_sections(sections, threshold=dedup_threshold)

    sections_removed = original_section_count - len(sections)
    working_text = reassemble_sections(sections)

    # Step 2: Huffman-style alias compression
    aliases: dict[str, str] = {}
    glossary = ""

    if compress:
        freq_table = build_frequency_table(working_text, min_freq=min_freq)
        aliases = create_alias_dictionary(freq_table, max_aliases=max_aliases)
        working_text = compress_spec(working_text, aliases)
        glossary = build_glossary_header(aliases)

    compression_metrics = analyze_compression(text, working_text, aliases)
    quality_after = context_quality_score(glossary + working_text, context_window)

    return OptimizationResult(
        original_text=text,
        optimized_text=working_text,
        glossary=glossary,
        aliases=aliases,
        compression_metrics=compression_metrics,
        quality_before=quality_before,
        quality_after=quality_after,
        duplicates_found=duplicates_found,
        sections_removed=sections_removed,
    )
