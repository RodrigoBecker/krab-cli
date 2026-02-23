"""spec.refining — Tree-of-Thought refinement engine for specs.

Analyzes an existing spec and generates structured refinement questions
using Tree-of-Thought (ToT) prompting. Produces a refinement document
that guides the user (or an AI agent) through improving the spec by
exploring multiple reasoning paths.

The ToT approach:
1. DECOMPOSE — Break the spec into concern dimensions
2. BRANCH — Generate multiple perspectives for each dimension
3. EVALUATE — Assess completeness and precision of each branch
4. SYNTHESIZE — Merge best insights into refinement recommendations
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@dataclass
class RefinementDimension:
    """A dimension/concern to analyze in the spec."""

    name: str
    description: str
    questions: list[str] = field(default_factory=list)
    branches: list[RefinementBranch] = field(default_factory=list)
    completeness: float = 0.0  # 0-1


@dataclass
class RefinementBranch:
    """A reasoning branch within a dimension."""

    perspective: str
    thought: str
    questions: list[str]
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class RefinementPlan:
    """Complete refinement plan for a spec."""

    spec_type: str
    dimensions: list[RefinementDimension]
    critical_gaps: list[str]
    suggested_order: list[str]
    estimated_iterations: int

    @property
    def total_questions(self) -> int:
        return sum(
            len(d.questions) + sum(len(b.questions) for b in d.branches) for d in self.dimensions
        )


# ─── Spec Analyzers ──────────────────────────────────────────────────────


def _detect_spec_type(text: str) -> str:
    """Detect what kind of spec this is."""
    text_lower = text.lower()
    if "gherkin" in text_lower or "scenario:" in text_lower or "given" in text_lower:
        return "task"
    if "mermaid" in text_lower or "c4" in text_lower or "deployment" in text_lower:
        return "architecture"
    if "milestone" in text_lower or "fase" in text_lower or "sprint" in text_lower:
        return "plan"
    if "framework" in text_lower and "linguagem" in text_lower:
        return "skill"
    return "generic"


def _check_section_presence(text: str, patterns: list[tuple[str, str]]) -> dict[str, bool]:
    """Check which expected sections are present."""
    result = {}
    for section_name, pattern in patterns:
        result[section_name] = bool(re.search(pattern, text, re.IGNORECASE))
    return result


def _count_placeholders(text: str) -> int:
    """Count unfilled template placeholders."""
    patterns = [
        r"<!--.*?-->",
        r"\b(TBD|TODO|FIXME|XXX)\b",
        r"<\w+>",  # <tipo de usuário>
    ]
    count = 0
    for p in patterns:
        count += len(re.findall(p, text))
    return count


def _count_gherkin_scenarios(text: str) -> int:
    """Count Gherkin scenarios."""
    return len(re.findall(r"^\s*Scenario(?:\s+Outline)?:", text, re.MULTILINE))


def _count_mermaid_diagrams(text: str) -> int:
    """Count Mermaid diagram blocks."""
    return len(re.findall(r"```mermaid", text))


def _extract_headings(text: str) -> list[tuple[int, str]]:
    """Extract markdown headings with level."""
    return [
        (len(m.group(1)), m.group(2).strip())
        for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
    ]


# ─── Dimension Builders ──────────────────────────────────────────────────


def _build_completeness_dimension(text: str, spec_type: str) -> RefinementDimension:
    """Analyze structural completeness."""
    dim = RefinementDimension(
        name="Completude Estrutural",
        description="Verifica se todas as seções esperadas estão presentes e preenchidas.",
    )

    placeholders = _count_placeholders(text)
    headings = _extract_headings(text)
    heading_count = len(headings)

    if placeholders > 10:
        dim.branches.append(
            RefinementBranch(
                perspective="Preenchimento",
                thought=f"Há {placeholders} placeholders não preenchidos. Seções com <!-- --> precisam de conteúdo real.",
                questions=[
                    "Quais placeholders são críticos para o entendimento do agente?",
                    "Algum placeholder pode ser removido por não se aplicar ao projeto?",
                    "Há informações no projeto (memory/skills) que já respondem esses placeholders?",
                ],
                priority="high",
            )
        )

    if heading_count < 3:
        dim.branches.append(
            RefinementBranch(
                perspective="Estrutura",
                thought="Spec tem poucas seções. Uma spec bem estruturada geralmente tem 5-10 seções.",
                questions=[
                    "Que seções adicionais dariam mais clareza ao agente?",
                    "A spec cobre tanto o 'o quê' quanto o 'como'?",
                ],
                priority="medium",
            )
        )

    # Type-specific checks
    if spec_type == "task":
        scenarios = _count_gherkin_scenarios(text)
        if scenarios == 0:
            dim.questions.append("Faltam cenários Gherkin — como o agente saberá o que testar?")
            dim.completeness = 0.3
        elif scenarios < 3:
            dim.questions.append(
                f"Apenas {scenarios} cenário(s) Gherkin. Considerar: happy path, erro, edge case."
            )
            dim.completeness = 0.6
        else:
            dim.completeness = 0.8

    elif spec_type == "architecture":
        diagrams = _count_mermaid_diagrams(text)
        if diagrams == 0:
            dim.questions.append(
                "Sem diagramas Mermaid. Diagramas visuais são essenciais para specs de arquitetura."
            )
            dim.completeness = 0.3
        else:
            dim.completeness = 0.7

    elif spec_type == "plan":
        has_timeline = bool(
            re.search(r"(?:timeline|gantt|sprint|semana|milestone)", text, re.IGNORECASE)
        )
        if not has_timeline:
            dim.questions.append("Plano sem timeline definida. Quando cada fase será executada?")
            dim.completeness = 0.4
        else:
            dim.completeness = 0.7

    return dim


def _build_precision_dimension(text: str) -> RefinementDimension:
    """Analyze precision and specificity."""
    from krab_cli.core.ambiguity import detect_ambiguity

    dim = RefinementDimension(
        name="Precisão e Especificidade",
        description="Avalia se a linguagem é precisa o suficiente para evitar ambiguidade.",
    )

    report = detect_ambiguity(text)

    if report.ambiguous_terms > 0:
        # Branch 1: Fix vague terms
        high_terms = [m for m in report.matches if m.severity == "HIGH"]
        if high_terms:
            term_list = ", ".join(set(m.term for m in high_terms[:5]))
            dim.branches.append(
                RefinementBranch(
                    perspective="Termos vagos de alta severidade",
                    thought=f"Encontrados termos críticos: {term_list}. Estes aumentam significativamente o risco de hallucination.",
                    questions=[
                        f"O que exatamente significa '{high_terms[0].term}' neste contexto? Substituir por valor concreto.",
                        "Cada 'TBD/TODO' pode ser resolvido agora ou deve virar um ticket separado?",
                        "Os termos vagos refletem incerteza genuína ou apenas falta de especificação?",
                    ],
                    priority="critical",
                )
            )

        # Branch 2: Quantifiability
        dim.branches.append(
            RefinementBranch(
                perspective="Mensurabilidade",
                thought="Requisitos devem ser mensuráveis para que o agente possa validar a implementação.",
                questions=[
                    "Todo requisito tem um critério de aceite verificável?",
                    "Limites numéricos estão explícitos (timeout, max items, rate limits)?",
                    "Formatos de dados estão especificados (ISO 8601, UUID v4, UTF-8)?",
                ],
                priority="high",
            )
        )

    dim.completeness = report.precision_score / 100
    return dim


def _build_coherence_dimension(text: str, spec_type: str) -> RefinementDimension:
    """Analyze internal coherence and consistency."""
    dim = RefinementDimension(
        name="Coerência Interna",
        description="Verifica se as partes da spec são consistentes entre si.",
    )

    # Branch 1: Cross-reference check
    dim.branches.append(
        RefinementBranch(
            perspective="Referências cruzadas",
            thought="Seções que se referenciam devem ser consistentes. Endpoints na seção técnica devem mapear para cenários Gherkin.",
            questions=[
                "Cada endpoint mencionado tem pelo menos um cenário Gherkin correspondente?",
                "O modelo de dados suporta todos os campos necessários para os cenários?",
                "As dependências listadas estão refletidas na seção técnica?",
            ],
            priority="high",
        )
    )

    # Branch 2: Terminology consistency
    dim.branches.append(
        RefinementBranch(
            perspective="Consistência terminológica",
            thought="O mesmo conceito deve usar o mesmo termo em toda a spec. Misturar 'usuário'/'user'/'cliente' confunde o agente.",
            questions=[
                "Existe um glossário de termos do domínio? Se não, quais termos precisam ser definidos?",
                "Os nomes de entidades são consistentes entre diagramas, Gherkin e modelo de dados?",
                "Os termos técnicos estão em inglês ou português? Há mistura?",
            ],
            priority="medium",
        )
    )

    dim.completeness = 0.5  # Hard to auto-assess
    return dim


def _build_agent_readiness_dimension(text: str) -> RefinementDimension:
    """Analyze if spec is optimized for AI agent consumption."""
    from krab_cli.core.readability import flesch_kincaid_grade

    dim = RefinementDimension(
        name="Prontidão para Agente IA",
        description="Avalia se a spec está otimizada para consumo por agentes de IA.",
    )

    fk_grade = flesch_kincaid_grade(text)
    token_estimate = len(text) // 4

    # Branch 1: Token efficiency
    if token_estimate > 4000:
        dim.branches.append(
            RefinementBranch(
                perspective="Eficiência de tokens",
                thought=f"Spec usa ~{token_estimate} tokens. Specs longas podem exceder a janela de contexto do agente.",
                questions=[
                    "Quais seções podem ser comprimidas sem perda de informação?",
                    "Há repetição que pode ser eliminada com aliases (usar `krab optimize`)?",
                    "A spec pode ser dividida em specs menores e mais focadas?",
                ],
                priority="medium" if token_estimate < 8000 else "high",
            )
        )

    # Branch 2: Clarity for agents
    if fk_grade > 16:
        dim.branches.append(
            RefinementBranch(
                perspective="Clareza textual",
                thought=f"Flesch-Kincaid grade {fk_grade} indica texto muito complexo. Simplificar reduz hallucination.",
                questions=[
                    "Sentenças longas podem ser quebradas em frases mais curtas?",
                    "Jargão pode ser substituído por termos mais diretos?",
                    "Parágrafos podem ser convertidos em listas estruturadas?",
                ],
                priority="medium",
            )
        )

    # Branch 3: Explicit context
    dim.branches.append(
        RefinementBranch(
            perspective="Contexto explícito",
            thought="Agentes não têm contexto implícito. Toda informação necessária deve estar na spec.",
            questions=[
                "Um agente sem conhecimento prévio do projeto conseguiria implementar a partir desta spec?",
                "As convenções do projeto (naming, patterns, stack) estão referenciadas?",
                "Há links para specs relacionadas que o agente precisaria consultar?",
            ],
            priority="high",
        )
    )

    dim.completeness = 0.5
    return dim


def _build_testability_dimension(text: str, spec_type: str) -> RefinementDimension:
    """Analyze if spec produces testable requirements."""
    dim = RefinementDimension(
        name="Testabilidade",
        description="Avalia se os requisitos são verificáveis e testáveis.",
    )

    scenarios = _count_gherkin_scenarios(text)
    has_acceptance = bool(re.search(r"(?:critério|aceit|acceptance|done)", text, re.IGNORECASE))

    if spec_type == "task":
        # Branch 1: Scenario coverage
        dim.branches.append(
            RefinementBranch(
                perspective="Cobertura de cenários",
                thought=f"{'Bom: ' + str(scenarios) + ' cenários' if scenarios >= 3 else 'Poucos cenários. Cada requisito deveria ter pelo menos 1 cenário.'}",
                questions=[
                    "Happy path está coberto com dados realistas?",
                    "Cenários de erro incluem mensagens de erro específicas (não genéricas)?",
                    "Edge cases estão documentados (concorrência, timeout, dados inválidos)?",
                    "Há Scenario Outline para variações paramétricas?",
                ],
                priority="high",
            )
        )

        # Branch 2: Acceptance criteria quality
        if not has_acceptance:
            dim.branches.append(
                RefinementBranch(
                    perspective="Critérios de aceitação",
                    thought="Sem critérios de aceitação explícitos. O agente não saberá quando a task está 'done'.",
                    questions=[
                        "Quais são as condições mensuráveis para considerar a feature completa?",
                        "Os critérios são independentes e atômicos?",
                    ],
                    priority="critical",
                )
            )

    elif spec_type == "architecture":
        dim.branches.append(
            RefinementBranch(
                perspective="Validação arquitetural",
                thought="Specs de arquitetura devem ter critérios verificáveis (SLAs, capacidade, compliance).",
                questions=[
                    "Os requisitos não-funcionais têm valores concretos (latência, throughput)?",
                    "A arquitetura pode ser validada com um PoC antes da implementação?",
                    "Há cenários de failure mode documentados?",
                ],
                priority="high",
            )
        )

    dim.completeness = min(scenarios / 5, 1.0) if spec_type == "task" else 0.5
    return dim


# ─── Main Analyzer ────────────────────────────────────────────────────────


def analyze_spec_for_refinement(text: str) -> RefinementPlan:
    """Analyze a spec and generate a Tree-of-Thought refinement plan.

    Steps:
    1. Detect spec type
    2. Build analysis dimensions
    3. Generate branching questions
    4. Prioritize and order
    """
    spec_type = _detect_spec_type(text)

    dimensions = [
        _build_completeness_dimension(text, spec_type),
        _build_precision_dimension(text),
        _build_coherence_dimension(text, spec_type),
        _build_agent_readiness_dimension(text),
        _build_testability_dimension(text, spec_type),
    ]

    # Identify critical gaps
    critical_gaps: list[str] = []
    for dim in dimensions:
        if dim.completeness < 0.4:
            critical_gaps.append(f"{dim.name}: completude {dim.completeness:.0%}")
        for branch in dim.branches:
            if branch.priority == "critical":
                critical_gaps.append(f"{dim.name}/{branch.perspective}")

    # Suggested order: critical first, then by completeness (lowest first)
    suggested_order = [
        d.name for d in sorted(dimensions, key=lambda d: (d.completeness, -len(d.questions)))
    ]

    # Estimate iterations
    total_questions = sum(
        len(d.questions) + sum(len(b.questions) for b in d.branches) for d in dimensions
    )
    estimated_iterations = max(1, total_questions // 5)

    return RefinementPlan(
        spec_type=spec_type,
        dimensions=dimensions,
        critical_gaps=critical_gaps,
        suggested_order=suggested_order,
        estimated_iterations=estimated_iterations,
    )


# ─── Template ─────────────────────────────────────────────────────────────


@register_template
class RefiningTemplate(SpecTemplate):
    template_type = "refining"
    description = "Tree-of-Thought spec refinement with structured questioning"

    def render(self, ctx: TemplateContext) -> str:
        """Render a refinement spec.

        If extra['source_text'] is provided, analyzes that spec.
        Otherwise, generates a blank refinement template.
        """
        source = ctx.extra.get("source_text", "")

        if source:
            return self._render_analysis(ctx, source)
        return self._render_blank(ctx)

    def _render_analysis(self, ctx: TemplateContext, source: str) -> str:
        plan = analyze_spec_for_refinement(source)

        sections = [
            self._header(ctx),
            "",
            f"# Refinamento: {ctx.name}",
            "",
            "> Análise Tree-of-Thought para refinamento de spec.",
            f"> Tipo detectado: **spec.{plan.spec_type}**",
            f"> Total de perguntas: **{plan.total_questions}**",
            f"> Iterações estimadas: **{plan.estimated_iterations}**",
            "",
        ]

        # Critical gaps
        if plan.critical_gaps:
            sections.append("## [!] Gaps Criticos\n")
            for gap in plan.critical_gaps:
                sections.append(f"- **{gap}**")
            sections.append("")

        # Suggested order
        sections.append("## Ordem Sugerida de Refinamento\n")
        for i, name in enumerate(plan.suggested_order, 1):
            sections.append(f"{i}. {name}")
        sections.append("")

        # Each dimension
        for dim in plan.dimensions:
            sections.append(f"## {dim.name}")
            sections.append(f"\n> {dim.description}")
            sections.append(f"> Completude: **{dim.completeness:.0%}**\n")

            # Direct questions
            if dim.questions:
                sections.append("### Perguntas Diretas\n")
                for q in dim.questions:
                    sections.append(f"- [ ] {q}")
                sections.append("")

            # Branches (Tree of Thought)
            for branch in dim.branches:
                priority_icon = {
                    "critical": "[!!]",
                    "high": "[!]",
                    "medium": "[~]",
                    "low": "[.]",
                }.get(branch.priority, "[-]")

                sections.append(f"### {priority_icon} Perspectiva: {branch.perspective}")
                sections.append(f"\n**Pensamento**: {branch.thought}\n")
                sections.append("**Perguntas para explorar:**\n")
                for q in branch.questions:
                    sections.append(f"- [ ] {q}")
                sections.append("")

        # Next steps
        sections.extend(
            [
                "## Próximos Passos",
                "",
                "1. Responda as perguntas marcadas como [!!] (critico) primeiro",
                "2. Use `krab spec refine <arquivo>` novamente após cada rodada",
                "3. Quando todas as perguntas forem resolvidas, rode `krab analyze risk` para validar",
                "4. Atualize a spec original com as respostas",
                "",
                "### Comandos Úteis",
                "",
                "```bash",
                "# Re-analisar após mudanças",
                "krab spec refine spec-atualizada.md",
                "",
                "# Verificar risco de hallucination",
                "krab analyze risk spec-atualizada.md",
                "",
                "# Verificar ambiguidade restante",
                "krab analyze ambiguity spec-atualizada.md",
                "",
                "# Otimizar tokens antes de enviar ao agente",
                "krab optimize run spec-atualizada.md -o spec-final.md",
                "```",
            ]
        )

        return "\n".join(sections)

    def _render_blank(self, ctx: TemplateContext) -> str:
        return f"""{self._header(ctx)}

# Refinamento: {ctx.name}

> Template para refinamento Tree-of-Thought.
> Use `krab spec refine <spec-file>` para gerar análise automática.

## Dimensões de Análise

### 1. Completude Estrutural
- [ ] Todas as seções esperadas estão presentes?
- [ ] Placeholders foram preenchidos com dados reais?
- [ ] Cenários Gherkin cobrem happy path + edge cases?

### 2. Precisão e Especificidade
- [ ] Termos vagos foram substituídos por valores concretos?
- [ ] Requisitos são mensuráveis e verificáveis?
- [ ] Limites numéricos estão explícitos?

### 3. Coerência Interna
- [ ] Referências cruzadas são consistentes?
- [ ] Terminologia é uniforme em toda a spec?
- [ ] Modelo de dados suporta todos os cenários?

### 4. Prontidão para Agente
- [ ] Token count está dentro da janela de contexto?
- [ ] Texto é claro e direto?
- [ ] Contexto implícito está explicitado?

### 5. Testabilidade
- [ ] Cada requisito tem cenário Gherkin correspondente?
- [ ] Critérios de aceitação são atômicos e independentes?
- [ ] Edge cases estão documentados?
"""
