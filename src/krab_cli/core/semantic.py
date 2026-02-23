"""Semantic compression using RAKE and TextRank algorithms.

Extracts key terms and concepts from specs to produce compressed summaries
that preserve essential meaning while drastically reducing token count.
Unlike Huffman (syntactic), this operates at the semantic level.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

# ─── RAKE (Rapid Automatic Keyword Extraction) ───────────────────────────

STOP_WORDS: set[str] = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "can",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "and",
    "but",
    "or",
    "not",
    "no",
    "if",
    "then",
    "else",
    "when",
    "while",
    "where",
    "how",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "i",
    "we",
    "you",
    "they",
    "he",
    "she",
    "my",
    "your",
    "our",
    "their",
    "his",
    "her",
    "me",
    "us",
    "them",
    "so",
    "than",
    "too",
    "very",
    "just",
    "about",
    "above",
    "below",
    "between",
    "each",
    "every",
    "all",
    "any",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "only",
    "own",
    "same",
    "also",
    "however",
    "therefore",
    "thus",
    "hence",
    "must",
    "need",
    "needs",
    "using",
    "used",
    "use",
}


@dataclass
class RakeKeyword:
    """A keyword phrase extracted by RAKE."""

    phrase: str
    score: float
    word_count: int
    frequency: int


def rake_extract(
    text: str,
    max_words: int = 4,
    min_freq: int = 1,
    top_n: int = 30,
) -> list[RakeKeyword]:
    """Extract keywords using RAKE algorithm.

    Steps:
    1. Split text into candidate phrases using stop words as delimiters
    2. Calculate word scores based on degree/frequency ratio
    3. Score phrases as sum of word scores
    4. Return top-scoring phrases

    Args:
        text: Input text.
        max_words: Maximum words per keyword phrase.
        min_freq: Minimum frequency to include.
        top_n: Number of top keywords to return.
    """
    # Split into sentences
    sentences = re.split(r"[.!?\n;:]", text.lower())

    # Extract candidate phrases (sequences between stop words)
    phrases_list: list[list[str]] = []
    for sentence in sentences:
        words = re.findall(r"\b[a-z][a-z0-9_-]*\b", sentence)
        current_phrase: list[str] = []

        for word in words:
            if word in STOP_WORDS:
                if current_phrase and len(current_phrase) <= max_words:
                    phrases_list.append(current_phrase)
                current_phrase = []
            else:
                current_phrase.append(word)

        if current_phrase and len(current_phrase) <= max_words:
            phrases_list.append(current_phrase)

    # Count word frequency and degree
    word_freq: dict[str, int] = defaultdict(int)
    word_degree: dict[str, int] = defaultdict(int)

    for phrase in phrases_list:
        degree = len(phrase) - 1
        for word in phrase:
            word_freq[word] += 1
            word_degree[word] += degree

    # Word score = degree(w) + freq(w) / freq(w) = (degree + freq) / freq
    word_score: dict[str, float] = {}
    for word in word_freq:
        word_score[word] = (word_degree[word] + word_freq[word]) / word_freq[word]

    # Score phrases
    phrase_counter: dict[str, int] = defaultdict(int)
    phrase_scores: dict[str, float] = {}

    for phrase in phrases_list:
        phrase_str = " ".join(phrase)
        phrase_counter[phrase_str] += 1
        if phrase_str not in phrase_scores:
            phrase_scores[phrase_str] = sum(word_score.get(w, 0) for w in phrase)

    # Filter and sort
    results: list[RakeKeyword] = []
    for phrase_str, score in phrase_scores.items():
        freq = phrase_counter[phrase_str]
        if freq >= min_freq:
            results.append(
                RakeKeyword(
                    phrase=phrase_str,
                    score=round(score, 4),
                    word_count=len(phrase_str.split()),
                    frequency=freq,
                )
            )

    results.sort(key=lambda k: -k.score)
    return results[:top_n]


# ─── TextRank ─────────────────────────────────────────────────────────────


def textrank_sentences(
    text: str,
    top_n: int = 5,
    damping: float = 0.85,
    iterations: int = 30,
) -> list[tuple[str, float]]:
    """Extract most important sentences using TextRank algorithm.

    Builds a graph where sentences are nodes and edges are weighted by
    word overlap similarity. Applies PageRank-style iteration to find
    the most central/important sentences.

    Args:
        text: Input text.
        top_n: Number of top sentences to return.
        damping: PageRank damping factor.
        iterations: Number of PageRank iterations.
    """
    # Split into sentences
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 20]

    if len(sentences) <= top_n:
        return [(s, 1.0) for s in sentences]

    # Build similarity matrix
    tokenized = [set(re.findall(r"\b\w{3,}\b", s.lower())) for s in sentences]
    n = len(sentences)
    similarity = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            if not tokenized[i] or not tokenized[j]:
                continue
            overlap = len(tokenized[i] & tokenized[j])
            norm = (len(tokenized[i]) + len(tokenized[j])) / 2
            if norm > 0:
                sim = overlap / norm
                similarity[i][j] = sim
                similarity[j][i] = sim

    # PageRank iteration
    scores = [1.0 / n] * n

    for _ in range(iterations):
        new_scores = [0.0] * n
        for i in range(n):
            rank_sum = 0.0
            for j in range(n):
                if i == j:
                    continue
                out_sum = sum(similarity[j])
                if out_sum > 0:
                    rank_sum += similarity[j][i] * scores[j] / out_sum

            new_scores[i] = (1 - damping) / n + damping * rank_sum
        scores = new_scores

    # Return top-n sentences
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    return [(sentences[idx], round(score, 4)) for idx, score in ranked[:top_n]]


# ─── Semantic Compression ─────────────────────────────────────────────────


@dataclass
class SemanticSummary:
    """Result of semantic compression."""

    keywords: list[RakeKeyword]
    key_sentences: list[tuple[str, float]]
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float


def semantic_compress(
    text: str,
    target_ratio: float = 0.3,
    max_keywords: int = 20,
) -> SemanticSummary:
    """Compress a spec semantically, preserving key concepts.

    Combines RAKE keywords with TextRank sentences to produce a
    compressed version that retains the most important information.

    Args:
        text: Input spec text.
        target_ratio: Target size as fraction of original (0.3 = 30%).
        max_keywords: Maximum keywords to extract.
    """
    original_tokens = len(text) // 4

    keywords = rake_extract(text, top_n=max_keywords)
    target_sentences = max(3, int(len(re.split(r"(?<=[.!?])\s+", text)) * target_ratio))
    key_sentences = textrank_sentences(text, top_n=target_sentences)

    # Build compressed text
    parts: list[str] = []

    # Add keyword summary
    kw_line = "Key concepts: " + ", ".join(k.phrase for k in keywords[:15])
    parts.append(kw_line)
    parts.append("")

    # Add key sentences in original order
    all_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentence_texts = {s for s, _ in key_sentences}

    for sentence in all_sentences:
        stripped = sentence.strip()
        if stripped in sentence_texts:
            parts.append(stripped)

    compressed = "\n".join(parts)
    compressed_tokens = len(compressed) // 4

    return SemanticSummary(
        keywords=keywords,
        key_sentences=key_sentences,
        compressed_text=compressed,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=round(compressed_tokens / original_tokens, 4) if original_tokens else 0,
    )
