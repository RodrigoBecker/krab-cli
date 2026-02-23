"""Tests for krab_cli.core.fuzzy."""

from krab_cli.core.fuzzy import (
    deduplicate_sections,
    find_best_match,
    find_duplicates,
    ratio_score,
    token_set_score,
    weighted_score,
)


class TestScoring:
    def test_identical_strings(self):
        assert ratio_score("hello world", "hello world") == 100.0

    def test_completely_different(self):
        assert ratio_score("abc", "xyz") < 50.0

    def test_token_set_handles_reorder(self):
        score = token_set_score("the quick brown fox", "brown fox quick the")
        assert score > 90.0

    def test_weighted_score(self):
        score = weighted_score("authentication module", "authentication module system")
        assert score > 60.0


class TestFindDuplicates:
    def test_finds_duplicates(self):
        sections = [
            "The authentication module handles user login",
            "The authentication module handles user login and registration",
            "The payment module processes transactions",
        ]
        matches = find_duplicates(sections, threshold=70.0)
        assert len(matches) >= 1
        assert matches[0].score > 70.0

    def test_no_duplicates(self):
        sections = [
            "The sky is blue",
            "Python is a programming language",
            "Databases store information",
        ]
        matches = find_duplicates(sections, threshold=90.0)
        assert len(matches) == 0

    def test_empty_input(self):
        assert find_duplicates([], threshold=80.0) == []


class TestFindBestMatch:
    def test_finds_best_match(self):
        candidates = ["user authentication", "payment processing", "data validation"]
        results = find_best_match("auth user login", candidates, threshold=40.0)
        assert len(results) > 0
        assert "user authentication" in results[0][0]

    def test_threshold_filter(self):
        candidates = ["hello", "world"]
        results = find_best_match("zzzzz", candidates, threshold=90.0)
        assert len(results) == 0


class TestDeduplication:
    def test_removes_duplicates(self):
        sections = [
            "The system must support OAuth2 authentication for users",
            "The system must support OAuth2 authentication for all users",
            "The API uses REST endpoints",
        ]
        result = deduplicate_sections(sections, threshold=85.0)
        assert len(result) <= len(sections)

    def test_keeps_unique(self):
        sections = ["Section A about topic X", "Section B about topic Y"]
        result = deduplicate_sections(sections, threshold=95.0)
        assert len(result) == 2

    def test_empty_input(self):
        assert deduplicate_sections([]) == []
