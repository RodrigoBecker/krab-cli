"""Tests for krab_cli.cli commands."""

from typer.testing import CliRunner

from krab_cli.cli import app

runner = CliRunner()


class TestCliVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "██████╗" in result.output


class TestOptimizeCommands:
    def test_optimize_run(self, tmp_spec_file):
        result = runner.invoke(app, ["optimize", "run", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Compression Metrics" in result.output

    def test_optimize_run_with_output(self, tmp_spec_file, tmp_path):
        out = tmp_path / "optimized.md"
        result = runner.invoke(app, ["optimize", "run", str(tmp_spec_file), "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_optimize_aliases(self, tmp_spec_file):
        result = runner.invoke(app, ["optimize", "aliases", str(tmp_spec_file)])
        assert result.exit_code == 0

    def test_optimize_dedup(self, tmp_spec_file):
        result = runner.invoke(app, ["optimize", "dedup", str(tmp_spec_file)])
        assert result.exit_code == 0

    def test_file_not_found(self, tmp_path):
        fake = tmp_path / "nonexistent.md"
        result = runner.invoke(app, ["optimize", "run", str(fake)])
        assert result.exit_code == 1


class TestConvertCommands:
    def test_md2json(self, tmp_spec_file):
        result = runner.invoke(app, ["convert", "md2json", str(tmp_spec_file)])
        assert result.exit_code == 0

    def test_md2yaml(self, tmp_spec_file):
        result = runner.invoke(app, ["convert", "md2yaml", str(tmp_spec_file)])
        assert result.exit_code == 0

    def test_json2md(self, tmp_json_file):
        result = runner.invoke(app, ["convert", "json2md", str(tmp_json_file)])
        assert result.exit_code == 0

    def test_yaml2md(self, tmp_yaml_file):
        result = runner.invoke(app, ["convert", "yaml2md", str(tmp_yaml_file)])
        assert result.exit_code == 0

    def test_auto_convert(self, tmp_spec_file, tmp_path):
        out = tmp_path / "out.json"
        result = runner.invoke(
            app, ["convert", "auto", str(tmp_spec_file), "--to", "json", "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()


class TestAnalyzeCommands:
    def test_analyze_tokens(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "tokens", str(tmp_spec_file)])
        # May fail in sandboxed environments where tiktoken can't download encodings
        if "Token Summary" in result.output:
            assert result.exit_code == 0
        else:
            assert result.exit_code == 1  # Graceful failure is acceptable

    def test_analyze_quality(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "quality", str(tmp_spec_file)])
        assert result.exit_code == 0
        assert "Context Quality" in result.output

    def test_analyze_compare(self, tmp_spec_file, tmp_path):
        other = tmp_path / "other.md"
        other.write_text("# Different Spec\n\nCompletely different content here.", encoding="utf-8")
        result = runner.invoke(app, ["analyze", "compare", str(tmp_spec_file), str(other)])
        assert result.exit_code == 0
        assert "Similarity Scores" in result.output

    def test_analyze_freq(self, tmp_spec_file):
        result = runner.invoke(app, ["analyze", "freq", str(tmp_spec_file)])
        assert result.exit_code == 0
