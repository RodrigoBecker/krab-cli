#!/usr/bin/env python3
"""Semantic version bump based on conventional commits.

Reads commits since the last version tag (vX.Y.Z) and determines
the appropriate version bump:

  - feat:          → minor bump (0.1.0 → 0.2.0)
  - fix:, perf:    → patch bump (0.1.0 → 0.1.1)
  - BREAKING CHANGE or feat!:/fix!:  → major bump (0.1.0 → 1.0.0)
  - docs:, test:, refactor:, chore:  → patch bump

Updates:
  - pyproject.toml  (version = "X.Y.Z")
  - src/krab_cli/__init__.py  (__version__ = "X.Y.Z")

Usage:
  python scripts/bump_version.py              # auto-detect from commits
  python scripts/bump_version.py --bump patch # force patch bump
  python scripts/bump_version.py --bump minor # force minor bump
  python scripts/bump_version.py --bump major # force major bump
  python scripts/bump_version.py --dry-run    # show what would happen
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INIT_FILE = ROOT / "src" / "krab_cli" / "__init__.py"

# Conventional commit patterns
BREAKING_PATTERN = re.compile(
    r"^(\w+)!:|BREAKING[ -]CHANGE", re.MULTILINE
)
FEAT_PATTERN = re.compile(r"^feat(\(.+\))?:", re.MULTILINE)
FIX_PATTERN = re.compile(
    r"^(fix|perf|refactor|docs|test|chore|ci|build|style)(\(.+\))?:", re.MULTILINE
)


def get_current_version() -> str:
    """Read current version from __init__.py."""
    content = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        print("ERROR: Could not find __version__ in __init__.py", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semantic version string into (major, minor, patch)."""
    parts = version.split(".")
    if len(parts) != 3:
        print(f"ERROR: Invalid version format: {version}", file=sys.stderr)
        sys.exit(1)
    return int(parts[0]), int(parts[1]), int(parts[2])


def format_version(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def get_last_version_tag() -> str | None:
    """Find the most recent version tag (vX.Y.Z)."""
    result = subprocess.run(
        ["git", "tag", "--list", "v*", "--sort=-version:refname"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    tags = result.stdout.strip().splitlines()
    for tag in tags:
        tag = tag.strip()
        if re.match(r"^v\d+\.\d+\.\d+$", tag):
            return tag
    return None


def get_commits_since(tag: str | None) -> list[str]:
    """Get commit messages since a given tag (or all commits if no tag)."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"]
    else:
        cmd = ["git", "log", "--pretty=format:%s"]

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=ROOT
    )
    return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]


def determine_bump(commits: list[str]) -> str:
    """Determine bump type from commit messages."""
    has_breaking = False
    has_feat = False
    has_fix = False

    for msg in commits:
        if BREAKING_PATTERN.search(msg):
            has_breaking = True
        if FEAT_PATTERN.match(msg):
            has_feat = True
        if FIX_PATTERN.match(msg):
            has_fix = True

    if has_breaking:
        return "major"
    if has_feat:
        return "minor"
    if has_fix:
        return "patch"

    # Default: patch for any other commit
    return "patch"


def bump_version(current: str, bump_type: str) -> str:
    """Calculate next version."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return format_version(major + 1, 0, 0)
    elif bump_type == "minor":
        return format_version(major, minor + 1, 0)
    elif bump_type == "patch":
        return format_version(major, minor, patch + 1)
    else:
        print(f"ERROR: Unknown bump type: {bump_type}", file=sys.stderr)
        sys.exit(1)


def update_file(path: Path, old_version: str, new_version: str) -> bool:
    """Update version string in a file. Returns True if changed."""
    content = path.read_text(encoding="utf-8")
    new_content = content.replace(old_version, new_version)
    if content != new_content:
        path.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump semantic version")
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Force a specific bump type (overrides auto-detection)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    args = parser.parse_args()

    current = get_current_version()
    last_tag = get_last_version_tag()
    commits = get_commits_since(last_tag)

    if not commits and not args.bump:
        print(f"No new commits since {last_tag or 'beginning'}. Version stays at {current}")
        sys.exit(0)

    if args.bump:
        bump_type = args.bump
    else:
        bump_type = determine_bump(commits)

    new_version = bump_version(current, bump_type)

    print(f"Current version: {current}")
    print(f"Last tag:        {last_tag or '(none)'}")
    print(f"Commits:         {len(commits)}")
    print(f"Bump type:       {bump_type}")
    print(f"New version:     {new_version}")
    print()

    if commits:
        print("Commits since last tag:")
        for msg in commits[:20]:
            print(f"  - {msg}")
        if len(commits) > 20:
            print(f"  ... and {len(commits) - 20} more")
        print()

    if args.dry_run:
        print("[DRY RUN] No changes made.")
        return

    # Update files
    updated_pyproject = update_file(PYPROJECT, current, new_version)
    updated_init = update_file(INIT_FILE, current, new_version)

    if updated_pyproject:
        print(f"Updated: {PYPROJECT.relative_to(ROOT)}")
    if updated_init:
        print(f"Updated: {INIT_FILE.relative_to(ROOT)}")

    # Output for GitHub Actions
    # Write to GITHUB_OUTPUT if available
    import os

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"version={new_version}\n")
            f.write(f"tag=v{new_version}\n")
            f.write(f"bump={bump_type}\n")
            f.write(f"previous={current}\n")

    print(f"\nVersion bumped: {current} → {new_version}")


if __name__ == "__main__":
    main()
