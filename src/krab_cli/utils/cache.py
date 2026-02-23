"""Analysis result caching for Krab CLI.

Stores analysis results in .sdd/cache/ keyed by file content hash
and command parameters. Repeated analysis of unchanged files returns
instantly from cache instead of recomputing.

Cache key = sha256(file_content) + command_name + sorted(params)
Storage: .sdd/cache/{key}.json
Invalidation: automatic (content hash changes when file changes)
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any


CACHE_DIR = ".sdd/cache"


def _cache_dir() -> Path:
    """Return the cache directory path, creating it if needed."""
    path = Path(CACHE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_key(content_hash: str, command: str, params: dict[str, Any]) -> str:
    """Build a cache key from content hash, command name, and parameters."""
    param_str = json.dumps(params, sort_keys=True, default=str)
    raw = f"{content_hash}:{command}:{param_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def content_hash(text: str) -> str:
    """Compute sha256 hex digest of text content."""
    return hashlib.sha256(text.encode()).hexdigest()


def get(text: str, command: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Look up cached result for the given text+command+params.

    Returns the cached dict if found, or None on cache miss.
    """
    params = params or {}
    chash = content_hash(text)
    key = _make_key(chash, command, params)
    cache_file = _cache_dir() / f"{key}.json"

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        # Verify content hash matches (sanity check)
        if data.get("_content_hash") != chash:
            cache_file.unlink(missing_ok=True)
            return None
        return data.get("result")
    except (json.JSONDecodeError, OSError):
        cache_file.unlink(missing_ok=True)
        return None


def put(
    text: str,
    command: str,
    result: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> None:
    """Store a result in the cache.

    Uses atomic write (write to temp + rename) to avoid corruption.
    """
    params = params or {}
    chash = content_hash(text)
    key = _make_key(chash, command, params)
    cache_file = _cache_dir() / f"{key}.json"

    payload = {
        "_content_hash": chash,
        "_command": command,
        "_params": params,
        "result": result,
    }

    # Atomic write: write to temp file then rename
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(_cache_dir()),
            suffix=".tmp",
        )
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, default=str)
        Path(tmp_path).replace(cache_file)
    except OSError:
        # Cache write failure is non-fatal
        Path(tmp_path).unlink(missing_ok=True)


def clear() -> int:
    """Remove all cached results. Returns count of files removed."""
    cache_path = Path(CACHE_DIR)
    if not cache_path.exists():
        return 0
    count = 0
    for f in cache_path.glob("*.json"):
        f.unlink(missing_ok=True)
        count += 1
    return count


def stats() -> dict[str, Any]:
    """Return cache statistics."""
    cache_path = Path(CACHE_DIR)
    if not cache_path.exists():
        return {"entries": 0, "size_bytes": 0, "size_human": "0 B"}

    files = list(cache_path.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)

    if total_size < 1024:
        size_human = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_human = f"{total_size / 1024:.1f} KB"
    else:
        size_human = f"{total_size / (1024 * 1024):.1f} MB"

    return {
        "entries": len(files),
        "size_bytes": total_size,
        "size_human": size_human,
    }
