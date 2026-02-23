"""Fuzzy matching for spec deduplication and section similarity detection.

Uses RapidFuzz for fast string matching to find duplicate or near-duplicate
sections across specs, enabling consolidation and reducing redundancy.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process


@dataclass
class SimilarityMatch:
    """Represents a fuzzy match between two text sections."""

    source: str
    target: str
    score: float
    method: str

    @property
    def is_duplicate(self) -> bool:
        return self.score >= 95.0

    @property
    def is_near_duplicate(self) -> bool:
        return 80.0 <= self.score < 95.0

    @property
    def is_similar(self) -> bool:
        return 60.0 <= self.score < 80.0


def ratio_score(a: str, b: str) -> float:
    """Simple ratio similarity between two strings (0-100)."""
    return fuzz.ratio(a, b)


def partial_ratio_score(a: str, b: str) -> float:
    """Partial ratio — best matching substring (0-100)."""
    return fuzz.partial_ratio(a, b)


def token_sort_score(a: str, b: str) -> float:
    """Token sort ratio — order-invariant comparison (0-100)."""
    return fuzz.token_sort_ratio(a, b)


def token_set_score(a: str, b: str) -> float:
    """Token set ratio — handles duplicates and extras (0-100)."""
    return fuzz.token_set_ratio(a, b)


def weighted_score(a: str, b: str) -> float:
    """Weighted combination of multiple fuzzy methods for robust matching."""
    scores = {
        "ratio": fuzz.ratio(a, b),
        "partial": fuzz.partial_ratio(a, b),
        "token_sort": fuzz.token_sort_ratio(a, b),
        "token_set": fuzz.token_set_ratio(a, b),
    }
    weights = {"ratio": 0.2, "partial": 0.2, "token_sort": 0.3, "token_set": 0.3}
    return sum(scores[k] * weights[k] for k in scores)


def find_duplicates(
    sections: list[str],
    threshold: float = 80.0,
    method: str = "weighted",
) -> list[SimilarityMatch]:
    """Find duplicate or near-duplicate sections in a list of spec sections.

    Args:
        sections: List of text sections to compare.
        threshold: Minimum score (0-100) to consider a match.
        method: Scoring method — 'ratio', 'partial', 'token_sort', 'token_set', 'weighted'.

    Returns:
        List of SimilarityMatch objects above the threshold.
    """
    score_fn = _get_score_fn(method)
    matches: list[SimilarityMatch] = []

    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            score = score_fn(sections[i], sections[j])
            if score >= threshold:
                matches.append(
                    SimilarityMatch(
                        source=sections[i][:80],
                        target=sections[j][:80],
                        score=round(score, 2),
                        method=method,
                    )
                )

    return sorted(matches, key=lambda m: -m.score)


def find_best_match(
    query: str,
    candidates: list[str],
    threshold: float = 60.0,
    limit: int = 5,
) -> list[tuple[str, float]]:
    """Find the best matching candidates for a query string.

    Returns list of (candidate, score) tuples sorted by score descending.
    """
    results = process.extract(query, candidates, scorer=fuzz.WRatio, limit=limit)
    return [(match, score) for match, score, _ in results if score >= threshold]


def deduplicate_sections(
    sections: list[str],
    threshold: float = 90.0,
) -> list[str]:
    """Remove near-duplicate sections, keeping the longest version.

    Args:
        sections: List of text sections.
        threshold: Similarity threshold above which sections are considered duplicates.

    Returns:
        Deduplicated list of sections.
    """
    if not sections:
        return []

    keep: list[str] = []
    removed_indices: set[int] = set()

    for i in range(len(sections)):
        if i in removed_indices:
            continue
        best = sections[i]
        for j in range(i + 1, len(sections)):
            if j in removed_indices:
                continue
            score = weighted_score(sections[i], sections[j])
            if score >= threshold:
                removed_indices.add(j)
                if len(sections[j]) > len(best):
                    best = sections[j]
        keep.append(best)

    return keep


def _get_score_fn(method: str):
    """Get the scoring function for a given method name."""
    methods = {
        "ratio": ratio_score,
        "partial": partial_ratio_score,
        "token_sort": token_sort_score,
        "token_set": token_set_score,
        "weighted": weighted_score,
    }
    if method not in methods:
        raise ValueError(f"Unknown method '{method}'. Choose from: {list(methods.keys())}")
    return methods[method]
