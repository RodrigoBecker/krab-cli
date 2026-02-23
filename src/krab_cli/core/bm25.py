"""BM25 ranking for spec search and retrieval.

Superior to TF-IDF for ranking document relevance. Normalizes for document
length and applies diminishing returns on term frequency, producing more
accurate results when an agent needs to find "which spec covers X?".
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, filtering stop words."""
    stop_words = {
        "the",
        "a",
        "an",
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
        "and",
        "but",
        "or",
        "not",
        "no",
        "if",
        "then",
        "this",
        "that",
        "it",
        "its",
        "which",
        "who",
        "whom",
        "what",
        "where",
    }
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if w not in stop_words and len(w) > 1]


@dataclass
class BM25Index:
    """BM25 search index over a corpus of documents.

    Parameters:
        k1: Term frequency saturation parameter (default 1.5).
            Higher values give more weight to term frequency.
        b: Length normalization parameter (default 0.75).
            0 = no normalization, 1 = full normalization.
    """

    k1: float = 1.5
    b: float = 0.75
    _docs: dict[str, list[str]] = field(default_factory=dict)
    _doc_lengths: dict[str, int] = field(default_factory=dict)
    _avg_dl: float = 0.0
    _df: dict[str, int] = field(default_factory=dict)
    _n: int = 0

    def index(self, documents: dict[str, str]) -> None:
        """Build the BM25 index from documents.

        Args:
            documents: Dict of {doc_id: text}.
        """
        self._docs = {}
        self._doc_lengths = {}
        self._df = {}
        self._n = len(documents)

        total_length = 0

        for doc_id, text in documents.items():
            tokens = _tokenize(text)
            self._docs[doc_id] = tokens
            self._doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)

            # Count document frequency (unique terms per doc)
            unique_terms = set(tokens)
            for term in unique_terms:
                self._df[term] = self._df.get(term, 0) + 1

        self._avg_dl = total_length / self._n if self._n > 0 else 0

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        """Search the index with a query string.

        Args:
            query: Search query text.
            top_k: Number of top results to return.

        Returns:
            List of BM25Result sorted by relevance score.
        """
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        scores: dict[str, float] = {}

        for doc_id, doc_tokens in self._docs.items():
            score = self._score_document(query_terms, doc_id, doc_tokens)
            if score > 0:
                scores[doc_id] = score

        # Sort and return top-k
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]

        results: list[BM25Result] = []
        for rank, (doc_id, score) in enumerate(ranked, 1):
            # Find matching terms
            doc_term_set = set(self._docs[doc_id])
            matched = [t for t in query_terms if t in doc_term_set]

            results.append(
                BM25Result(
                    doc_id=doc_id,
                    score=round(score, 4),
                    rank=rank,
                    matched_terms=list(set(matched)),
                    doc_length=self._doc_lengths[doc_id],
                )
            )

        return results

    def _score_document(
        self,
        query_terms: list[str],
        doc_id: str,
        doc_tokens: list[str],
    ) -> float:
        """Calculate BM25 score for a single document."""
        dl = self._doc_lengths[doc_id]
        score = 0.0

        # Count term frequencies in document
        tf_map: dict[str, int] = {}
        for token in doc_tokens:
            tf_map[token] = tf_map.get(token, 0) + 1

        for term in query_terms:
            if term not in tf_map:
                continue

            tf = tf_map[term]
            df = self._df.get(term, 0)

            # IDF component with smoothing
            idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1)

            # TF component with saturation and length normalization
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (dl / self._avg_dl))
            tf_norm = numerator / denominator

            score += idf * tf_norm

        return score

    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            "total_documents": self._n,
            "total_terms": len(self._df),
            "avg_doc_length": round(self._avg_dl, 1),
            "min_doc_length": min(self._doc_lengths.values()) if self._doc_lengths else 0,
            "max_doc_length": max(self._doc_lengths.values()) if self._doc_lengths else 0,
        }


@dataclass
class BM25Result:
    """A single BM25 search result."""

    doc_id: str
    score: float
    rank: int
    matched_terms: list[str]
    doc_length: int
