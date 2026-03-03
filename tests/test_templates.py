"""Tests for spec templates and the Tree-of-Thought refining engine."""

import pytest

# Import all templates to register them
import krab_cli.templates.architecture
import krab_cli.templates.plan
import krab_cli.templates.refining
import krab_cli.templates.skill
import krab_cli.templates.task  # noqa: F401
from krab_cli.memory import MemoryStore, ProjectMemory, ProjectSkill
from krab_cli.templates import TemplateContext, build_context, get_template, list_templates
from krab_cli.templates.refining import analyze_spec_for_refinement

# ─── Template Registry ────────────────────────────────────────────────────


class TestRegistry:
    def test_list_templates(self):
        templates = list_templates()
        types = {t["type"] for t in templates}
        assert "task" in types
        assert "architecture" in types
        assert "plan" in types
        assert "skill" in types
        assert "refining" in types

    def test_get_template(self):
        t = get_template("task")
        assert t.template_type == "task"

    def test_get_unknown_template(self):
        with pytest.raises(ValueError, match="Unknown template"):
            get_template("nonexistent")


# ─── Template Rendering ──────────────────────────────────────────────────


class TestTaskTemplate:
    def test_renders_gherkin(self):
        ctx = TemplateContext(name="Login Feature", description="User authentication")
        template = get_template("task")
        content = template.render(ctx)
        assert "# Login Feature" in content
        assert "Feature:" in content
        assert "Scenario:" in content
        assert "Given" in content
        assert "When" in content
        assert "Then" in content

    def test_renders_with_memory(self):
        memory = ProjectMemory(
            project_name="Builder",
            tech_stack={"backend": "Python"},
        )
        ctx = TemplateContext(name="Auth", memory=memory)
        template = get_template("task")
        content = template.render(ctx)
        assert "Builder" in content
        assert "Python" in content

    def test_suggested_filename(self):
        ctx = TemplateContext(name="User Login")
        template = get_template("task")
        assert template.suggested_filename(ctx) == ".sdd/specs/spec.task.user-login.md"


class TestArchitectureTemplate:
    def test_renders_mermaid(self):
        ctx = TemplateContext(name="Auth Module")
        template = get_template("architecture")
        content = template.render(ctx)
        assert "```mermaid" in content
        assert "graph" in content
        assert "sequenceDiagram" in content
        assert "erDiagram" in content

    def test_renders_c4(self):
        ctx = TemplateContext(name="System Overview")
        template = get_template("architecture")
        content = template.render(ctx)
        assert "C4" in content or "Contexto" in content
        assert "Container" in content
        assert "Component" in content

    def test_renders_adr(self):
        ctx = TemplateContext(name="API Design")
        template = get_template("architecture")
        content = template.render(ctx)
        assert "ADR" in content


class TestPlanTemplate:
    def test_renders_phases(self):
        ctx = TemplateContext(name="MVP Launch")
        template = get_template("plan")
        content = template.render(ctx)
        assert "Fase 1" in content
        assert "Fase 2" in content
        assert "Milestone" in content

    def test_renders_gantt(self):
        ctx = TemplateContext(name="Q1 Plan")
        template = get_template("plan")
        content = template.render(ctx)
        assert "gantt" in content

    def test_renders_risk_table(self):
        ctx = TemplateContext(name="Risk Plan")
        template = get_template("plan")
        content = template.render(ctx)
        assert "Risco" in content
        assert "Mitigação" in content

    def test_includes_skills_block(self):
        ctx = TemplateContext(
            name="Test Plan",
            skills_block="  language: Python 3.12\n  framework: FastAPI",
        )
        template = get_template("plan")
        content = template.render(ctx)
        assert "Python 3.12" in content


class TestSkillTemplate:
    def test_renders_categories(self):
        ctx = TemplateContext(name="Project Skills")
        template = get_template("skill")
        content = template.render(ctx)
        assert "Linguagen" in content
        assert "Framework" in content
        assert "Pattern" in content
        assert "Ferramenta" in content

    def test_renders_conventions(self):
        ctx = TemplateContext(name="Skills")
        template = get_template("skill")
        content = template.render(ctx)
        assert "Convenções" in content or "Git" in content


# ─── Refining Engine ──────────────────────────────────────────────────────


class TestRefiningEngine:
    def test_detects_task_type(self):
        text = """# Auth Feature
        ```gherkin
        Feature: Login
          Scenario: Happy path
            Given a valid user
            When they login
            Then they see dashboard
        ```
        """
        plan = analyze_spec_for_refinement(text)
        assert plan.spec_type == "task"

    def test_detects_architecture_type(self):
        text = """# System Architecture
        ## C4 Context Diagram
        ```mermaid
        graph TB
            A[User] --> B[System]
        ```
        ## Deployment
        Production cluster with 3 nodes.
        """
        plan = analyze_spec_for_refinement(text)
        assert plan.spec_type == "architecture"

    def test_generates_dimensions(self, sample_md):
        plan = analyze_spec_for_refinement(sample_md)
        assert len(plan.dimensions) == 5
        dim_names = {d.name for d in plan.dimensions}
        assert "Completude Estrutural" in dim_names
        assert "Precisão e Especificidade" in dim_names
        assert "Coerência Interna" in dim_names
        assert "Prontidão para Agente IA" in dim_names
        assert "Testabilidade" in dim_names

    def test_generates_questions(self, sample_md):
        plan = analyze_spec_for_refinement(sample_md)
        assert plan.total_questions > 0

    def test_identifies_critical_gaps(self):
        vague_text = "The system should do some things TBD. Various items etc."
        plan = analyze_spec_for_refinement(vague_text)
        assert len(plan.critical_gaps) > 0

    def test_estimates_iterations(self, sample_md):
        plan = analyze_spec_for_refinement(sample_md)
        assert plan.estimated_iterations >= 1

    def test_suggested_order(self, sample_md):
        plan = analyze_spec_for_refinement(sample_md)
        assert len(plan.suggested_order) == 5


class TestRefiningTemplate:
    def test_renders_with_source(self, sample_md):
        ctx = TemplateContext(
            name="test-spec",
            extra={"source_text": sample_md},
        )
        template = get_template("refining")
        content = template.render(ctx)
        assert "Refinamento:" in content
        assert "Gaps Críticos" in content or "Ordem Sugerida" in content
        assert "Perspectiva:" in content or "Perguntas" in content

    def test_renders_blank(self):
        ctx = TemplateContext(name="blank-refine")
        template = get_template("refining")
        content = template.render(ctx)
        assert "Completude" in content
        assert "Precisão" in content
        assert "Testabilidade" in content


# ─── Build Context ────────────────────────────────────────────────────────


class TestBuildContext:
    def test_without_memory(self):
        ctx = build_context(name="Test", description="A test spec")
        assert ctx.name == "Test"
        assert ctx.memory is None
        assert ctx.skills_block == ""

    def test_with_memory(self, tmp_path):
        store = MemoryStore(root=tmp_path)
        store.init(project_name="MyProject")
        store.add_skill(ProjectSkill(name="Python", category="language"))

        ctx = build_context(name="Test", store=store)
        assert ctx.memory is not None
        assert ctx.memory.project_name == "MyProject"
        assert "Python" in ctx.skills_block

    def test_slug_generation(self):
        ctx = TemplateContext(name="My Cool Feature!")
        assert ctx.slug == "my-cool-feature"
