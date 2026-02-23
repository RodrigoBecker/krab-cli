"""Huffman-based compression for spec token optimization.

Builds a frequency dictionary of repeated terms/phrases in specs and creates
short aliases, reducing overall token count when specs are fed to AI agents.
"""

from __future__ import annotations

import heapq
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class HuffmanNode:
    """Node in the Huffman tree."""

    freq: int
    symbol: str = field(compare=False, default="")
    left: HuffmanNode | None = field(compare=False, default=None, repr=False)
    right: HuffmanNode | None = field(compare=False, default=None, repr=False)


def _tokenize_spec(text: str) -> list[str]:
    """Split spec text into meaningful tokens (words, identifiers, patterns)."""
    patterns = [
        r"[A-Z][a-z]+(?:[A-Z][a-z]+)+",  # CamelCase
        r"[a-z]+(?:_[a-z]+)+",  # snake_case
        r"[a-z]+(?:-[a-z]+)+",  # kebab-case
        r"\b\w{4,}\b",  # words with 4+ chars
    ]
    tokens: list[str] = []
    for pattern in patterns:
        tokens.extend(re.findall(pattern, text))
    return tokens


def build_frequency_table(text: str, min_freq: int = 2) -> dict[str, int]:
    """Build a frequency table of tokens appearing at least `min_freq` times."""
    tokens = _tokenize_spec(text)
    counter = Counter(tokens)
    return {token: freq for token, freq in counter.most_common() if freq >= min_freq}


def build_huffman_tree(freq_table: dict[str, int]) -> HuffmanNode | None:
    """Build a Huffman tree from a frequency table."""
    if not freq_table:
        return None

    heap: list[HuffmanNode] = [HuffmanNode(freq=f, symbol=s) for s, f in freq_table.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, merged)

    return heap[0] if heap else None


def generate_codes(node: HuffmanNode | None, prefix: str = "") -> dict[str, str]:
    """Generate Huffman codes (binary strings) from the tree."""
    if node is None:
        return {}
    if node.symbol:
        return {node.symbol: prefix or "0"}
    codes: dict[str, str] = {}
    codes.update(generate_codes(node.left, prefix + "0"))
    codes.update(generate_codes(node.right, prefix + "1"))
    return codes


def create_alias_dictionary(
    freq_table: dict[str, int],
    prefix: str = "$",
    max_aliases: int = 50,
) -> dict[str, str]:
    """Create short aliases for high-frequency tokens to save tokens.

    Maps long repeated terms to short aliases like $a, $b, ..., $aa, $ab, etc.
    Returns a dict of {original_term: alias}.
    """
    sorted_terms = sorted(freq_table.items(), key=lambda x: (-x[1], -len(x[0])))
    aliases: dict[str, str] = {}
    idx = 0

    for term, freq in sorted_terms[:max_aliases]:
        # Only alias terms where alias is shorter than original
        alias = _index_to_alias(idx, prefix)
        token_savings = (len(term) - len(alias)) * freq
        if token_savings > 0:
            aliases[term] = alias
            idx += 1

    return aliases


def _index_to_alias(idx: int, prefix: str) -> str:
    """Convert an index to a short alias string: 0->$a, 25->$z, 26->$aa."""
    result = ""
    while True:
        result = chr(ord("a") + idx % 26) + result
        idx = idx // 26 - 1
        if idx < 0:
            break
    return f"{prefix}{result}"


def compress_spec(text: str, aliases: dict[str, str]) -> str:
    """Apply alias substitutions to compress a spec text."""
    result = text
    # Sort by length descending to avoid partial replacements
    for term, alias in sorted(aliases.items(), key=lambda x: -len(x[0])):
        result = result.replace(term, alias)
    return result


def decompress_spec(text: str, aliases: dict[str, str]) -> str:
    """Reverse alias substitutions to restore original spec text."""
    reverse = {alias: term for term, alias in aliases.items()}
    result = text
    for alias, term in sorted(reverse.items(), key=lambda x: -len(x[0])):
        result = result.replace(alias, term)
    return result


def build_glossary_header(aliases: dict[str, str]) -> str:
    """Build a glossary header block to prepend to compressed specs."""
    if not aliases:
        return ""
    lines = ["<!-- SDD GLOSSARY -->"]
    for term, alias in sorted(aliases.items(), key=lambda x: x[1]):
        lines.append(f"<!-- {alias} = {term} -->")
    lines.append("<!-- /SDD GLOSSARY -->\n")
    return "\n".join(lines)


def analyze_compression(original: str, compressed: str, aliases: dict[str, str]) -> dict[str, Any]:
    """Analyze compression metrics."""
    glossary = build_glossary_header(aliases)
    total_compressed = glossary + compressed
    original_len = len(original)
    compressed_len = len(total_compressed)
    return {
        "original_chars": original_len,
        "compressed_chars": compressed_len,
        "glossary_chars": len(glossary),
        "savings_chars": original_len - compressed_len,
        "compression_ratio": round(compressed_len / original_len, 4) if original_len else 0,
        "savings_pct": round((1 - compressed_len / original_len) * 100, 2) if original_len else 0,
        "alias_count": len(aliases),
    }
