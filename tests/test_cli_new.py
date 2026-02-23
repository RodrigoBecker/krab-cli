"""Tests for new CLI commands (Wave 1-3)."""

from typer.testing import CliRunner

from krab_cli.cli import app

runner = CliRunner()


class TestAnalyzeNewCommands:
    def test_entropy(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "entropy", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Entropy" in result.output

    def test_readability(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "readability", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Readability" in result.output

    def test_ambiguity(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "ambiguity", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Precision" in result.output

    def test_substrings(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "substrings", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Waste" in result.output or "Repeated" in result.output

    def test_risk(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "risk", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Risk" in result.output

    def test_chunking(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "chunking", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Strategy" in result.output

    def test_keywords(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "keywords", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "RAKE" in result.output or "Keyword" in result.output


class TestSearchCommands:
    def test_bm25_search(self, tmp_path):
        # Create test specs
        (tmp_path / "auth.md").write_text("Authentication OAuth2 JWT token validation login")
        (tmp_path / "payment.md").write_text("Payment processing credit card billing invoice")
        result = runner.invoke(
            app, ["search", "bm25", str(tmp_path), "-q", "authentication OAuth2"]
        )
        assert result.exit_code == 0

    def test_budget(self, tmp_path):
        (tmp_path / "a.md").write_text("# Auth\n\nOAuth2 authentication module.\n")
        (tmp_path / "b.md").write_text("# API\n\nREST endpoints documentation.\n")
        result = runner.invoke(app, ["search", "budget", str(tmp_path), "--budget", "500"])
        assert result.exit_code == 0

    def test_duplicates(self, tmp_path):
        (tmp_path / "a.md").write_text(
            "The authentication module handles user login and registration"
        )
        (tmp_path / "b.md").write_text(
            "The authentication module manages user login and registration flow"
        )
        result = runner.invoke(app, ["search", "duplicates", str(tmp_path), "--threshold", "0.3"])
        assert result.exit_code == 0


class TestDiffCommands:
    def test_diff_versions(self, tmp_path):
        old = tmp_path / "v1.md"
        new = tmp_path / "v2.md"
        old.write_text("# Auth\n\nLogin flow\n\n## API\n\nREST endpoints\n")
        new.write_text(
            "# Auth\n\nLogin flow updated\n\n## API\n\nREST endpoints\n\n## New\n\nAdded.\n"
        )
        result = runner.invoke(app, ["diff", "versions", str(old), str(new)])
        assert result.exit_code == 0
        assert "Delta" in result.output

    def test_diff_sections(self, tmp_path):
        old = tmp_path / "v1.md"
        new = tmp_path / "v2.md"
        old.write_text("# Auth\n\nLogin\n\n# API\n\nEndpoints\n")
        new.write_text("# Auth\n\nLogin updated\n\n# API\n\nEndpoints\n")
        result = runner.invoke(app, ["diff", "sections", str(old), str(new)])
        assert result.exit_code == 0
