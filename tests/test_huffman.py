"""Tests for krab_cli.core.huffman."""

from krab_cli.core.huffman import (
    analyze_compression,
    build_frequency_table,
    build_glossary_header,
    build_huffman_tree,
    compress_spec,
    create_alias_dictionary,
    decompress_spec,
    generate_codes,
)


class TestFrequencyTable:
    def test_basic_frequency(self):
        text = "authentication authentication authentication login login"
        table = build_frequency_table(text, min_freq=2)
        assert "authentication" in table
        assert table["authentication"] == 3
        assert "login" in table
        assert table["login"] == 2

    def test_min_freq_filter(self):
        text = "hello hello world"
        table = build_frequency_table(text, min_freq=2)
        assert "hello" in table
        assert "world" not in table

    def test_empty_text(self):
        table = build_frequency_table("", min_freq=1)
        assert table == {}


class TestHuffmanTree:
    def test_build_tree(self):
        freq = {"a": 5, "b": 9, "c": 12, "d": 13}
        tree = build_huffman_tree(freq)
        assert tree is not None
        assert tree.freq == 39

    def test_generate_codes(self):
        freq = {"a": 5, "b": 9, "c": 12}
        tree = build_huffman_tree(freq)
        codes = generate_codes(tree)
        assert len(codes) == 3
        assert all(set(code).issubset({"0", "1"}) for code in codes.values())

    def test_empty_tree(self):
        tree = build_huffman_tree({})
        assert tree is None
        codes = generate_codes(None)
        assert codes == {}


class TestAliases:
    def test_create_aliases(self):
        freq = {"authentication": 10, "authorization": 8, "endpoint": 5}
        aliases = create_alias_dictionary(freq)
        assert len(aliases) > 0
        for term, alias in aliases.items():
            assert len(alias) < len(term)

    def test_alias_ordering(self):
        freq = {"longterm_one": 10, "longterm_two": 5}
        aliases = create_alias_dictionary(freq)
        assert len(aliases) == 2


class TestCompression:
    def test_compress_decompress_roundtrip(self):
        text = "The authentication module handles authentication and authorization."
        aliases = {"authentication": "$a", "authorization": "$b"}
        compressed = compress_spec(text, aliases)
        assert "$a" in compressed
        decompressed = decompress_spec(compressed, aliases)
        assert decompressed == text

    def test_glossary_header(self):
        aliases = {"auth": "$a", "token": "$b"}
        header = build_glossary_header(aliases)
        assert "SDD GLOSSARY" in header
        assert "$a = auth" in header
        assert "$b = token" in header

    def test_analyze_compression(self, sample_md):
        aliases = {"authentication": "$a", "module": "$b", "system": "$c"}
        compressed = compress_spec(sample_md, aliases)
        metrics = analyze_compression(sample_md, compressed, aliases)
        assert metrics["savings_chars"] > 0
        assert metrics["compression_ratio"] < 1.0
        assert metrics["alias_count"] == 3
