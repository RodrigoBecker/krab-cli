"""spec.clarify — Interactive Q&A engine for spec enrichment.

The Clarify system analyzes an existing spec and generates targeted
questions to improve its quality. It supports two modes:

1. **Interactive**: Asks questions via CLI prompts, records answers,
   and generates an enriched version of the spec.
2. **Agent-driven**: Generates a Q&A document that an AI agent can
   use to rewrite the spec with richer, more specific content.

The clarify output is a structured Q&A document that can be appended
to the spec or used as context for the agent during enrichment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@dataclass
class ClarifyQuestion:
    """A question to clarify a spec section."""

    section: str
    question: str
    category: str  # completeness, precision, context, testability, ops
    priority: str = "medium"  # low, medium, high, critical
    answer: str = ""
    answered: bool = False

    def to_markdown(self) -> str:
        priority_icon = {
            "critical": "[!!]",
            "high": "[!]",
            "medium": "[~]",
            "low": "[.]",
        }.get(self.priority, "[-]")
        status = "x" if self.answered else " "
        lines = [f"- [{status}] {priority_icon} **{self.section}**: {self.question}"]
        if self.answer:
            lines.append(f"  > **Resposta**: {self.answer}")
        return "\n".join(lines)


@dataclass
class ClarifySession:
    """A complete clarify Q&A session for a spec."""

    spec_file: str
    spec_type: str
    questions: list[ClarifyQuestion] = field(default_factory=list)
    created_at: str = ""

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def answered_count(self) -> int:
        return sum(1 for q in self.questions if q.answered)

    @property
    def completion_pct(self) -> float:
        if not self.questions:
            return 0.0
        return (self.answered_count / self.total_questions) * 100

    def by_category(self) -> dict[str, list[ClarifyQuestion]]:
        result: dict[str, list[ClarifyQuestion]] = {}
        for q in self.questions:
            result.setdefault(q.category, []).append(q)
        return result

    def by_priority(self) -> list[ClarifyQuestion]:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(self.questions, key=lambda q: order.get(q.priority, 4))


# ─── Spec Analyzer for Question Generation ──────────────────────────────


def _detect_spec_type(text: str) -> str:
    """Detect spec type from content."""
    text_lower = text.lower()
    if "gherkin" in text_lower or "scenario:" in text_lower:
        return "task"
    if "mermaid" in text_lower or "c4" in text_lower:
        return "architecture"
    if "milestone" in text_lower or "fase" in text_lower:
        return "plan"
    if "constituicao" in text_lower or "principio" in text_lower:
        return "constitution"
    if "guardrail" in text_lower or "gate" in text_lower:
        return "guardrails"
    if "runbook" in text_lower or "deploy" in text_lower:
        return "runbook"
    return "generic"


def _count_placeholders(text: str) -> list[tuple[str, int]]:
    """Find sections with placeholders."""
    results: list[tuple[str, int]] = []
    current_section = "Geral"

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            current_section = heading_match.group(2).strip()

        placeholder_patterns = [
            r"<!--.*?-->",
            r"\b(TBD|TODO|FIXME|XXX)\b",
            r"<\w+[^>]*>",
        ]
        for pattern in placeholder_patterns:
            count = len(re.findall(pattern, line))
            if count > 0:
                results.append((current_section, count))
                break

    return results


def _extract_sections(text: str) -> list[tuple[str, str]]:
    """Extract sections with their content."""
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_content: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            if current_heading:
                sections.append((current_heading, "\n".join(current_content)))
            current_heading = heading_match.group(2).strip()
            current_content = []
        else:
            current_content.append(line)

    if current_heading:
        sections.append((current_heading, "\n".join(current_content)))

    return sections


def generate_clarify_questions(text: str, spec_file: str = "") -> ClarifySession:
    """Analyze a spec and generate targeted clarification questions.

    Categories:
    - completeness: Missing sections, unfilled placeholders
    - precision: Vague terms, unmeasurable requirements
    - context: Missing project context, dependencies
    - testability: Missing scenarios, uncovered edge cases
    - ops: Missing operational info, deploy, monitoring
    """
    spec_type = _detect_spec_type(text)
    session = ClarifySession(
        spec_file=spec_file,
        spec_type=spec_type,
        created_at=datetime.now(tz=UTC).isoformat(),
    )

    # Analyze placeholders
    placeholder_sections = _count_placeholders(text)
    sections_with_placeholders = set()
    for section, _count in placeholder_sections:
        sections_with_placeholders.add(section)

    for section in sections_with_placeholders:
        session.questions.append(
            ClarifyQuestion(
                section=section,
                question=f"A secao '{section}' contem placeholders nao preenchidos. Quais dados concretos devem substituir os placeholders?",
                category="completeness",
                priority="high",
            )
        )

    # Analyze extracted sections
    sections = _extract_sections(text)
    section_names = [s[0] for s in sections]

    # Completeness questions by spec type
    if spec_type == "task":
        _add_task_questions(session, text, section_names)
    elif spec_type == "architecture":
        _add_architecture_questions(session, text, section_names)
    elif spec_type == "plan":
        _add_plan_questions(session, text, section_names)
    elif spec_type == "constitution":
        _add_constitution_questions(session, text, section_names)
    elif spec_type == "guardrails":
        _add_guardrails_questions(session, text, section_names)
    elif spec_type == "runbook":
        _add_runbook_questions(session, text, section_names)

    # Universal precision questions
    _add_precision_questions(session, text)

    # Universal context questions
    _add_context_questions(session, text)

    return session


def _add_task_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add task-specific questions."""
    scenarios = len(re.findall(r"Scenario(?:\s+Outline)?:", text))

    if scenarios < 3:
        session.questions.append(
            ClarifyQuestion(
                section="Cenarios BDD",
                question="Quais cenarios adicionais devem ser cobertos? (happy path, erro, edge case, concorrencia)",
                category="testability",
                priority="critical",
            )
        )

    if not re.search(r"(?:criterio|aceit|acceptance|done)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Criterios de Aceitacao",
                question="Quais sao as condicoes mensuraveis para considerar esta feature completa?",
                category="completeness",
                priority="critical",
            )
        )

    if not re.search(r"(?:endpoint|api|rota|route)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Notas Tecnicas",
                question="Quais endpoints/APIs serao criados ou modificados? Quais metodos HTTP e formatos de resposta?",
                category="precision",
                priority="high",
            )
        )

    if not re.search(r"(?:modelo|entity|schema|tabela|table)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Modelo de Dados",
                question="Quais entidades/tabelas serao criadas ou modificadas? Quais campos e tipos?",
                category="precision",
                priority="high",
            )
        )

    session.questions.append(
        ClarifyQuestion(
            section="Escopo",
            question="O que esta EXPLICITAMENTE fora do escopo desta task? Quais funcionalidades relacionadas NAO serao implementadas?",
            category="completeness",
            priority="medium",
        )
    )


def _add_architecture_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add architecture-specific questions."""
    if not re.search(r"mermaid", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Diagramas",
                question="Quais diagramas Mermaid devem ser incluidos? (C4, sequencia, deployment, fluxo de dados)",
                category="completeness",
                priority="high",
            )
        )

    session.questions.append(
        ClarifyQuestion(
            section="Decisoes",
            question="Quais alternativas foram consideradas e por que foram descartadas?",
            category="precision",
            priority="high",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="NFR",
            question="Quais sao os requisitos nao-funcionais? (latencia P95, throughput, disponibilidade, RPO/RTO)",
            category="precision",
            priority="critical",
        )
    )


def _add_plan_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add plan-specific questions."""
    if not re.search(r"(?:timeline|gantt|sprint|semana|milestone)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Timeline",
                question="Qual o cronograma esperado? Quais sao os milestones e suas datas alvo?",
                category="completeness",
                priority="critical",
            )
        )

    session.questions.append(
        ClarifyQuestion(
            section="Riscos",
            question="Quais sao os principais riscos do plano e como mitiga-los?",
            category="completeness",
            priority="high",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="Dependencias",
            question="Quais dependencias externas (equipes, APIs, infra) podem bloquear o plano?",
            category="precision",
            priority="high",
        )
    )


def _add_constitution_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add constitution-specific questions."""
    session.questions.append(
        ClarifyQuestion(
            section="Principios",
            question="Quais principios adicionais sao especificos para este projeto (alem dos padroes SDD)?",
            category="completeness",
            priority="high",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="Limites do Agente",
            question="Quais acoes o agente IA NUNCA deve executar sem aprovacao humana?",
            category="precision",
            priority="critical",
        )
    )


def _add_guardrails_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add guardrails-specific questions."""
    session.questions.append(
        ClarifyQuestion(
            section="Gates Customizados",
            question="Quais gates adicionais sao necessarios para este projeto? (compliance, performance, acessibilidade)",
            category="completeness",
            priority="high",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="Thresholds",
            question="Os thresholds padrao (risk < 40, ambiguidade < 5, cobertura >= 80%) sao adequados? Quais precisam de ajuste?",
            category="precision",
            priority="medium",
        )
    )


def _add_runbook_questions(
    session: ClarifySession, text: str, sections: list[str]
) -> None:
    """Add runbook-specific questions."""
    session.questions.append(
        ClarifyQuestion(
            section="Variaveis de Ambiente",
            question="Quais variaveis de ambiente sao necessarias? Liste com descricao e valores de exemplo.",
            category="completeness",
            priority="critical",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="Deploy",
            question="Qual o processo de deploy? CI/CD automatico ou manual? Quais ferramentas?",
            category="ops",
            priority="high",
        )
    )

    session.questions.append(
        ClarifyQuestion(
            section="Monitoramento",
            question="Quais metricas e alertas sao essenciais? Quais ferramentas de observabilidade serao usadas?",
            category="ops",
            priority="high",
        )
    )


def _add_precision_questions(session: ClarifySession, text: str) -> None:
    """Add universal precision questions based on vague terms."""
    vague_patterns = [
        (r"\betc\.?\b", "O que exatamente esta incluido onde foi usado 'etc'?"),
        (r"\bvarios\b", "Quantos especificamente? Quais?"),
        (r"\balguns\b", "Quais especificamente?"),
        (r"\bpossivel\b", "E obrigatorio ou opcional? Qual a prioridade?"),
        (r"\bgrande\b", "Qual o valor numerico especifico?"),
        (r"\brapido\b", "Qual o SLA em milissegundos?"),
        (r"\bseguro\b", "Quais mecanismos de seguranca especificos?"),
    ]

    found_vague = False
    for pattern, _question in vague_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            found_vague = True
            break

    if found_vague:
        session.questions.append(
            ClarifyQuestion(
                section="Precisao",
                question="A spec contem termos vagos (etc, varios, rapido, grande). Substitua cada um por valores concretos e mensuraveis.",
                category="precision",
                priority="high",
            )
        )


def _add_context_questions(session: ClarifySession, text: str) -> None:
    """Add universal context questions."""
    if not re.search(r"(?:projeto|project|stack|arquitetura)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Contexto do Projeto",
                question="O contexto do projeto (stack, arquitetura, convencoes) esta referenciado? Use `krab memory show` para verificar.",
                category="context",
                priority="medium",
            )
        )

    if not re.search(r"(?:spec\.\w+|\.sdd/specs)", text, re.IGNORECASE):
        session.questions.append(
            ClarifyQuestion(
                section="Specs Relacionadas",
                question="Quais specs existentes estao relacionadas a esta? Liste as dependencias.",
                category="context",
                priority="medium",
            )
        )


# ─── Template ─────────────────────────────────────────────────────────────


@register_template
class ClarifyTemplate(SpecTemplate):
    template_type = "clarify"
    description = "Interactive Q&A session to enrich and clarify specs"

    def render(self, ctx: TemplateContext) -> str:
        """Render a clarify Q&A document.

        If extra['source_text'] is provided, generates questions from analysis.
        If extra['session'] is provided, renders an answered session.
        Otherwise, generates a blank template.
        """
        source = ctx.extra.get("source_text", "")
        session = ctx.extra.get("session")

        if session and isinstance(session, ClarifySession):
            return self._render_session(ctx, session)
        if source:
            return self._render_analysis(ctx, source)
        return self._render_blank(ctx)

    def _render_analysis(self, ctx: TemplateContext, source: str) -> str:
        session = generate_clarify_questions(source, spec_file=ctx.name)
        return self._render_session(ctx, session)

    def _render_session(self, ctx: TemplateContext, session: ClarifySession) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# Clarify: {ctx.name}",
            "",
            f"> Sessao de Q&A para enriquecer a spec `{session.spec_file}`.",
            f"> Tipo detectado: **spec.{session.spec_type}**",
            f"> Total de perguntas: **{session.total_questions}**",
            f"> Respondidas: **{session.answered_count}** ({session.completion_pct:.0f}%)",
            "",
        ]

        # Group by category
        categories = session.by_category()
        category_labels = {
            "completeness": "Completude",
            "precision": "Precisao e Especificidade",
            "context": "Contexto e Dependencias",
            "testability": "Testabilidade",
            "ops": "Operacional",
        }

        for cat_key, cat_label in category_labels.items():
            questions = categories.get(cat_key, [])
            if not questions:
                continue

            sections.append(f"## {cat_label}")
            sections.append("")
            for q in questions:
                sections.append(q.to_markdown())
            sections.append("")

        # Instructions for agent
        sections.extend([
            "## Instrucoes para o Agente",
            "",
            "> Use as respostas acima para reescrever a spec original.",
            "> Cada resposta deve ser incorporada na secao correspondente.",
            "",
            "### Como usar este documento:",
            "",
            "1. **Modo interativo**: Responda as perguntas via `krab spec clarify <spec>`",
            "2. **Modo agente**: O agente usa este Q&A como contexto para enriquecer a spec",
            "3. **Re-analise**: Apos responder, rode `krab spec clarify <spec>` novamente",
            "",
            "### Slash Commands relacionados:",
            "",
            "```bash",
            "# Rodar clarify interativo",
            "krab spec clarify <spec>",
            "",
            "# Gerar documento de clarify sem interacao",
            "krab spec new clarify -n <nome>",
            "",
            "# Refinar spec apos clarify",
            "krab spec refine <spec>",
            "```",
        ])

        return "\n".join(sections)

    def _render_blank(self, ctx: TemplateContext) -> str:
        return f"""{self._header(ctx)}

# Clarify: {ctx.name}

> Template para sessao de Q&A interativa.
> Use `krab spec clarify <spec-file>` para gerar perguntas automaticas.

## Completude
- [ ] <!-- Pergunta sobre secoes faltantes -->

## Precisao
- [ ] <!-- Pergunta sobre termos vagos -->

## Contexto
- [ ] <!-- Pergunta sobre dependencias -->

## Testabilidade
- [ ] <!-- Pergunta sobre cenarios -->

## Operacional
- [ ] <!-- Pergunta sobre deploy/monitoramento -->
"""
