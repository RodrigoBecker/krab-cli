"""Tests for spec and memory CLI commands."""

import os
import subprocess

import pytest
from typer.testing import CliRunner

from krab_cli.cli import app
from krab_cli.memory import MemoryStore, SpecRegistry

runner = CliRunner()


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def git_spec_repo(tmp_path):
    """Create a local Git repo with sample specs for import tests."""
    repo_dir = tmp_path / "remote-repo"
    specs_dir = repo_dir / ".sdd" / "specs"
    specs_dir.mkdir(parents=True)

    (specs_dir / "spec.task.auth-login.md").write_text(
        "# Auth Login\n## Requirements\nUser login feature.\n"
    )
    (specs_dir / "spec.task.payment-flow.md").write_text(
        "# Payment Flow\n## Requirements\nPayment processing.\n"
    )
    (specs_dir / "spec.architecture.api-gateway.md").write_text(
        "# API Gateway\n## Overview\nGateway architecture.\n"
    )
    # A non-spec file that should NOT be picked up
    (specs_dir / "readme.md").write_text("# Not a spec\n")

    subprocess.run(
        ["git", "init"], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    return repo_dir


@pytest.fixture()
def git_spec_repo_custom_path(tmp_path):
    """Create a Git repo with specs in a custom directory."""
    repo_dir = tmp_path / "custom-repo"
    specs_dir = repo_dir / "my-specs"
    specs_dir.mkdir(parents=True)

    (specs_dir / "spec.task.feature-x.md").write_text(
        "# Feature X\n## Requirements\nCustom path spec.\n"
    )

    subprocess.run(
        ["git", "init"], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    return repo_dir


@pytest.fixture()
def git_spec_repo_with_branch(tmp_path):
    """Create a Git repo with specs on a specific branch."""
    repo_dir = tmp_path / "branch-repo"
    repo_dir.mkdir(parents=True)

    subprocess.run(
        ["git", "init"], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    # Initial commit on default branch
    (repo_dir / "README.md").write_text("# Repo\n")
    subprocess.run(
        ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    # Create a 'specs-v2' branch with specs
    subprocess.run(
        ["git", "checkout", "-b", "specs-v2"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    specs_dir = repo_dir / ".sdd" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.task.v2-feature.md").write_text(
        "# V2 Feature\n## Requirements\nBranch-specific spec.\n"
    )
    subprocess.run(
        ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "add v2 specs"],
        cwd=repo_dir, capture_output=True, check=True,
    )
    return repo_dir


class TestSpecCommands:
    def test_spec_list(self):
        result = runner.invoke(app, ["spec", "list"])
        assert result.exit_code == 0
        assert "task" in result.output
        assert "architecture" in result.output
        assert "plan" in result.output
        assert "skill" in result.output

    def test_spec_new_task(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec",
                "new",
                "task",
                "--name",
                "Login Feature",
                "--desc",
                "User authentication",
                "-o",
                str(tmp_path / "spec.task.login.md"),
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "spec.task.login.md").exists()
        content = (tmp_path / "spec.task.login.md").read_text()
        assert "Login Feature" in content
        assert "Gherkin" in content or "Scenario" in content

    def test_spec_new_architecture(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec",
                "new",
                "architecture",
                "--name",
                "Auth Module",
                "-o",
                str(tmp_path / "spec.arch.auth.md"),
            ],
        )
        assert result.exit_code == 0
        content = (tmp_path / "spec.arch.auth.md").read_text()
        assert "mermaid" in content

    def test_spec_new_plan(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec",
                "new",
                "plan",
                "--name",
                "MVP Launch",
                "-o",
                str(tmp_path / "spec.plan.mvp.md"),
            ],
        )
        assert result.exit_code == 0
        content = (tmp_path / "spec.plan.mvp.md").read_text()
        assert "Fase" in content

    def test_spec_new_skill(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec",
                "new",
                "skill",
                "--name",
                "Project Skills",
                "-o",
                str(tmp_path / "spec.skill.md"),
            ],
        )
        assert result.exit_code == 0
        content = (tmp_path / "spec.skill.md").read_text()
        assert "Linguagen" in content or "Framework" in content

    def test_spec_new_invalid_type(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(app, ["spec", "new", "invalid", "--name", "X"])
        assert result.exit_code == 1

    def test_spec_refine(self, tmp_path):
        spec_file = tmp_path / "test-spec.md"
        spec_file.write_text("""# Auth Feature
## Requirements
The system should handle authentication. TBD on the details.

```gherkin
Feature: Login
  Scenario: Happy path
    Given a valid user
    When they login
    Then they see the dashboard
```
""")
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec",
                "refine",
                str(spec_file),
                "-o",
                str(tmp_path / "refinement.md"),
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "refinement.md").exists()
        content = (tmp_path / "refinement.md").read_text()
        assert "Refinamento" in content

    def test_spec_new_with_memory(self, tmp_path):
        os.chdir(tmp_path)
        # Init memory
        runner.invoke(app, ["memory", "init", "--name", "MyProject"])
        runner.invoke(app, ["memory", "set", "tech_stack.backend", "Python"])
        runner.invoke(app, ["memory", "set", "architecture_style", "hexagonal"])

        result = runner.invoke(
            app,
            [
                "spec",
                "new",
                "task",
                "--name",
                "Auth Feature",
                "-o",
                str(tmp_path / "spec.task.auth.md"),
            ],
        )
        assert result.exit_code == 0
        content = (tmp_path / "spec.task.auth.md").read_text()
        assert "MyProject" in content
        assert "Python" in content


class TestMemoryCommands:
    def test_init(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(app, ["memory", "init", "--name", "TestProject"])
        assert result.exit_code == 0
        assert (tmp_path / ".sdd" / "memory.json").exists()

    def test_show(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "TestProject"])
        result = runner.invoke(app, ["memory", "show"])
        assert result.exit_code == 0
        assert "TestProject" in result.output

    def test_show_not_initialized(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(app, ["memory", "show"])
        assert result.exit_code == 1

    def test_set(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(app, ["memory", "set", "tech_stack.backend", "Node.js"])
        assert result.exit_code == 0
        assert "Node.js" in result.output

    def test_add_skill(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(
            app,
            [
                "memory",
                "add-skill",
                "Python",
                "--cat",
                "language",
                "--ver",
                "3.12",
                "--desc",
                "Main language",
                "--tags",
                "backend,scripting",
            ],
        )
        assert result.exit_code == 0

    def test_skills_list(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(app, ["memory", "add-skill", "Python", "--cat", "language"])
        runner.invoke(app, ["memory", "add-skill", "FastAPI", "--cat", "framework"])
        result = runner.invoke(app, ["memory", "skills"])
        assert result.exit_code == 0
        assert "Python" in result.output
        assert "FastAPI" in result.output

    def test_remove_skill(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(app, ["memory", "add-skill", "Python", "--cat", "language"])
        result = runner.invoke(app, ["memory", "remove-skill", "Python"])
        assert result.exit_code == 0

    def test_history(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        # Generate a spec to create history
        runner.invoke(
            app,
            [
                "spec",
                "new",
                "task",
                "--name",
                "Auth",
                "-o",
                str(tmp_path / "spec.task.auth.md"),
            ],
        )
        result = runner.invoke(app, ["memory", "history"])
        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY commands
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistryCommands:
    def test_registry_add(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(
            app,
            ["spec", "registry", "add", "myspecs", "https://github.com/user/specs"],
        )
        assert result.exit_code == 0
        assert "adicionado" in result.output

        # Verify persistence
        store = MemoryStore(tmp_path)
        regs = store.load_registries()
        assert "myspecs" in regs
        assert regs["myspecs"].url == "https://github.com/user/specs"

    def test_registry_add_with_options(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(
            app,
            [
                "spec", "registry", "add", "team",
                "git@github.com:org/specs.git",
                "--path", "specs/v2",
                "--branch", "main",
            ],
        )
        assert result.exit_code == 0
        store = MemoryStore(tmp_path)
        reg = store.load_registries()["team"]
        assert reg.path == "specs/v2"
        assert reg.branch == "main"

    def test_registry_add_update_existing(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app, ["spec", "registry", "add", "myspecs", "https://old-url.com"]
        )
        result = runner.invoke(
            app, ["spec", "registry", "add", "myspecs", "https://new-url.com"]
        )
        assert result.exit_code == 0
        assert "atualizado" in result.output

        store = MemoryStore(tmp_path)
        assert store.load_registries()["myspecs"].url == "https://new-url.com"

    def test_registry_remove(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app, ["spec", "registry", "add", "myspecs", "https://example.com"]
        )
        result = runner.invoke(app, ["spec", "registry", "remove", "myspecs"])
        assert result.exit_code == 0
        assert "removido" in result.output

        store = MemoryStore(tmp_path)
        assert "myspecs" not in store.load_registries()

    def test_registry_remove_not_found(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(app, ["spec", "registry", "remove", "nope"])
        assert result.exit_code == 1
        assert "nao encontrado" in result.output

    def test_registry_list(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app, ["spec", "registry", "add", "alpha", "https://github.com/a/specs"]
        )
        runner.invoke(
            app, ["spec", "registry", "add", "beta", "https://github.com/b/specs"]
        )
        result = runner.invoke(app, ["spec", "registry", "list"])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_registry_list_empty(self, tmp_path):
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(app, ["spec", "registry", "list"])
        assert result.exit_code == 0
        assert "Nenhum registry" in result.output

    def test_registry_not_initialized(self, tmp_path):
        os.chdir(tmp_path)
        result = runner.invoke(app, ["spec", "registry", "list"])
        assert result.exit_code == 1
        assert "nao inicializado" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# SPEC IMPORT commands
# ═══════════════════════════════════════════════════════════════════════════


class TestSpecImport:
    def test_import_from_url_all(self, tmp_path, git_spec_repo):
        """Import all specs from a local git repo URL."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo), "--all"],
        )
        assert result.exit_code == 0
        assert "Importadas 3 specs" in result.output

        specs_dir = tmp_path / ".sdd" / "specs"
        assert (specs_dir / "spec.task.auth-login.md").exists()
        assert (specs_dir / "spec.task.payment-flow.md").exists()
        assert (specs_dir / "spec.architecture.api-gateway.md").exists()
        # Non-spec file should NOT be imported
        assert not (specs_dir / "readme.md").exists()

    def test_import_interactive_selection(self, tmp_path, git_spec_repo):
        """Import only selected specs via interactive prompt."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo)],
            input="1,3\n",
        )
        assert result.exit_code == 0
        assert "Importadas 2 specs" in result.output

        specs_dir = tmp_path / ".sdd" / "specs"
        imported = list(specs_dir.glob("spec.*.md"))
        assert len(imported) == 2

    def test_import_interactive_all(self, tmp_path, git_spec_repo):
        """Select 'all' at the interactive prompt."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo)],
            input="all\n",
        )
        assert result.exit_code == 0
        assert "Importadas 3 specs" in result.output

    def test_import_conflict_no_force(self, tmp_path, git_spec_repo):
        """Existing specs are skipped without --force."""
        os.chdir(tmp_path)
        # Pre-create a conflicting spec
        specs_dir = tmp_path / ".sdd" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.task.auth-login.md").write_text("# Old content\n")

        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo), "--all"],
        )
        assert result.exit_code == 0
        assert "ja existe" in result.output
        assert "Importadas 2 specs" in result.output
        assert "1 specs ignoradas" in result.output

        # Conflicting file should NOT be overwritten
        content = (specs_dir / "spec.task.auth-login.md").read_text()
        assert content == "# Old content\n"

    def test_import_conflict_with_force(self, tmp_path, git_spec_repo):
        """Existing specs are overwritten with --force."""
        os.chdir(tmp_path)
        specs_dir = tmp_path / ".sdd" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.task.auth-login.md").write_text("# Old content\n")

        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo), "--all", "--force"],
        )
        assert result.exit_code == 0
        assert "Importadas 3 specs" in result.output

        content = (specs_dir / "spec.task.auth-login.md").read_text()
        assert "Auth Login" in content  # New content from repo

    def test_import_custom_path(self, tmp_path, git_spec_repo_custom_path):
        """Import specs from a custom subdirectory via --path."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec", "import", str(git_spec_repo_custom_path),
                "--path", "my-specs",
                "--all",
            ],
        )
        assert result.exit_code == 0
        assert "Importadas 1 specs" in result.output
        assert (tmp_path / ".sdd" / "specs" / "spec.task.feature-x.md").exists()

    def test_import_custom_output_dir(self, tmp_path, git_spec_repo):
        """Import to a custom output directory via --output."""
        os.chdir(tmp_path)
        out_dir = tmp_path / "imported"
        result = runner.invoke(
            app,
            ["spec", "import", str(git_spec_repo), "--all", "-o", str(out_dir)],
        )
        assert result.exit_code == 0
        assert (out_dir / "spec.task.auth-login.md").exists()

    def test_import_branch(self, tmp_path, git_spec_repo_with_branch):
        """Import specs from a specific branch via --branch."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "spec", "import", str(git_spec_repo_with_branch),
                "--branch", "specs-v2",
                "--all",
            ],
        )
        assert result.exit_code == 0
        assert "Importadas 1 specs" in result.output
        assert (tmp_path / ".sdd" / "specs" / "spec.task.v2-feature.md").exists()

    def test_import_no_specs_found(self, tmp_path):
        """Empty repo (no specs) exits cleanly."""
        # Create a git repo with no specs
        repo = tmp_path / "empty-repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Empty\n")
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.com"],
            cwd=repo, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=repo, capture_output=True, check=True,
        )
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo, capture_output=True, check=True,
        )

        os.chdir(tmp_path)
        result = runner.invoke(
            app, ["spec", "import", str(repo), "--all"],
        )
        assert result.exit_code == 0
        assert "Nenhuma spec" in result.output

    def test_import_clone_failure(self, tmp_path):
        """Invalid URL produces an error."""
        os.chdir(tmp_path)
        result = runner.invoke(
            app, ["spec", "import", "https://invalid.example.com/no-repo.git", "--all"],
        )
        assert result.exit_code == 1
        assert "Falha ao clonar" in result.output

    def test_import_from_registry_alias(self, tmp_path, git_spec_repo):
        """Import using a registry alias instead of URL."""
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app,
            ["spec", "registry", "add", "myspecs", str(git_spec_repo)],
        )

        result = runner.invoke(
            app, ["spec", "import", "myspecs", "--all"],
        )
        assert result.exit_code == 0
        assert "Importadas 3 specs" in result.output

    def test_import_registry_alias_not_found(self, tmp_path):
        """Unknown alias without .sdd/ produces clear error."""
        os.chdir(tmp_path)
        result = runner.invoke(app, ["spec", "import", "nonexistent", "--all"])
        assert result.exit_code == 1
        assert "nao e uma URL Git" in result.output

    def test_import_registry_alias_not_found_with_sdd(self, tmp_path):
        """Unknown alias with .sdd/ initialized produces clear error."""
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        result = runner.invoke(app, ["spec", "import", "nonexistent", "--all"])
        assert result.exit_code == 1
        assert "nao encontrado" in result.output

    def test_import_records_history(self, tmp_path, git_spec_repo):
        """Import records entries in .sdd/history.json."""
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app, ["spec", "import", str(git_spec_repo), "--all"],
        )

        store = MemoryStore(tmp_path)
        history = store.load_history()
        import_entries = [e for e in history if e["action"] == "spec_import"]
        assert len(import_entries) == 3
        assert import_entries[0]["url"] == str(git_spec_repo)

    def test_import_registry_with_defaults(self, tmp_path, git_spec_repo_with_branch):
        """Registry defaults for path and branch are used."""
        os.chdir(tmp_path)
        runner.invoke(app, ["memory", "init", "--name", "Test"])
        runner.invoke(
            app,
            [
                "spec", "registry", "add", "v2specs",
                str(git_spec_repo_with_branch),
                "--branch", "specs-v2",
                "--path", ".sdd/specs",
            ],
        )

        result = runner.invoke(
            app, ["spec", "import", "v2specs", "--all"],
        )
        assert result.exit_code == 0
        assert "Importadas 1 specs" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# SPEC REGISTRY dataclass unit tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSpecRegistryModel:
    def test_to_dict_minimal(self):
        reg = SpecRegistry(name="test", url="https://example.com")
        d = reg.to_dict()
        assert d["name"] == "test"
        assert d["url"] == "https://example.com"
        assert "path" not in d  # empty fields are omitted
        assert "branch" not in d

    def test_to_dict_full(self):
        reg = SpecRegistry(
            name="full", url="https://x.com", path="specs/", branch="main", added_at="2026-01-01"
        )
        d = reg.to_dict()
        assert d["path"] == "specs/"
        assert d["branch"] == "main"
        assert d["added_at"] == "2026-01-01"

    def test_from_dict(self):
        reg = SpecRegistry.from_dict({
            "name": "test",
            "url": "https://example.com",
            "path": "my-specs",
            "branch": "dev",
        })
        assert reg.name == "test"
        assert reg.url == "https://example.com"
        assert reg.path == "my-specs"
        assert reg.branch == "dev"

    def test_from_dict_minimal(self):
        reg = SpecRegistry.from_dict({"name": "x", "url": "https://y.com"})
        assert reg.name == "x"
        assert reg.path == ""
        assert reg.branch == ""

    def test_memorystore_registries_roundtrip(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.init(project_name="Test")

        store.add_registry("alpha", "https://a.com", path="specs")
        store.add_registry("beta", "https://b.com", branch="main")

        regs = store.load_registries()
        assert len(regs) == 2
        assert regs["alpha"].url == "https://a.com"
        assert regs["alpha"].path == "specs"
        assert regs["beta"].branch == "main"

    def test_memorystore_remove_registry(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.init(project_name="Test")
        store.add_registry("x", "https://x.com")

        store.remove_registry("x")
        assert "x" not in store.load_registries()

    def test_memorystore_remove_registry_not_found(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.init(project_name="Test")

        with pytest.raises(ValueError, match="nao encontrado"):
            store.remove_registry("nope")
