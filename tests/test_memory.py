"""Tests for memory system and spec templates."""

import pytest

from krab_cli.memory import MemoryStore, ProjectMemory, ProjectSkill

# ─── Memory Store ─────────────────────────────────────────────────────────


class TestMemoryStore:
    def test_init_creates_sdd_dir(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        memory = store.init(project_name="TestProject", description="A test project")
        assert store.is_initialized
        assert memory.project_name == "TestProject"
        assert (tmp_path / ".sdd" / "memory.json").exists()
        assert (tmp_path / ".sdd" / "skills.json").exists()

    def test_load_memory(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="MyProject")
        memory = store.load_memory()
        assert memory.project_name == "MyProject"

    def test_set_field_simple(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="Test")
        store.set_field("architecture_style", "hexagonal")
        memory = store.load_memory()
        assert memory.architecture_style == "hexagonal"

    def test_set_field_nested(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="Test")
        store.set_field("tech_stack.backend", "Node.js")
        store.set_field("tech_stack.database", "PostgreSQL")
        memory = store.load_memory()
        assert memory.tech_stack["backend"] == "Node.js"
        assert memory.tech_stack["database"] == "PostgreSQL"

    def test_set_field_list(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="Test")
        store.set_field("constraints", "Must use REST API")
        store.set_field("constraints", "Max 200ms latency")
        memory = store.load_memory()
        assert len(memory.constraints) == 2

    def test_set_field_unknown(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="Test")
        with pytest.raises(ValueError, match="Unknown field"):
            store.set_field("nonexistent", "value")


class TestProjectSkills:
    def test_add_skill(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        skill = ProjectSkill(name="Python", category="language", version="3.12")
        store.add_skill(skill)
        skills = store.load_skills()
        assert len(skills) == 1
        assert skills[0].name == "Python"

    def test_add_multiple_skills(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        store.add_skill(ProjectSkill(name="Python", category="language"))
        store.add_skill(ProjectSkill(name="FastAPI", category="framework"))
        store.add_skill(ProjectSkill(name="PostgreSQL", category="infra"))
        skills = store.load_skills()
        assert len(skills) == 3

    def test_update_existing_skill(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        store.add_skill(ProjectSkill(name="Python", category="language", version="3.11"))
        store.add_skill(ProjectSkill(name="Python", category="language", version="3.12"))
        skills = store.load_skills()
        assert len(skills) == 1
        assert skills[0].version == "3.12"

    def test_remove_skill(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        store.add_skill(ProjectSkill(name="Python", category="language"))
        store.add_skill(ProjectSkill(name="FastAPI", category="framework"))
        store.remove_skill("Python")
        skills = store.load_skills()
        assert len(skills) == 1
        assert skills[0].name == "FastAPI"

    def test_skills_context_block(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        store.add_skill(ProjectSkill(name="Python", category="language", version="3.12"))
        store.add_skill(ProjectSkill(name="FastAPI", category="framework", version="0.100"))
        block = store.skills_context_block()
        assert "Python" in block
        assert "FastAPI" in block


class TestProjectMemory:
    def test_context_block(self):
        memory = ProjectMemory(
            project_name="Builder",
            architecture_style="hexagonal",
            tech_stack={"backend": "Python", "db": "PostgreSQL"},
            constraints=["REST only", "Max 200ms"],
        )
        block = memory.to_context_block()
        assert "Builder" in block
        assert "hexagonal" in block
        assert "Python" in block

    def test_empty_context_block(self):
        memory = ProjectMemory()
        block = memory.to_context_block()
        assert block == ""


class TestHistory:
    def test_add_and_load(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init()
        store.add_history_entry({"action": "test", "name": "my-spec"})
        history = store.load_history()
        assert len(history) == 1
        assert history[0]["action"] == "test"
        assert "timestamp" in history[0]
