"""Tests for the semantic version bump script."""

from __future__ import annotations

import pytest

# Import functions directly from the script
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "bump_version",
    Path(__file__).resolve().parent.parent / "scripts" / "bump_version.py",
)
bump_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_mod)

parse_version = bump_mod.parse_version
format_version = bump_mod.format_version
bump_version = bump_mod.bump_version
determine_bump = bump_mod.determine_bump


# ═══════════════════════════════════════════════════════════════════════════
# parse_version
# ═══════════════════════════════════════════════════════════════════════════


class TestParseVersion:
    def test_parse_basic(self):
        assert parse_version("0.1.0") == (0, 1, 0)

    def test_parse_double_digits(self):
        assert parse_version("1.23.456") == (1, 23, 456)

    def test_parse_zeros(self):
        assert parse_version("0.0.0") == (0, 0, 0)

    def test_parse_large(self):
        assert parse_version("10.20.30") == (10, 20, 30)

    def test_parse_invalid_exits(self):
        with pytest.raises(SystemExit):
            parse_version("1.2")

    def test_parse_invalid_four_parts(self):
        with pytest.raises(SystemExit):
            parse_version("1.2.3.4")


# ═══════════════════════════════════════════════════════════════════════════
# format_version
# ═══════════════════════════════════════════════════════════════════════════


class TestFormatVersion:
    def test_format_basic(self):
        assert format_version(0, 1, 0) == "0.1.0"

    def test_format_zeros(self):
        assert format_version(0, 0, 0) == "0.0.0"

    def test_format_large(self):
        assert format_version(10, 20, 30) == "10.20.30"


# ═══════════════════════════════════════════════════════════════════════════
# bump_version
# ═══════════════════════════════════════════════════════════════════════════


class TestBumpVersion:
    def test_patch_bump(self):
        assert bump_version("0.1.0", "patch") == "0.1.1"

    def test_minor_bump(self):
        assert bump_version("0.1.0", "minor") == "0.2.0"

    def test_major_bump(self):
        assert bump_version("0.1.0", "major") == "1.0.0"

    def test_minor_resets_patch(self):
        assert bump_version("1.2.3", "minor") == "1.3.0"

    def test_major_resets_minor_and_patch(self):
        assert bump_version("1.2.3", "major") == "2.0.0"

    def test_patch_increments(self):
        assert bump_version("1.2.3", "patch") == "1.2.4"

    def test_from_zero(self):
        assert bump_version("0.0.0", "patch") == "0.0.1"
        assert bump_version("0.0.0", "minor") == "0.1.0"
        assert bump_version("0.0.0", "major") == "1.0.0"

    def test_unknown_bump_exits(self):
        with pytest.raises(SystemExit):
            bump_version("0.1.0", "invalid")


# ═══════════════════════════════════════════════════════════════════════════
# determine_bump
# ═══════════════════════════════════════════════════════════════════════════


class TestDetermineBump:
    def test_feat_is_minor(self):
        commits = ["feat: add new feature", "fix: fix something"]
        assert determine_bump(commits) == "minor"

    def test_feat_with_scope_is_minor(self):
        commits = ["feat(cli): add new command"]
        assert determine_bump(commits) == "minor"

    def test_fix_is_patch(self):
        commits = ["fix: correct bug"]
        assert determine_bump(commits) == "patch"

    def test_fix_with_scope_is_patch(self):
        commits = ["fix(memory): correct loading"]
        assert determine_bump(commits) == "patch"

    def test_breaking_bang_is_major(self):
        commits = ["feat!: redesign API"]
        assert determine_bump(commits) == "major"

    def test_breaking_change_footer_is_major(self):
        commits = ["feat: add feature\nBREAKING CHANGE: removed old API"]
        assert determine_bump(commits) == "major"

    def test_breaking_change_hyphen_is_major(self):
        commits = ["refactor: update\nBREAKING-CHANGE: removed method"]
        assert determine_bump(commits) == "major"

    def test_breaking_overrides_feat(self):
        commits = ["feat: new thing", "fix!: breaking fix"]
        assert determine_bump(commits) == "major"

    def test_refactor_is_patch(self):
        commits = ["refactor: clean up code"]
        assert determine_bump(commits) == "patch"

    def test_docs_is_patch(self):
        commits = ["docs: update readme"]
        assert determine_bump(commits) == "patch"

    def test_test_is_patch(self):
        commits = ["test: add unit tests"]
        assert determine_bump(commits) == "patch"

    def test_chore_is_patch(self):
        commits = ["chore: update dependencies"]
        assert determine_bump(commits) == "patch"

    def test_perf_is_patch(self):
        commits = ["perf: improve query speed"]
        assert determine_bump(commits) == "patch"

    def test_mixed_feat_and_fix(self):
        commits = ["fix: bug fix", "feat: new feature", "docs: update docs"]
        assert determine_bump(commits) == "minor"

    def test_no_conventional_defaults_to_patch(self):
        commits = ["random commit message", "another one"]
        assert determine_bump(commits) == "patch"

    def test_empty_commits_defaults_to_patch(self):
        assert determine_bump([]) == "patch"

    def test_ci_is_patch(self):
        commits = ["ci: update workflow"]
        assert determine_bump(commits) == "patch"

    def test_build_is_patch(self):
        commits = ["build: update build config"]
        assert determine_bump(commits) == "patch"

    def test_style_is_patch(self):
        commits = ["style: format code"]
        assert determine_bump(commits) == "patch"
