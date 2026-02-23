"""Information-theoretic analysis for SDD specs.

Implements Shannon Entropy, Markov Chain predictability, and estimated Perplexity
to measure real information content and identify redundant/boilerplate patterns.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r"\b\w+\b", text.lower())


# ─── Shannon Entropy ──────────────────────────────────────────────────────


def shannon_entropy(text: str) -> float:
    """Calculate Shannon entropy (bits per token) of a text.

    H(X) = -sum(p(x) * log2(p(x)))

    Higher entropy = more information content / less predictable.
    Lower entropy = more repetitive / compressible.
    """
    tokens = tokenize(text)
    if not tokens:
        return 0.0

    total = len(tokens)
    freq = Counter(tokens)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def section_entropy_map(sections: dict[str, str]) -> dict[str, float]:
    """Calculate entropy for each named section.

    Args:
        sections: Dict of {section_name: section_text}.

    Returns:
        Dict of {section_name: entropy_value}.
    """
    return {name: shannon_entropy(text) for name, text in sections.items()}


def entropy_grade(entropy: float, token_count: int) -> str:
    """Grade entropy quality for a spec section."""
    if token_count < 10:
        return "TOO_SHORT"
    if entropy >= 6.0:
        return "EXCELLENT"
    if entropy >= 4.5:
        return "GOOD"
    if entropy >= 3.0:
        return "FAIR"
    return "LOW — high redundancy"


# ─── Markov Chain Analysis ────────────────────────────────────────────────


@dataclass
class MarkovAnalysis:
    """Results of Markov chain predictability analysis."""

    order: int
    predictability: float
    top_patterns: list[tuple[str, str, float]]
    total_transitions: int
    unique_transitions: int

    @property
    def predictability_grade(self) -> str:
        if self.predictability >= 0.8:
            return "HIGHLY_PREDICTABLE — boilerplate heavy"
        if self.predictability >= 0.6:
            return "PREDICTABLE — some redundancy"
        if self.predictability >= 0.4:
            return "MODERATE"
        return "LOW_PREDICTABILITY — good variety"


def markov_predictability(text: str, order: int = 1) -> MarkovAnalysis:
    """Analyze text predictability using a Markov chain of given order.

    Builds transition probabilities and measures how predictable the next
    token is given the previous `order` tokens. High predictability means
    the spec uses repetitive sentence structures.

    Args:
        text: Input text.
        order: Markov chain order (1 = bigram, 2 = trigram patterns).
    """
    tokens = tokenize(text)
    if len(tokens) <= order:
        return MarkovAnalysis(
            order=order,
            predictability=0.0,
            top_patterns=[],
            total_transitions=0,
            unique_transitions=0,
        )

    # Build transition counts
    transitions: dict[tuple[str, ...], Counter] = defaultdict(Counter)
    for i in range(len(tokens) - order):
        state = tuple(tokens[i : i + order])
        next_token = tokens[i + order]
        transitions[state][next_token] += 1

    # Calculate average max transition probability
    total_max_prob = 0.0
    total_transitions = 0
    unique_transitions = 0

    for _state, next_counts in transitions.items():
        total = sum(next_counts.values())
        max_prob = max(next_counts.values()) / total
        total_max_prob += max_prob
        total_transitions += total
        unique_transitions += len(next_counts)

    num_states = len(transitions)
    predictability = total_max_prob / num_states if num_states else 0.0

    # Top most predictable patterns
    top_patterns: list[tuple[str, str, float]] = []
    for state, next_counts in transitions.items():
        total = sum(next_counts.values())
        most_common_token, most_common_count = next_counts.most_common(1)[0]
        prob = most_common_count / total
        if prob >= 0.7 and total >= 2:
            state_str = " ".join(state)
            top_patterns.append((state_str, most_common_token, round(prob, 3)))

    top_patterns.sort(key=lambda x: -x[2])

    return MarkovAnalysis(
        order=order,
        predictability=round(predictability, 4),
        top_patterns=top_patterns[:15],
        total_transitions=total_transitions,
        unique_transitions=unique_transitions,
    )


# ─── Perplexity ───────────────────────────────────────────────────────────


def estimated_perplexity(text: str, order: int = 1) -> float:
    """Estimate perplexity of text using an n-gram language model.

    Perplexity = 2^H where H is the cross-entropy.
    Lower perplexity = more predictable/repetitive text.
    Higher perplexity = more diverse/informative text.

    For spec optimization, we want a balance: too low means boilerplate,
    too high might mean incoherent content.
    """
    tokens = tokenize(text)
    if len(tokens) <= order + 1:
        return 0.0

    # Build n-gram model
    ngram_counts: dict[tuple[str, ...], Counter] = defaultdict(Counter)
    for i in range(len(tokens) - order):
        context = tuple(tokens[i : i + order])
        next_token = tokens[i + order]
        ngram_counts[context][next_token] += 1

    # Calculate cross-entropy
    log_prob_sum = 0.0
    count = 0

    for i in range(len(tokens) - order):
        context = tuple(tokens[i : i + order])
        next_token = tokens[i + order]

        if context in ngram_counts:
            total = sum(ngram_counts[context].values())
            token_count = ngram_counts[context].get(next_token, 0)
            if token_count > 0:
                prob = token_count / total
                log_prob_sum += math.log2(prob)
                count += 1

    if count == 0:
        return 0.0

    cross_entropy = -log_prob_sum / count
    perplexity = 2**cross_entropy
    return round(perplexity, 4)


def perplexity_grade(perplexity: float) -> str:
    """Grade perplexity for spec quality."""
    if perplexity == 0:
        return "INSUFFICIENT_DATA"
    if perplexity >= 50:
        return "HIGH — very diverse content"
    if perplexity >= 20:
        return "GOOD — balanced variety"
    if perplexity >= 8:
        return "MODERATE — some repetition"
    return "LOW — highly repetitive/boilerplate"


# ─── Combined Report ──────────────────────────────────────────────────────


@dataclass
class EntropyReport:
    """Combined information-theoretic analysis."""

    entropy: float
    entropy_grade: str
    markov: MarkovAnalysis
    perplexity: float
    perplexity_grade: str
    token_count: int
    unique_tokens: int
    vocabulary_richness: float


def full_entropy_analysis(text: str) -> EntropyReport:
    """Run all information-theoretic analyses on a text."""
    tokens = tokenize(text)
    unique = set(tokens)
    total = len(tokens)

    ent = shannon_entropy(text)
    markov = markov_predictability(text, order=1)
    perp = estimated_perplexity(text, order=1)

    return EntropyReport(
        entropy=ent,
        entropy_grade=entropy_grade(ent, total),
        markov=markov,
        perplexity=perp,
        perplexity_grade=perplexity_grade(perp),
        token_count=total,
        unique_tokens=len(unique),
        vocabulary_richness=round(len(unique) / total, 4) if total else 0,
    )
