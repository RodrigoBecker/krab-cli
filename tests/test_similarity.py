"""Tests for krab_cli.core.similarity."""

from krab_cli.core.similarity import (
    context_quality_score,
    cosine_similarity,
    full_comparison,
    jaccard_similarity,
    ngram_overlap,
    tfidf_similarity,
    tokenize,
)


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("Hello World! This is a test.")
        assert "hello" in tokens
        assert "world" in tokens

    def test_empty(self):
        assert tokenize("") == []


class TestJaccard:
    def test_identical(self):
        assert jaccard_similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert jaccard_similarity("abc def", "xyz uvw") == 0.0

    def test_partial_overlap(self):
        score = jaccard_similarity("the quick brown fox", "the lazy brown dog")
        assert 0.0 < score < 1.0


class TestCosine:
    def test_identical(self):
        score = cosine_similarity("hello world", "hello world")
        assert abs(score - 1.0) < 0.001

    def test_orthogonal(self):
        score = cosine_similarity("aaa bbb", "ccc ddd")
        assert score == 0.0


class TestNgramOverlap:
    def test_identical(self):
        score = ngram_overlap("the quick brown fox", "the quick brown fox")
        assert score == 1.0

    def test_partial(self):
        score = ngram_overlap("the quick brown fox", "the quick red fox")
        assert 0.0 < score < 1.0


class TestTfidf:
    def test_similar_docs(self):
        docs = [
            "authentication module login user",
            "authentication module logout user",
            "payment processing credit card",
        ]
        score_01 = tfidf_similarity(docs, 0, 1)
        score_02 = tfidf_similarity(docs, 0, 2)
        assert score_01 > score_02

    def test_single_doc(self):
        assert tfidf_similarity(["only one"], 0, 0) == 0.0


class TestFullComparison:
    def test_returns_report(self):
        report = full_comparison(
            "The authentication module handles user login",
            "The authentication module manages user login",
        )
        assert report.jaccard > 0.5
        assert report.cosine > 0.5
        assert report.combined > 0.5
        assert report.verdict in (
            "DUPLICATE",
            "HIGH_SIMILARITY",
            "MODERATE_SIMILARITY",
            "LOW_SIMILARITY",
        )

    def test_different_texts(self):
        report = full_comparison("abc def ghi", "xyz uvw rst")
        assert report.combined < 0.3


class TestContextQuality:
    def test_basic_quality(self, sample_md):
        quality = context_quality_score(sample_md, context_window=8192)
        assert "word_count" in quality
        assert "estimated_tokens" in quality
        assert "information_density" in quality
        assert "density_grade" in quality
        assert quality["word_count"] > 0

    def test_custom_window(self):
        text = "hello world " * 100
        quality = context_quality_score(text, context_window=200)
        assert quality["utilization_pct"] > 0
