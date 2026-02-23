"""Similarity algorithms for spec comparison and context quality analysis.

Provides multiple similarity metrics (Jaccard, Cosine, N-gram overlap, TF-IDF)
for comparing specs, detecting redundancy, and evaluating context quality.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class SimilarityReport:
    """Comprehensive similarity report between two texts."""

    jaccard: float
    cosine: float
    ngram_overlap: float
    combined: float
    shared_terms: list[str]
    unique_to_a: list[str]
    unique_to_b: list[str]

    @property
    def verdict(self) -> str:
        if self.combined >= 0.9:
            return "DUPLICATE"
        if self.combined >= 0.7:
            return "HIGH_SIMILARITY"
        if self.combined >= 0.4:
            return "MODERATE_SIMILARITY"
        return "LOW_SIMILARITY"


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r"\b\w+\b", text.lower())


def ngrams(tokens: list[str], n: int = 2) -> list[tuple[str, ...]]:
    """Generate n-grams from a token list."""
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity coefficient between two texts.

    J(A,B) = |A intersection B| / |A union B|
    """
    set_a = set(tokenize(a))
    set_b = set(tokenize(b))
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity(a: str, b: str) -> float:
    """Cosine similarity between two texts using term frequency vectors.

    cos(A,B) = (A . B) / (||A|| x ||B||)
    """
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)

    all_terms = set(counter_a.keys()) | set(counter_b.keys())
    if not all_terms:
        return 0.0

    dot_product = sum(counter_a.get(t, 0) * counter_b.get(t, 0) for t in all_terms)
    magnitude_a = math.sqrt(sum(v**2 for v in counter_a.values()))
    magnitude_b = math.sqrt(sum(v**2 for v in counter_b.values()))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def ngram_overlap(a: str, b: str, n: int = 2) -> float:
    """N-gram overlap coefficient between two texts.

    Measures structural similarity by comparing shared n-grams.
    """
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    ngrams_a = set(ngrams(tokens_a, n))
    ngrams_b = set(ngrams(tokens_b, n))

    if not ngrams_a and not ngrams_b:
        return 1.0
    intersection = ngrams_a & ngrams_b
    min_size = min(len(ngrams_a), len(ngrams_b))
    return len(intersection) / min_size if min_size else 0.0


def tfidf_similarity(documents: list[str], query_idx: int, target_idx: int) -> float:
    """TF-IDF based cosine similarity between two documents in a corpus.

    Considers term importance across the entire spec corpus.
    """
    if len(documents) < 2:
        return 0.0

    tokenized = [tokenize(doc) for doc in documents]
    all_terms = set()
    for tokens in tokenized:
        all_terms.update(tokens)

    # Compute IDF
    doc_count = len(documents)
    idf: dict[str, float] = {}
    for term in all_terms:
        df = sum(1 for tokens in tokenized if term in tokens)
        idf[term] = math.log(doc_count / (1 + df)) + 1

    # Compute TF-IDF vectors for query and target
    def tfidf_vector(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: (tf.get(term, 0) / total) * idf.get(term, 0) for term in all_terms}

    vec_a = tfidf_vector(tokenized[query_idx])
    vec_b = tfidf_vector(tokenized[target_idx])

    dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in all_terms)
    mag_a = math.sqrt(sum(v**2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v**2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def full_comparison(a: str, b: str) -> SimilarityReport:
    """Run all similarity metrics and produce a comprehensive report."""
    jac = jaccard_similarity(a, b)
    cos = cosine_similarity(a, b)
    ngo = ngram_overlap(a, b, n=2)
    combined = jac * 0.3 + cos * 0.4 + ngo * 0.3

    set_a = set(tokenize(a))
    set_b = set(tokenize(b))
    shared = sorted(set_a & set_b)
    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)

    return SimilarityReport(
        jaccard=round(jac, 4),
        cosine=round(cos, 4),
        ngram_overlap=round(ngo, 4),
        combined=round(combined, 4),
        shared_terms=shared[:20],
        unique_to_a=only_a[:20],
        unique_to_b=only_b[:20],
    )


def context_quality_score(spec: str, context_window: int = 8192) -> dict:
    """Evaluate how well a spec utilizes an AI context window.

    Returns metrics on information density, redundancy, and estimated token usage.
    """
    tokens = tokenize(spec)
    unique_tokens = set(tokens)
    total = len(tokens)
    unique_count = len(unique_tokens)

    # Estimate tokens (rough ~0.75 words per token for English)
    estimated_tokens = int(total * 1.33)

    # Information density: ratio of unique to total tokens
    density = unique_count / total if total else 0

    # Redundancy: repeated tokens / total
    redundancy = 1 - density

    # Context utilization
    utilization = min(estimated_tokens / context_window, 1.0)

    return {
        "word_count": total,
        "unique_words": unique_count,
        "estimated_tokens": estimated_tokens,
        "context_window": context_window,
        "utilization_pct": round(utilization * 100, 2),
        "information_density": round(density, 4),
        "redundancy_ratio": round(redundancy, 4),
        "density_grade": _grade_density(density),
    }


def _grade_density(density: float) -> str:
    """Grade information density."""
    if density >= 0.7:
        return "EXCELLENT"
    if density >= 0.5:
        return "GOOD"
    if density >= 0.3:
        return "FAIR"
    return "POOR — consider deduplication"
