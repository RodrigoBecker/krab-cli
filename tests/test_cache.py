"""Tests for the analysis result caching module."""

from __future__ import annotations

import json
import os

import pytest


@pytest.fixture(autouse=True)
def _use_tmp_dir(tmp_path, monkeypatch):
    """Run all cache tests in an isolated temp directory."""
    monkeypatch.chdir(tmp_path)


class TestCacheBasic:
    """Basic cache operations: get, put, clear, stats."""

    def test_cache_miss_returns_none(self):
        from krab_cli.utils.cache import get

        result = get("some text", "test_cmd")
        assert result is None

    def test_put_and_get(self):
        from krab_cli.utils.cache import get, put

        text = "hello world"
        cmd = "analyze_tokens"
        data = {"tokens": 42, "chars": 100}

        put(text, cmd, data)
        cached = get(text, cmd)
        assert cached == data

    def test_different_text_is_miss(self):
        from krab_cli.utils.cache import get, put

        put("text A", "cmd", {"value": 1})
        assert get("text B", "cmd") is None

    def test_different_command_is_miss(self):
        from krab_cli.utils.cache import get, put

        put("text", "cmd_a", {"value": 1})
        assert get("text", "cmd_b") is None

    def test_params_differentiate_entries(self):
        from krab_cli.utils.cache import get, put

        text = "same text"
        put(text, "cmd", {"v": 1}, params={"encoding": "a"})
        put(text, "cmd", {"v": 2}, params={"encoding": "b"})

        assert get(text, "cmd", {"encoding": "a"})["v"] == 1
        assert get(text, "cmd", {"encoding": "b"})["v"] == 2

    def test_default_params_vs_explicit_params(self):
        from krab_cli.utils.cache import get, put

        text = "content"
        put(text, "cmd", {"default": True})
        put(text, "cmd", {"custom": True}, params={"k": "v"})

        assert get(text, "cmd") == {"default": True}
        assert get(text, "cmd", {"k": "v"}) == {"custom": True}

    def test_clear_removes_all(self):
        from krab_cli.utils.cache import clear, get, put, stats

        put("a", "cmd", {"x": 1})
        put("b", "cmd", {"x": 2})
        assert stats()["entries"] == 2

        count = clear()
        assert count == 2
        assert get("a", "cmd") is None
        assert get("b", "cmd") is None
        assert stats()["entries"] == 0

    def test_clear_empty_cache(self):
        from krab_cli.utils.cache import clear

        assert clear() == 0

    def test_stats_empty(self):
        from krab_cli.utils.cache import stats

        st = stats()
        assert st["entries"] == 0
        assert st["size_bytes"] == 0

    def test_stats_with_entries(self):
        from krab_cli.utils.cache import put, stats

        put("text", "cmd", {"key": "value"})
        st = stats()
        assert st["entries"] == 1
        assert st["size_bytes"] > 0
        assert isinstance(st["size_human"], str)


class TestCacheIntegrity:
    """Edge cases and integrity checks."""

    def test_content_hash_deterministic(self):
        from krab_cli.utils.cache import content_hash

        h1 = content_hash("hello")
        h2 = content_hash("hello")
        assert h1 == h2

    def test_content_hash_differs_for_different_text(self):
        from krab_cli.utils.cache import content_hash

        h1 = content_hash("hello")
        h2 = content_hash("world")
        assert h1 != h2

    def test_corrupted_cache_file_is_handled(self):
        from krab_cli.utils.cache import _cache_dir, _make_key, content_hash, get, put

        text = "test text"
        cmd = "test_cmd"
        put(text, cmd, {"ok": True})

        # Corrupt the cache file
        chash = content_hash(text)
        key = _make_key(chash, cmd, {})
        cache_file = _cache_dir() / f"{key}.json"
        cache_file.write_text("NOT VALID JSON", encoding="utf-8")

        # Should return None and not crash
        result = get(text, cmd)
        assert result is None

    def test_tampered_content_hash_is_rejected(self):
        from krab_cli.utils.cache import _cache_dir, _make_key, content_hash, get, put

        text = "original"
        cmd = "cmd"
        put(text, cmd, {"data": 1})

        # Tamper with the stored content hash
        chash = content_hash(text)
        key = _make_key(chash, cmd, {})
        cache_file = _cache_dir() / f"{key}.json"
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["_content_hash"] = "tampered_hash"
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        # Should return None (hash mismatch)
        result = get(text, cmd)
        assert result is None

    def test_overwrite_existing_entry(self):
        from krab_cli.utils.cache import get, put

        text = "same"
        put(text, "cmd", {"v": 1})
        put(text, "cmd", {"v": 2})
        assert get(text, "cmd") == {"v": 2}

    def test_nested_dict_values(self):
        from krab_cli.utils.cache import get, put

        data = {
            "metrics": {"tokens": 100, "cost": 0.05},
            "list": [1, 2, 3],
            "nested": {"a": {"b": "c"}},
        }
        put("text", "cmd", data)
        assert get("text", "cmd") == data

    def test_unicode_content(self):
        from krab_cli.utils.cache import get, put

        text = "Especificacao com acentos e cedilha"
        put(text, "cmd", {"result": "ok"})
        assert get(text, "cmd") == {"result": "ok"}

    def test_large_content(self):
        from krab_cli.utils.cache import get, put

        text = "x" * 100_000
        put(text, "cmd", {"big": True})
        assert get(text, "cmd") == {"big": True}
