"""Tests for Wave 3 modules: depgraph, chunking, semantic, risk."""

from krab_cli.core.chunking import analyze_strategy, compare_strategies
from krab_cli.core.depgraph import build_dependency_graph
from krab_cli.core.risk import assess_hallucination_risk
from krab_cli.core.semantic import rake_extract, semantic_compress, textrank_sentences

# ─── Dependency Graph ─────────────────────────────────────────────────────


class TestDependencyGraph:
    def test_builds_graph(self):
        specs = {
            "auth-spec.md": "Authentication with OAuth2 and JWT token management for user login",
            "user-spec.md": "User management module, see `auth-spec.md` for authentication details",
            "payment-spec.md": "Payment processing with credit card billing and invoicing",
        }
        graph = build_dependency_graph(specs)
        assert graph.node_count == 3
        assert graph.node_count > 0

    def test_keyword_connections(self):
        specs = {
            "auth.md": "Authentication module handles user login with session tokens and JWT validation",
            "session.md": "Session management handles user session tokens and cookie validation",
        }
        graph = build_dependency_graph(specs)
        assert graph.edge_count > 0

    def test_context_cluster(self):
        specs = {
            "a.md": "See `b.md` for details on authentication",
            "b.md": "See `c.md` for database schema",
            "c.md": "Database schema definitions",
            "d.md": "Completely unrelated payment processing",
        }
        graph = build_dependency_graph(specs)
        cluster = graph.get_context_cluster("a.md", depth=2)
        assert "a.md" in cluster

    def test_mermaid_export(self):
        specs = {
            "auth.md": "Authentication user session token management",
            "user.md": "User profile management with authentication tokens",
        }
        graph = build_dependency_graph(specs)
        mermaid = graph.to_mermaid()
        assert "graph LR" in mermaid

    def test_topological_order(self):
        specs = {"a.md": "Base spec", "b.md": "Depends on a"}
        graph = build_dependency_graph(specs)
        order = graph.topological_order()
        assert len(order) == 2


# ─── Chunking ─────────────────────────────────────────────────────────────


class TestChunking:
    def test_heading_strategy(self, sample_md):
        result = analyze_strategy(sample_md, "heading")
        assert result.total_chunks > 0
        assert result.avg_chunk_tokens > 0

    def test_paragraph_strategy(self, sample_md):
        result = analyze_strategy(sample_md, "paragraph")
        assert result.total_chunks > 0

    def test_semantic_strategy(self, sample_md):
        result = analyze_strategy(sample_md, "semantic")
        assert result.total_chunks > 0

    def test_fixed_size_strategy(self, sample_md):
        result = analyze_strategy(sample_md, "fixed_size")
        assert result.total_chunks > 0

    def test_compare_strategies(self, sample_md):
        results = compare_strategies(sample_md)
        assert len(results) == 4
        # First result should be recommended
        assert "RECOMMENDED" in results[0].recommendation

    def test_unknown_strategy(self):
        import pytest

        with pytest.raises(ValueError):
            analyze_strategy("text", "unknown")


# ─── Semantic Compression ─────────────────────────────────────────────────


class TestRAKE:
    def test_extracts_keywords(self, sample_md):
        keywords = rake_extract(sample_md, top_n=10)
        assert len(keywords) > 0
        assert all(kw.score > 0 for kw in keywords)

    def test_empty_text(self):
        keywords = rake_extract("", top_n=10)
        assert keywords == []

    def test_keyword_structure(self, sample_md):
        keywords = rake_extract(sample_md, top_n=5)
        for kw in keywords:
            assert kw.phrase != ""
            assert kw.word_count >= 1
            assert kw.frequency >= 1


class TestTextRank:
    def test_extracts_sentences(self, sample_md):
        sentences = textrank_sentences(sample_md, top_n=3)
        assert len(sentences) > 0
        for sent, score in sentences:
            assert len(sent) > 0
            assert score > 0

    def test_short_text(self):
        sentences = textrank_sentences("Hello. World.", top_n=5)
        assert len(sentences) <= 5


class TestSemanticCompress:
    def test_compresses(self, sample_md):
        result = semantic_compress(sample_md, target_ratio=0.3)
        assert result.compressed_tokens < result.original_tokens
        assert result.compression_ratio < 1.0
        assert len(result.keywords) > 0
        assert len(result.compressed_text) > 0

    def test_preserves_keywords(self, sample_md):
        result = semantic_compress(sample_md)
        assert "Key concepts:" in result.compressed_text


# ─── Hallucination Risk ──────────────────────────────────────────────────


class TestHallucinationRisk:
    def test_basic_assessment(self, sample_md):
        report = assess_hallucination_risk(sample_md)
        assert 0 <= report.overall_score <= 100
        assert report.risk_level in ("LOW", "MODERATE", "HIGH", "CRITICAL")
        assert len(report.factors) == 6
        assert len(report.recommendations) > 0

    def test_vague_spec_high_risk(self):
        vague = (
            "The system should probably do some things approximately "
            "as needed. TBD on the details etc. Various items might be "
            "implemented eventually when possible if necessary. "
            "Several components could be adequate."
        )
        report = assess_hallucination_risk(vague)
        assert report.overall_score > 20  # Should flag some risk

    def test_precise_spec_lower_risk(self):
        precise = (
            "# Authentication API\n\n"
            "## POST /auth/login\n\n"
            "Accepts JSON body with email (string, required) and password (string, required). "
            "Returns 200 with JWT access_token (expires in 3600 seconds) and refresh_token. "
            "Returns 401 on invalid credentials. Rate limited to 5 requests per minute per IP.\n\n"
            "## POST /auth/logout\n\n"
            "Accepts Authorization header with Bearer token. "
            "Invalidates the session and returns 204 No Content.\n"
        )
        report = assess_hallucination_risk(precise)
        # Precise spec should have lower risk than vague
        assert report.risk_level in ("LOW", "MODERATE")

    def test_report_factors(self, sample_md):
        report = assess_hallucination_risk(sample_md)
        factor_names = {f.name for f in report.factors}
        assert "Ambiguity" in factor_names
        assert "Information Density" in factor_names
        assert "Readability" in factor_names
        assert "Context Overflow" in factor_names
