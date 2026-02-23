"""Repeated substring detection using suffix arrays.

Finds exact repeated substrings of any length across specs, identifying
verbatim duplicated phrases like "The system must implement" that appear
multiple times and waste context tokens.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class RepeatedSubstring:
    """A repeated substring finding."""

    text: str
    count: int
    total_chars: int
    estimated_token_waste: int

    @property
    def savings_potential(self) -> int:
        """Characters that could be saved by aliasing this substring."""
        alias_cost = 4  # e.g., "$ab"
        return (len(self.text) - alias_cost) * (self.count - 1)


def _build_suffix_array(text: str) -> list[int]:
    """Build a suffix array for the text.

    Returns sorted indices of all suffixes.
    Uses Python's built-in sort which is efficient enough for spec-sized texts.
    """
    n = len(text)
    suffixes = list(range(n))
    suffixes.sort(key=lambda i: text[i:])
    return suffixes


def _lcp_from_suffix_array(text: str, sa: list[int]) -> list[int]:
    """Compute Longest Common Prefix array from suffix array.

    LCP[i] = length of longest common prefix between sa[i] and sa[i-1].
    """
    n = len(text)
    rank = [0] * n
    lcp = [0] * n

    for i, s in enumerate(sa):
        rank[s] = i

    k = 0
    for i in range(n):
        if rank[i] == 0:
            k = 0
            continue

        j = sa[rank[i] - 1]
        while i + k < n and j + k < n and text[i + k] == text[j + k]:
            k += 1
        lcp[rank[i]] = k
        k = max(k - 1, 0)

    return lcp


def find_repeated_substrings(
    text: str,
    min_length: int = 15,
    min_count: int = 2,
    max_results: int = 50,
) -> list[RepeatedSubstring]:
    """Find repeated substrings using suffix array + LCP.

    Args:
        text: Input text.
        min_length: Minimum substring length to report.
        min_count: Minimum repetition count.
        max_results: Maximum results to return.

    Returns:
        List of RepeatedSubstring sorted by savings potential.
    """
    if len(text) < min_length:
        return []

    # Normalize whitespace for comparison
    normalized = re.sub(r"\s+", " ", text)

    sa = _build_suffix_array(normalized)
    lcp = _lcp_from_suffix_array(normalized, sa)

    # Collect candidate substrings from LCP runs
    candidates: dict[str, int] = {}

    for i in range(1, len(lcp)):
        if lcp[i] >= min_length:
            substr = normalized[sa[i] : sa[i] + lcp[i]]
            # Trim to word boundaries
            substr = _trim_to_words(substr)
            if len(substr) >= min_length:
                candidates[substr] = candidates.get(substr, 0) + 1

    # Count actual occurrences more precisely
    results: list[RepeatedSubstring] = []
    seen_substrings: set[str] = set()

    for substr, _approx_count in sorted(candidates.items(), key=lambda x: -len(x[0])):
        # Skip if this is a substring of an already-found longer string
        if any(substr in seen for seen in seen_substrings):
            continue

        actual_count = normalized.count(substr)
        if actual_count >= min_count:
            total_chars = len(substr) * actual_count
            # Rough token estimate: ~4 chars per token
            token_waste = (total_chars - len(substr)) // 4

            results.append(
                RepeatedSubstring(
                    text=substr.strip(),
                    count=actual_count,
                    total_chars=total_chars,
                    estimated_token_waste=token_waste,
                )
            )
            seen_substrings.add(substr)

    # Sort by savings potential
    results.sort(key=lambda r: -r.savings_potential)
    return results[:max_results]


def find_repeated_phrases(
    text: str,
    min_words: int = 3,
    min_count: int = 2,
    max_results: int = 50,
) -> list[RepeatedSubstring]:
    """Find repeated multi-word phrases using n-gram counting.

    Simpler and faster than suffix arrays for phrase-level detection.

    Args:
        text: Input text.
        min_words: Minimum words per phrase.
        min_count: Minimum repetition count.
        max_results: Maximum results to return.
    """
    # Tokenize into words, preserving some structure
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < min_words:
        return []

    results: list[RepeatedSubstring] = []

    # Try different phrase lengths from longest to shortest
    for n in range(min(10, len(words)), min_words - 1, -1):
        phrases: list[str] = []
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            phrases.append(phrase)

        counter = Counter(phrases)

        for phrase, count in counter.most_common():
            if count < min_count:
                break

            # Skip if this phrase is part of an already-found longer phrase
            already_covered = any(phrase in r.text for r in results)
            if already_covered:
                continue

            total_chars = len(phrase) * count
            token_waste = (total_chars - len(phrase)) // 4

            results.append(
                RepeatedSubstring(
                    text=phrase,
                    count=count,
                    total_chars=total_chars,
                    estimated_token_waste=token_waste,
                )
            )

    results.sort(key=lambda r: -r.savings_potential)
    return results[:max_results]


def _trim_to_words(text: str) -> str:
    """Trim a substring to word boundaries."""
    # Remove partial words at start
    match = re.match(r"^\w*\s+", text)
    if match:
        text = text[match.end() :]

    # Remove partial words at end
    match = re.search(r"\s+\w*$", text)
    if match:
        text = text[: match.start()]

    return text.strip()


def total_waste_analysis(text: str, min_length: int = 15) -> dict:
    """Analyze total character/token waste from repeated substrings."""
    repeated = find_repeated_substrings(text, min_length=min_length)
    phrases = find_repeated_phrases(text, min_words=3)

    total_char_waste = sum(r.savings_potential for r in repeated)
    total_phrase_waste = sum(r.savings_potential for r in phrases)

    return {
        "repeated_substrings": len(repeated),
        "repeated_phrases": len(phrases),
        "char_waste_substrings": total_char_waste,
        "char_waste_phrases": total_phrase_waste,
        "estimated_token_savings": (total_char_waste + total_phrase_waste) // 4,
        "text_length": len(text),
        "waste_pct": round((total_char_waste / len(text)) * 100, 2) if text else 0,
    }
