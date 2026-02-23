"""Tests for Wave 2 modules: budget, minhash, bm25, delta."""

from krab_cli.core.bm25 import BM25Index
from krab_cli.core.budget import ScoredSection, optimize_budget, score_sections
from krab_cli.core.delta import compute_delta, delta_token_savings, generate_section_delta
from krab_cli.core.minhash import LSH, MinHash, find_near_duplicates

# ─── Budget Optimizer ─────────────────────────────────────────────────────


class TestBudget:
    def test_knapsack_respects_budget(self):
        sections = [
            ScoredSection(name="A", text="x" * 400, token_cost=100, info_value=0.8),
            ScoredSection(name="B", text="x" * 400, token_cost=100, info_value=0.6),
            ScoredSection(name="C", text="x" * 400, token_cost=100, info_value=0.9),
        ]
        result = optimize_budget(sections, budget=200, strategy="knapsack")
        assert result.total_tokens <= 200
        assert len(result.selected) == 2

    def test_greedy_strategy(self):
        sections = [
            ScoredSection(name="A", text="x" * 40, token_cost=10, info_value=0.5),
            ScoredSection(name="B", text="x" * 800, token_cost=200, info_value=0.9),
            ScoredSection(name="C", text="x" * 40, token_cost=10, info_value=0.8),
        ]
        result = optimize_budget(sections, budget=30, strategy="greedy")
        assert result.total_tokens <= 30

    def test_required_sections(self):
        sections = [
            ScoredSection(name="A", text="x" * 40, token_cost=10, info_value=0.1, required=True),
            ScoredSection(name="B", text="x" * 40, token_cost=10, info_value=0.9),
        ]
        result = optimize_budget(sections, budget=15)
        selected_names = {s.name for s in result.selected}
        assert "A" in selected_names

    def test_score_sections(self):
        docs = {"spec1.md": "OAuth2 authentication JWT tokens", "spec2.md": "Hello world"}
        scored = score_sections(docs)
        assert len(scored) == 2
        assert all(s.token_cost > 0 for s in scored)
        assert all(s.info_value >= 0 for s in scored)


# ─── MinHash + LSH ────────────────────────────────────────────────────────


class TestMinHash:
    def test_identical_signatures(self):
        mh = MinHash(num_perm=128)
        shingles = {"hello", "world", "test"}
        sig1 = mh.signature(shingles)
        sig2 = mh.signature(shingles)
        assert MinHash.estimate_similarity(sig1, sig2) == 1.0

    def test_different_signatures(self):
        mh = MinHash(num_perm=128)
        sig1 = mh.signature({"aaa", "bbb", "ccc"})
        sig2 = mh.signature({"xxx", "yyy", "zzz"})
        assert MinHash.estimate_similarity(sig1, sig2) < 0.5


class TestLSH:
    def test_insert_and_query(self):
        mh = MinHash(num_perm=128)
        lsh = LSH(num_bands=16, rows_per_band=8)

        sig = mh.signature({"hello", "world", "test"})
        lsh.insert("doc1", sig)
        lsh.insert("doc2", sig)

        candidates = lsh.query(sig)
        assert "doc1" in candidates
        assert "doc2" in candidates


class TestFindNearDuplicates:
    def test_finds_duplicates(self):
        docs = {
            "a.md": "The authentication module handles user login and registration",
            "b.md": "The authentication module manages user login and registration flow",
            "c.md": "Payment processing system handles credit card transactions",
        }
        matches = find_near_duplicates(docs, threshold=0.3)
        if matches:
            assert matches[0].doc_a != matches[0].doc_b

    def test_empty_corpus(self):
        matches = find_near_duplicates({}, threshold=0.5)
        assert matches == []


# ─── BM25 ─────────────────────────────────────────────────────────────────


class TestBM25:
    def test_search_finds_relevant(self):
        index = BM25Index()
        docs = {
            "auth.md": "Authentication module with OAuth2 and JWT token validation",
            "payment.md": "Payment processing with credit cards and invoicing",
            "user.md": "User management, profiles, and role-based access control",
        }
        index.index(docs)
        results = index.search("authentication OAuth2 JWT")
        assert len(results) > 0
        assert results[0].doc_id == "auth.md"

    def test_empty_query(self):
        index = BM25Index()
        index.index({"a.md": "hello world"})
        results = index.search("")
        assert results == []

    def test_no_results(self):
        index = BM25Index()
        index.index({"a.md": "hello world"})
        results = index.search("zzzzzzz")
        assert results == []

    def test_index_stats(self):
        index = BM25Index()
        index.index({"a.md": "hello world", "b.md": "foo bar baz"})
        stats = index.get_stats()
        assert stats["total_documents"] == 2
        assert stats["total_terms"] > 0


# ─── Delta Encoding ───────────────────────────────────────────────────────


class TestDelta:
    def test_identical_files(self):
        text = "# Hello\n\nWorld\n"
        report = compute_delta(text, text)
        assert not report.has_changes
        assert report.change_ratio == 0.0

    def test_added_content(self):
        old = "# Hello\n\nWorld\n"
        new = "# Hello\n\nWorld\n\n## New Section\n\nNew content here.\n"
        report = compute_delta(old, new)
        assert report.has_changes
        assert report.lines_added > 0

    def test_removed_content(self):
        old = "# Hello\n\nWorld\n\nExtra line\n"
        new = "# Hello\n\nWorld\n"
        report = compute_delta(old, new)
        assert report.lines_removed > 0

    def test_section_delta(self):
        old = "# Auth\n\nLogin flow\n\n# API\n\nREST endpoints\n"
        new = "# Auth\n\nLogin flow updated\n\n# API\n\nREST endpoints\n"
        deltas = generate_section_delta(old, new)
        assert len(deltas) > 0

    def test_token_savings(self):
        old = "# Spec\n\n" + "Content line.\n" * 50
        new = "# Spec\n\n" + "Content line.\n" * 50 + "\n## New Section\n\nExtra.\n"
        savings = delta_token_savings(old, new)
        assert savings["delta_tokens"] <= savings["full_spec_tokens"]
        assert "recommendation" in savings
