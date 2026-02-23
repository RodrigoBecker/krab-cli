"""Tests for spec and memory CLI commands."""

import os

from typer.testing import CliRunner

from krab_cli.cli import app

runner = CliRunner()


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
