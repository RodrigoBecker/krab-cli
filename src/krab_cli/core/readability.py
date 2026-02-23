"""Readability analysis for SDD specs.

Implements Flesch-Kincaid, Coleman-Liau, Gunning Fog, and ARI (Automated
Readability Index) adapted for technical documentation. Higher complexity
in specs correlates with increased hallucination risk for AI agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


def _count_sentences(text: str) -> int:
    """Count sentences using punctuation boundaries."""
    sentences = re.split(r"[.!?]+", text)
    return max(len([s for s in sentences if s.strip()]), 1)


def _count_words(text: str) -> int:
    """Count words."""
    return max(len(re.findall(r"\b\w+\b", text)), 1)


def _count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.lower().strip()
    if len(word) <= 2:
        return 1

    # Remove trailing silent e
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    return max(count, 1)


def _count_total_syllables(text: str) -> int:
    """Count total syllables in text."""
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    return sum(_count_syllables(w) for w in words)


def _count_complex_words(text: str) -> int:
    """Count words with 3+ syllables (for Gunning Fog)."""
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    return sum(1 for w in words if _count_syllables(w) >= 3)


def _count_characters(text: str) -> int:
    """Count alphanumeric characters."""
    return len(re.findall(r"\w", text))


# ─── Readability Metrics ──────────────────────────────────────────────────


def flesch_kincaid_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level.

    FK = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59

    Returns estimated US school grade level needed to understand the text.
    Typical specs: 10-14. Above 16 = very complex.
    """
    words = _count_words(text)
    sentences = _count_sentences(text)
    syllables = _count_total_syllables(text)

    score = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    return round(max(score, 0), 2)


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease score.

    FRE = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)

    Scale: 0-100. Higher = easier to read.
    90-100: Very Easy | 60-70: Standard | 30-50: Difficult | 0-30: Very Confusing
    """
    words = _count_words(text)
    sentences = _count_sentences(text)
    syllables = _count_total_syllables(text)

    score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    return round(max(min(score, 100), 0), 2)


def coleman_liau_index(text: str) -> float:
    """Coleman-Liau Index.

    CLI = 0.0588 * L - 0.296 * S - 15.8
    L = avg letters per 100 words, S = avg sentences per 100 words

    Based on character counts rather than syllables — more reliable for
    technical text with abbreviations and acronyms.
    """
    words = _count_words(text)
    sentences = _count_sentences(text)
    characters = _count_characters(text)

    l_value = (characters / words) * 100
    s_value = (sentences / words) * 100

    score = 0.0588 * l_value - 0.296 * s_value - 15.8
    return round(max(score, 0), 2)


def gunning_fog_index(text: str) -> float:
    """Gunning Fog Index.

    GFI = 0.4 * ((words/sentences) + 100 * (complex_words/words))

    Complex words = 3+ syllables. Good for detecting jargon-heavy specs.
    Under 12: readable. 12-16: acceptable. Above 16: difficult.
    """
    words = _count_words(text)
    sentences = _count_sentences(text)
    complex_words = _count_complex_words(text)

    score = 0.4 * ((words / sentences) + 100 * (complex_words / words))
    return round(score, 2)


def ari_score(text: str) -> float:
    """Automated Readability Index.

    ARI = 4.71 * (characters/words) + 0.5 * (words/sentences) - 21.43

    Character-based like Coleman-Liau. Good for code-heavy technical docs.
    """
    words = _count_words(text)
    sentences = _count_sentences(text)
    characters = _count_characters(text)

    score = 4.71 * (characters / words) + 0.5 * (words / sentences) - 21.43
    return round(max(score, 0), 2)


# ─── Combined Report ──────────────────────────────────────────────────────


@dataclass
class ReadabilityReport:
    """Comprehensive readability analysis."""

    flesch_kincaid_grade: float
    flesch_reading_ease: float
    coleman_liau: float
    gunning_fog: float
    ari: float
    word_count: int
    sentence_count: int
    avg_words_per_sentence: float
    complex_word_pct: float
    overall_grade: str
    recommendation: str


def full_readability_analysis(text: str) -> ReadabilityReport:
    """Run all readability metrics and produce a report with recommendations."""
    words = _count_words(text)
    sentences = _count_sentences(text)
    complex_words = _count_complex_words(text)

    fk = flesch_kincaid_grade(text)
    fre = flesch_reading_ease(text)
    cl = coleman_liau_index(text)
    gf = gunning_fog_index(text)
    ar = ari_score(text)

    avg_grade = (fk + cl + gf + ar) / 4
    avg_wps = round(words / sentences, 1)
    complex_pct = round((complex_words / words) * 100, 1) if words else 0

    grade, recommendation = _grade_and_recommend(avg_grade, avg_wps, complex_pct, fre)

    return ReadabilityReport(
        flesch_kincaid_grade=fk,
        flesch_reading_ease=fre,
        coleman_liau=cl,
        gunning_fog=gf,
        ari=ar,
        word_count=words,
        sentence_count=sentences,
        avg_words_per_sentence=avg_wps,
        complex_word_pct=complex_pct,
        overall_grade=grade,
        recommendation=recommendation,
    )


def _grade_and_recommend(
    avg_grade: float, avg_wps: float, complex_pct: float, fre: float
) -> tuple[str, str]:
    """Generate grade and actionable recommendation."""
    issues: list[str] = []

    if avg_wps > 25:
        issues.append("sentences are too long (avg > 25 words)")
    if complex_pct > 30:
        issues.append(f"high jargon density ({complex_pct}% complex words)")
    if fre < 30:
        issues.append("very low reading ease — consider simplifying")

    if avg_grade <= 10:
        grade = "EASY"
    elif avg_grade <= 14:
        grade = "MODERATE"
    elif avg_grade <= 18:
        grade = "COMPLEX"
    else:
        grade = "VERY_COMPLEX"

    if not issues:
        recommendation = "Spec readability is appropriate for technical documentation."
    else:
        recommendation = "Consider: " + "; ".join(issues) + "."

    return grade, recommendation
