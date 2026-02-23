"""MinHash + Locality-Sensitive Hashing for scalable duplicate detection.

Replaces O(n^2) pairwise comparison with O(n) fingerprinting + bucketing.
Essential when the spec corpus grows to dozens or hundreds of files.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass


def _shingle(text: str, k: int = 3) -> set[str]:
    """Create k-shingles (character n-grams) from text."""
    text = re.sub(r"\s+", " ", text.lower().strip())
    if len(text) < k:
        return {text}
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def _word_shingle(text: str, k: int = 2) -> set[str]:
    """Create word-level k-shingles from text."""
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


class MinHash:
    """MinHash signature generator for set similarity estimation.

    Uses random hash permutations to create compact signatures that
    approximate Jaccard similarity in O(1) comparison time.
    """

    def __init__(self, num_perm: int = 128, seed: int = 42):
        self.num_perm = num_perm
        self._rng = random.Random(seed)
        # Generate hash function parameters: h(x) = (ax + b) % p
        self._max_hash = (1 << 32) - 1
        self._prime = 4294967311  # next prime after 2^32
        self._a = [self._rng.randint(1, self._prime - 1) for _ in range(num_perm)]
        self._b = [self._rng.randint(0, self._prime - 1) for _ in range(num_perm)]

    def signature(self, shingles: set[str]) -> list[int]:
        """Compute MinHash signature for a set of shingles."""
        sig = [self._max_hash] * self.num_perm

        for shingle in shingles:
            h = int(hashlib.md5(shingle.encode()).hexdigest(), 16) & self._max_hash
            for i in range(self.num_perm):
                val = (self._a[i] * h + self._b[i]) % self._prime
                if val < sig[i]:
                    sig[i] = val

        return sig

    @staticmethod
    def estimate_similarity(sig_a: list[int], sig_b: list[int]) -> float:
        """Estimate Jaccard similarity from two MinHash signatures."""
        if len(sig_a) != len(sig_b):
            raise ValueError("Signatures must have same length")
        matches = sum(1 for a, b in zip(sig_a, sig_b, strict=True) if a == b)
        return matches / len(sig_a)


class LSH:
    """Locality-Sensitive Hashing for fast candidate pair detection.

    Divides MinHash signatures into bands. Documents sharing at least
    one band are candidate pairs, dramatically reducing comparisons.
    """

    def __init__(self, num_bands: int = 16, rows_per_band: int = 8):
        self.num_bands = num_bands
        self.rows_per_band = rows_per_band
        self._buckets: list[dict[int, list[str]]] = [{} for _ in range(num_bands)]

    def insert(self, doc_id: str, signature: list[int]) -> None:
        """Insert a document's MinHash signature into LSH buckets."""
        for band_idx in range(self.num_bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(signature[start:end])
            band_hash = hash(band)

            if band_hash not in self._buckets[band_idx]:
                self._buckets[band_idx][band_hash] = []
            self._buckets[band_idx][band_hash].append(doc_id)

    def query(self, signature: list[int]) -> set[str]:
        """Find candidate matches for a signature."""
        candidates: set[str] = set()
        for band_idx in range(self.num_bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band = tuple(signature[start:end])
            band_hash = hash(band)

            bucket = self._buckets[band_idx].get(band_hash, [])
            candidates.update(bucket)

        return candidates

    def find_all_candidates(self) -> set[tuple[str, str]]:
        """Find all candidate duplicate pairs across all buckets."""
        pairs: set[tuple[str, str]] = set()
        for band_buckets in self._buckets:
            for doc_ids in band_buckets.values():
                if len(doc_ids) > 1:
                    for i in range(len(doc_ids)):
                        for j in range(i + 1, len(doc_ids)):
                            a, b = sorted([doc_ids[i], doc_ids[j]])
                            pairs.add((a, b))
        return pairs


@dataclass
class LSHMatch:
    """A near-duplicate match found by MinHash + LSH."""

    doc_a: str
    doc_b: str
    estimated_similarity: float


def find_near_duplicates(
    documents: dict[str, str],
    threshold: float = 0.5,
    num_perm: int = 128,
    num_bands: int = 16,
    shingle_mode: str = "word",
    shingle_k: int = 2,
) -> list[LSHMatch]:
    """Find near-duplicate documents using MinHash + LSH.

    Args:
        documents: Dict of {doc_id: text}.
        threshold: Minimum estimated Jaccard similarity.
        num_perm: Number of MinHash permutations (higher = more accurate).
        num_bands: Number of LSH bands (higher = more candidates).
        shingle_mode: 'char' for character shingles, 'word' for word shingles.
        shingle_k: Shingle size (k characters or k words).

    Returns:
        List of LSHMatch above the similarity threshold.
    """
    rows_per_band = num_perm // num_bands

    mh = MinHash(num_perm=num_perm)
    lsh = LSH(num_bands=num_bands, rows_per_band=rows_per_band)

    shingle_fn = _word_shingle if shingle_mode == "word" else _shingle
    signatures: dict[str, list[int]] = {}

    # Generate signatures and insert into LSH
    for doc_id, text in documents.items():
        shingles = shingle_fn(text, k=shingle_k)
        sig = mh.signature(shingles)
        signatures[doc_id] = sig
        lsh.insert(doc_id, sig)

    # Check candidate pairs
    candidate_pairs = lsh.find_all_candidates()
    matches: list[LSHMatch] = []

    for doc_a, doc_b in candidate_pairs:
        sim = mh.estimate_similarity(signatures[doc_a], signatures[doc_b])
        if sim >= threshold:
            matches.append(LSHMatch(doc_a=doc_a, doc_b=doc_b, estimated_similarity=round(sim, 4)))

    matches.sort(key=lambda m: -m.estimated_similarity)
    return matches
