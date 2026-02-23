"""Tests for Wave 1 modules: entropy, readability, ambiguity, substrings."""

from krab_cli.core.ambiguity import detect_ambiguity
from krab_cli.core.entropy import (
    estimated_perplexity,
    full_entropy_analysis,
    markov_predictability,
    shannon_entropy,
)
from krab_cli.core.readability import (
    flesch_kincaid_grade,
    flesch_reading_ease,
    full_readability_analysis,
    gunning_fog_index,
)
from krab_cli.core.substrings import find_repeated_phrases, total_waste_analysis

# ─── Entropy ──────────────────────────────────────────────────────────────


class TestShannonEntropy:
    def test_uniform_distribution(self):
        # All unique words -> high entropy
        text = "alpha bravo charlie delta echo foxtrot golf hotel india"
        e = shannon_entropy(text)
        assert e > 3.0

    def test_repetitive_text(self):
        text = "the the the the the the the the"
        e = shannon_entropy(text)
        assert e == 0.0

    def test_empty_text(self):
        assert shannon_entropy("") == 0.0


class TestMarkov:
    def test_predictable_text(self):
        text = "the system must the system must the system must the system must"
        m = markov_predictability(text, order=1)
        assert m.predictability > 0.5

    def test_varied_text(self, sample_md):
        m = markov_predictability(sample_md, order=1)
        assert m.total_transitions > 0
        assert m.unique_transitions > 0


class TestPerplexity:
    def test_repetitive_low_perplexity(self):
        text = "the cat sat on the mat the cat sat on the mat the cat sat on the mat"
        p = estimated_perplexity(text)
        assert p < 20

    def test_short_text(self):
        assert estimated_perplexity("hi") == 0.0


class TestFullEntropy:
    def test_complete_report(self, sample_md):
        report = full_entropy_analysis(sample_md)
        assert report.entropy > 0
        assert report.token_count > 0
        assert report.unique_tokens > 0
        assert report.vocabulary_richness > 0
        assert report.entropy_grade != ""
        assert report.perplexity_grade != ""


# ─── Readability ──────────────────────────────────────────────────────────


class TestReadability:
    def test_flesch_kincaid(self, sample_md):
        grade = flesch_kincaid_grade(sample_md)
        assert grade >= 0

    def test_flesch_reading_ease(self, sample_md):
        ease = flesch_reading_ease(sample_md)
        assert 0 <= ease <= 100

    def test_gunning_fog(self, sample_md):
        fog = gunning_fog_index(sample_md)
        assert fog >= 0

    def test_full_report(self, sample_md):
        report = full_readability_analysis(sample_md)
        assert report.word_count > 0
        assert report.sentence_count > 0
        assert report.overall_grade in ("EASY", "MODERATE", "COMPLEX", "VERY_COMPLEX")
        assert report.recommendation != ""


# ─── Ambiguity ────────────────────────────────────────────────────────────


class TestAmbiguity:
    def test_detects_vague_terms(self):
        text = "The system should handle approximately 100 users etc."
        report = detect_ambiguity(text)
        assert report.ambiguous_terms > 0
        terms = [m.term for m in report.matches]
        assert "etc" in terms or "approximately" in terms

    def test_clean_text(self):
        text = "The POST /auth/login endpoint accepts email and password parameters."
        report = detect_ambiguity(text)
        assert report.precision_score > 50

    def test_detects_tbd(self):
        text = "The timeout value is TBD. The retry count is TODO."
        report = detect_ambiguity(text)
        high_matches = [m for m in report.matches if m.severity == "HIGH"]
        assert len(high_matches) >= 2

    def test_empty_text(self):
        report = detect_ambiguity("")
        assert report.precision_score == 100.0

    def test_report_structure(self, sample_md):
        report = detect_ambiguity(sample_md)
        assert report.total_words > 0
        assert isinstance(report.severity_counts, dict)
        assert report.grade in ("EXCELLENT", "GOOD", "FAIR", "POOR")


# ─── Substrings ───────────────────────────────────────────────────────────


class TestRepeatedPhrases:
    def test_finds_repeated(self):
        text = (
            "The system must implement rate limiting. "
            "The system must implement brute force protection. "
            "The system must implement logging. "
        )
        phrases = find_repeated_phrases(text, min_words=3, min_count=2)
        assert len(phrases) > 0
        assert any("system must implement" in p.text for p in phrases)

    def test_no_repeats(self):
        text = "Alpha bravo charlie. Delta echo foxtrot."
        phrases = find_repeated_phrases(text, min_words=3, min_count=2)
        assert len(phrases) == 0


class TestWasteAnalysis:
    def test_basic_waste(self, sample_md):
        waste = total_waste_analysis(sample_md)
        assert "repeated_phrases" in waste
        assert "estimated_token_savings" in waste
        assert waste["text_length"] > 0
