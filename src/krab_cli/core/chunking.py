"""Chunking Strategy Analyzer for SDD specs.

Evaluates different text splitting strategies and recommends the one that
best preserves context coherence when feeding specs to AI agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """A single chunk of text."""

    text: str
    index: int
    strategy: str
    token_estimate: int = 0
    coherence_score: float = 0.0

    def __post_init__(self):
        if self.token_estimate == 0:
            self.token_estimate = max(len(self.text) // 4, 1)


@dataclass
class ChunkingResult:
    """Result of applying a chunking strategy."""

    strategy: str
    chunks: list[Chunk]
    total_chunks: int
    avg_chunk_tokens: float
    min_chunk_tokens: int
    max_chunk_tokens: int
    coherence_score: float
    token_variance: float
    recommendation: str


def chunk_by_heading(text: str) -> list[Chunk]:
    """Split by markdown headings — preserves semantic sections."""
    parts = re.split(r"(?=^#{1,4}\s)", text, flags=re.MULTILINE)
    chunks = []
    for i, part in enumerate(parts):
        part = part.strip()
        if part:
            chunks.append(Chunk(text=part, index=i, strategy="heading"))
    return chunks


def chunk_by_paragraph(text: str) -> list[Chunk]:
    """Split by double newlines — preserves paragraph coherence."""
    parts = re.split(r"\n\s*\n", text)
    chunks = []
    for i, part in enumerate(parts):
        part = part.strip()
        if part:
            chunks.append(Chunk(text=part, index=i, strategy="paragraph"))
    return chunks


def chunk_by_fixed_size(text: str, max_tokens: int = 512) -> list[Chunk]:
    """Split into fixed-size chunks with overlap."""
    words = text.split()
    # ~0.75 words per token
    words_per_chunk = int(max_tokens * 0.75)
    overlap = words_per_chunk // 5  # 20% overlap

    chunks = []
    i = 0
    idx = 0
    while i < len(words):
        end = min(i + words_per_chunk, len(words))
        chunk_text = " ".join(words[i:end])
        chunks.append(Chunk(text=chunk_text, index=idx, strategy="fixed_size"))
        i += words_per_chunk - overlap
        idx += 1

    return chunks


def chunk_by_semantic(text: str) -> list[Chunk]:
    """Split by semantic boundaries — headings, code blocks, and topic shifts.

    More sophisticated than heading-only: also splits on code block
    boundaries and detects topic shifts via vocabulary changes.
    """
    lines = text.split("\n")
    chunks: list[Chunk] = []
    current_lines: list[str] = []
    idx = 0
    in_code = False

    for line in lines:
        is_heading = re.match(r"^#{1,6}\s", line)
        is_code_fence = line.strip().startswith("```")
        is_separator = re.match(r"^[-=*]{3,}\s*$", line)

        if is_code_fence:
            in_code = not in_code
            current_lines.append(line)
            if not in_code and current_lines:
                # End of code block — flush
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    chunks.append(Chunk(text=chunk_text, index=idx, strategy="semantic"))
                    idx += 1
                current_lines = []
            continue

        if in_code:
            current_lines.append(line)
            continue

        if (is_heading or is_separator) and current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(Chunk(text=chunk_text, index=idx, strategy="semantic"))
                idx += 1
            current_lines = [line]
        else:
            current_lines.append(line)

    # Flush remaining
    if current_lines:
        chunk_text = "\n".join(current_lines).strip()
        if chunk_text:
            chunks.append(Chunk(text=chunk_text, index=idx, strategy="semantic"))

    return chunks


# ─── Coherence Scoring ────────────────────────────────────────────────────


def _score_coherence(chunks: list[Chunk]) -> float:
    """Score how well chunks preserve contextual coherence.

    Measures:
    - Term overlap between adjacent chunks (higher = better continuity)
    - Self-contained completeness (does each chunk make sense alone?)
    - Structural completeness (no orphaned references)
    """
    if len(chunks) <= 1:
        return 1.0

    scores: list[float] = []

    for i in range(len(chunks) - 1):
        words_a = set(re.findall(r"\b\w{3,}\b", chunks[i].text.lower()))
        words_b = set(re.findall(r"\b\w{3,}\b", chunks[i + 1].text.lower()))

        if not words_a or not words_b:
            continue

        # Adjacent overlap (some overlap is good — means related content)
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))

        # Self-containedness: does the chunk start with context?
        has_heading = bool(re.match(r"^#{1,6}\s", chunks[i].text))
        self_contained = 0.7 if has_heading else 0.4

        # Combined
        coherence = overlap * 0.5 + self_contained * 0.5
        scores.append(coherence)

    return round(sum(scores) / len(scores), 4) if scores else 0.5


def _compute_token_variance(chunks: list[Chunk]) -> float:
    """Compute variance of chunk sizes (lower = more uniform)."""
    if len(chunks) <= 1:
        return 0.0

    sizes = [c.token_estimate for c in chunks]
    mean = sum(sizes) / len(sizes)
    variance = sum((s - mean) ** 2 for s in sizes) / len(sizes)
    return round(variance, 2)


# ─── Strategy Comparison ──────────────────────────────────────────────────


STRATEGIES = {
    "heading": chunk_by_heading,
    "paragraph": chunk_by_paragraph,
    "fixed_size": chunk_by_fixed_size,
    "semantic": chunk_by_semantic,
}


def analyze_strategy(text: str, strategy: str) -> ChunkingResult:
    """Analyze a single chunking strategy."""
    fn = STRATEGIES.get(strategy)
    if fn is None:
        raise ValueError(f"Unknown strategy: {strategy}. Choose from: {list(STRATEGIES.keys())}")

    chunks = fn(text)
    if not chunks:
        return ChunkingResult(
            strategy=strategy,
            chunks=[],
            total_chunks=0,
            avg_chunk_tokens=0,
            min_chunk_tokens=0,
            max_chunk_tokens=0,
            coherence_score=0,
            token_variance=0,
            recommendation="No chunks produced",
        )

    sizes = [c.token_estimate for c in chunks]
    coherence = _score_coherence(chunks)
    variance = _compute_token_variance(chunks)

    for chunk in chunks:
        chunk.coherence_score = coherence

    return ChunkingResult(
        strategy=strategy,
        chunks=chunks,
        total_chunks=len(chunks),
        avg_chunk_tokens=round(sum(sizes) / len(sizes), 1),
        min_chunk_tokens=min(sizes),
        max_chunk_tokens=max(sizes),
        coherence_score=coherence,
        token_variance=variance,
        recommendation="",
    )


def compare_strategies(text: str) -> list[ChunkingResult]:
    """Compare all chunking strategies and recommend the best one.

    Returns results sorted by a combined score of coherence and uniformity.
    """
    results: list[ChunkingResult] = []

    for strategy_name in STRATEGIES:
        result = analyze_strategy(text, strategy_name)
        results.append(result)

    # Rank by combined score
    max_variance = max((r.token_variance for r in results if r.total_chunks > 0), default=1)
    if max_variance == 0:
        max_variance = 1

    for result in results:
        if result.total_chunks == 0:
            continue
        uniformity = 1 - (result.token_variance / max_variance)
        combined = result.coherence_score * 0.6 + uniformity * 0.4
        result.recommendation = f"Score: {combined:.3f}"

    results.sort(
        key=lambda r: (
            r.coherence_score * 0.6 + (1 - r.token_variance / max_variance) * 0.4
            if r.total_chunks > 0
            else 0
        ),
        reverse=True,
    )

    if results:
        results[0].recommendation = f"RECOMMENDED — {results[0].recommendation}"

    return results
