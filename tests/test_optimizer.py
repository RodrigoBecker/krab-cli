"""Tests for krab_cli.core.optimizer."""

from krab_cli.core.optimizer import optimize_spec, reassemble_sections, split_into_sections


class TestSplitSections:
    def test_splits_by_headings(self, sample_md):
        sections = split_into_sections(sample_md)
        assert len(sections) > 1

    def test_reassemble(self, sample_md):
        sections = split_into_sections(sample_md)
        reassembled = reassemble_sections(sections)
        assert len(reassembled) > 0


class TestOptimizeSpec:
    def test_full_pipeline(self, sample_md):
        result = optimize_spec(sample_md)
        assert result.optimized_text
        assert result.compression_metrics["original_chars"] > 0
        assert result.quality_before["word_count"] > 0
        assert result.quality_after["word_count"] > 0

    def test_compression_reduces_body(self, sample_md):
        result = optimize_spec(sample_md, min_freq=2)
        # Body text should be shorter even if glossary adds overhead
        assert len(result.optimized_text) <= len(result.original_text)

    def test_no_compress(self, sample_md):
        result = optimize_spec(sample_md, compress=False)
        assert result.aliases == {}
        assert result.glossary == ""

    def test_no_dedup(self, sample_md):
        result = optimize_spec(sample_md, deduplicate=False)
        assert result.sections_removed == 0

    def test_final_output(self, sample_md):
        result = optimize_spec(sample_md)
        output = result.final_output
        assert len(output) > 0
