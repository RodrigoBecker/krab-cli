"""Tests for krab_cli.converters."""

import json

import yaml

from krab_cli.converters.converter import (
    convert,
    detect_format,
    json_to_md,
    md_to_json,
    md_to_yaml,
    yaml_to_md,
)
from krab_cli.converters.md_parser import parse_markdown


class TestMdParser:
    def test_parse_headings(self, sample_md):
        result = parse_markdown(sample_md)
        assert "sections" in result
        assert len(result["sections"]) > 0
        headings = [s["heading"] for s in result["sections"]]
        assert "User Authentication Module" in headings

    def test_parse_front_matter(self, sample_md):
        result = parse_markdown(sample_md)
        assert "_meta" in result
        assert result["_meta"]["title"] == "User Authentication Module"
        assert result["_meta"]["version"] == "2.0.0"

    def test_parse_lists(self, sample_md):
        result = parse_markdown(sample_md)
        sections = result["sections"]
        has_list = any(
            any(b.get("type") == "list" for b in s.get("content", []) if isinstance(b, dict))
            for s in sections
        )
        assert has_list

    def test_empty_input(self):
        result = parse_markdown("")
        assert "sections" in result


class TestMdToJson:
    def test_produces_valid_json(self, sample_md):
        result = md_to_json(sample_md)
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "sections" in data

    def test_roundtrip(self, sample_md):
        json_str = md_to_json(sample_md)
        md_back = json_to_md(json_str)
        assert len(md_back) > 0
        assert "Authentication" in md_back


class TestMdToYaml:
    def test_produces_valid_yaml(self, sample_md):
        result = md_to_yaml(sample_md)
        data = yaml.safe_load(result)
        assert isinstance(data, dict)
        assert "sections" in data

    def test_roundtrip(self, sample_md):
        yaml_str = md_to_yaml(sample_md)
        md_back = yaml_to_md(yaml_str)
        assert len(md_back) > 0


class TestJsonToMd:
    def test_produces_markdown(self, sample_json):
        result = json_to_md(sample_json)
        assert "API Overview" in result
        assert "Endpoints" in result


class TestYamlToMd:
    def test_produces_markdown(self, sample_yaml):
        result = yaml_to_md(sample_yaml)
        assert "Database Schema" in result
        assert "Users Table" in result


class TestConvertDispatcher:
    def test_md_to_json(self, sample_md):
        result = convert(sample_md, "md", "json")
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_md_to_yaml(self, sample_md):
        result = convert(sample_md, "markdown", "yaml")
        data = yaml.safe_load(result)
        assert isinstance(data, dict)

    def test_unsupported_conversion(self):
        import pytest

        with pytest.raises(ValueError, match="Unsupported conversion"):
            convert("text", "csv", "json")


class TestDetectFormat:
    def test_md(self):
        assert detect_format("spec.md") == "md"

    def test_json(self):
        assert detect_format("spec.json") == "json"

    def test_yaml(self):
        assert detect_format("spec.yaml") == "yaml"

    def test_yml(self):
        assert detect_format("spec.yml") == "yaml"

    def test_unknown(self):
        import pytest

        with pytest.raises(ValueError):
            detect_format("spec.txt")
