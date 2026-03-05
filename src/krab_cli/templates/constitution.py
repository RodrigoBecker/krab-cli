"""spec.constitution — Project Constitution spec template.

The Constitution is the foundational document of the project. It defines
the project's identity, principles, boundaries, and core decisions that
guide all development. It is a living document that evolves with the project.

This spec is global — it influences all other specs during refinement
and provides context for AI agents.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class ConstitutionTemplate(SpecTemplate):
    template_type = "constitution"
    description = "Project constitution — identity, principles, boundaries, and core decisions"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# {ctx.name}",
            "",
            "> Documento fundacional do projeto. Define identidade, principios,",
            "> limites e decisoes centrais que guiam todo o desenvolvimento.",
            "> Este documento e global e influencia todas as specs do projeto.",
            "",
            self._project_context_section(ctx),
            self._identity_section(ctx),
            self._principles_section(ctx),
            self._boundaries_section(ctx),
            self._architecture_decisions(ctx),
            self._quality_standards(ctx),
            self._communication_section(ctx),
            self._evolution_section(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _identity_section(self, ctx: TemplateContext) -> str:
        project_name = ""
        description = ""
        if ctx.memory:
            project_name = ctx.memory.project_name or ""
            description = ctx.memory.description or ""

        return f"""## Identidade do Projeto

### Nome
{project_name or '<!-- Nome do projeto -->'}

### Proposito
{description or '<!-- Qual problema este projeto resolve? Para quem? -->'}

### Visao
<!-- Onde este projeto estara em 6-12 meses? Qual o estado ideal? -->

### Dominio
<!-- Qual o dominio de negocio? Quais sao os conceitos centrais? -->

### Stakeholders
| Papel | Responsabilidade | Contexto |
|-------|-----------------|----------|
| <!-- Product Owner --> | <!-- Decisoes de produto --> | <!-- ... --> |
| <!-- Tech Lead --> | <!-- Decisoes tecnicas --> | <!-- ... --> |
| <!-- Agente IA --> | <!-- Implementacao --> | <!-- ... --> |
"""

    def _principles_section(self, ctx: TemplateContext) -> str:
        return """## Principios de Desenvolvimento

> Principios sao diretrizes imutaveis que guiam todas as decisoes tecnicas.
> Cada principio deve ter uma justificativa clara.

### 1. Spec-Driven Development (SDD)
- **Regra**: Toda feature comeca com uma spec antes da implementacao.
- **Justificativa**: Specs reduzem ambiguidade e alucinacao do agente IA.
- **Aplicacao**: Usar `krab spec new task` antes de qualquer codigo.

### 2. Testabilidade
- **Regra**: Todo requisito deve ter cenarios Gherkin verificaveis.
- **Justificativa**: Cenarios Gherkin sao a ponte entre spec e teste.
- **Aplicacao**: Minimo 3 cenarios por spec (happy path, erro, edge case).

### 3. Precisao sobre Generalidade
- **Regra**: Evitar termos vagos (TBD, varios, etc). Ser especifico.
- **Justificativa**: Termos vagos aumentam risco de hallucination.
- **Aplicacao**: Usar `krab analyze ambiguity` para validar.

### 4. Evolucao Incremental
- **Regra**: Mudancas pequenas e frequentes sobre mudancas grandes e raras.
- **Justificativa**: Reduz risco, facilita review, melhora qualidade.
- **Aplicacao**: Cada PR deve mapear para 1 spec.

### 5. <!-- Principio customizado -->
- **Regra**: <!-- Regra clara -->
- **Justificativa**: <!-- Por que esta regra existe? -->
- **Aplicacao**: <!-- Como aplicar na pratica? -->
"""

    def _boundaries_section(self, ctx: TemplateContext) -> str:
        constraints = ""
        if ctx.memory and ctx.memory.constraints:
            constraints = "\n".join(f"- {c}" for c in ctx.memory.constraints)

        integrations = ""
        if ctx.memory and ctx.memory.integrations:
            integrations = "\n".join(f"- {i}" for i in ctx.memory.integrations)

        return f"""## Limites e Restricoes

### O que este projeto FAZ
<!-- Escopo positivo — funcionalidades e responsabilidades -->
- <!-- Funcionalidade 1 -->
- <!-- Funcionalidade 2 -->

### O que este projeto NAO FAZ
<!-- Escopo negativo — o que esta explicitamente fora do escopo -->
- <!-- Responsabilidade que pertence a outro sistema -->
- <!-- Funcionalidade que nao sera implementada -->

### Restricoes Tecnicas
{constraints or '<!-- Restricoes de performance, seguranca, compliance, etc. -->'}

### Integracoes Externas
{integrations or '<!-- Servicos, APIs, bancos de dados externos -->'}

### Limites de Autonomia do Agente
- O agente IA **pode**: implementar features conforme specs, criar testes, refatorar
- O agente IA **nao pode**: alterar schemas de banco sem aprovacao, modificar configs de infra
- O agente IA **deve perguntar quando**: encontrar ambiguidade na spec, decisao arquitetural
"""

    def _architecture_decisions(self, ctx: TemplateContext) -> str:
        arch_style = ""
        tech_stack = ""
        if ctx.memory:
            if ctx.memory.architecture_style:
                arch_style = ctx.memory.architecture_style
            if ctx.memory.tech_stack:
                tech_stack = "\n".join(
                    f"- **{k}**: {v}" for k, v in ctx.memory.tech_stack.items()
                )

        return f"""## Decisoes Arquiteturais

### Estilo de Arquitetura
{arch_style or '<!-- monolith, microservices, hexagonal, event-driven, etc. -->'}

### Tech Stack
{tech_stack or '<!-- Definir via `krab memory set tech_stack.backend "..."` -->'}

### Decisoes Registradas (ADR)

> Use `krab memory` para registrar ADRs.
> Cada decisao deve ter contexto, opcoes consideradas e consequencias.

| # | Decisao | Status | Justificativa |
|---|---------|--------|--------------|
| 1 | <!-- Decisao --> | <!-- accepted/proposed/deprecated --> | <!-- Por que --> |
| 2 | <!-- Decisao --> | <!-- accepted/proposed/deprecated --> | <!-- Por que --> |

### Padroes Adotados
<!-- Design patterns, coding patterns, etc -->
- <!-- Pattern 1: justificativa -->
- <!-- Pattern 2: justificativa -->
"""

    def _quality_standards(self, ctx: TemplateContext) -> str:
        conventions = ""
        if ctx.memory and ctx.memory.conventions:
            conventions = "\n".join(
                f"- **{k}**: {v}" for k, v in ctx.memory.conventions.items()
            )

        return f"""## Padroes de Qualidade

### Convencoes de Codigo
{conventions or '<!-- Definir via `krab memory set conventions.naming "..."` -->'}

### Metricas de Qualidade
| Metrica | Alvo | Ferramenta |
|---------|------|-----------|
| Cobertura de testes | >= 80% | pytest --cov |
| Risk score da spec | < 40/100 | krab analyze risk |
| Ambiguidade da spec | < 5 termos vagos | krab analyze ambiguity |
| Lint | 0 errors | ruff check |

### Definition of Done (Global)
- [ ] Spec aprovada (risk score < 40)
- [ ] Todos os cenarios Gherkin implementados como testes
- [ ] Code review aprovado
- [ ] Lint/type-check sem erros
- [ ] Documentacao atualizada
- [ ] Deploy em staging validado
"""

    def _communication_section(self, ctx: TemplateContext) -> str:
        return """## Comunicacao e Contexto

### Idioma
- Specs: pt-BR
- Codigo: en-US (variaveis, funcoes, classes)
- Commits: en-US (conventional commits)

### Formato de Specs
- Template: Gherkin BDD (Given/When/Then)
- Diagramas: Mermaid
- Modelo de dados: inline no spec
- Versionamento: Git + `.sdd/specs/`

### Como o Agente Deve Ler Este Documento
1. Leia a Constituicao antes de qualquer implementacao
2. Respeite os principios — eles sao inegociaveis
3. Consulte os limites antes de tomar decisoes
4. Verifique as convencoes antes de escrever codigo
5. Na duvida, gere uma spec primeiro
"""

    def _evolution_section(self, ctx: TemplateContext) -> str:
        return """## Evolucao da Constituicao

> Este documento evolui com o projeto. Atualize-o quando:
> - Uma nova decisao arquitetural for tomada
> - Um novo principio for estabelecido
> - Limites de escopo mudarem
> - Convencoes forem atualizadas

### Historico de Mudancas
| Data | Mudanca | Motivacao |
|------|---------|-----------|
| <!-- data --> | <!-- o que mudou --> | <!-- por que --> |

### Comandos Uteis

```bash
# Atualizar a constituicao
krab spec clarify .sdd/specs/spec.constitution.constituicao-do-projeto.md

# Validar qualidade da constituicao
krab analyze risk .sdd/specs/spec.constitution.constituicao-do-projeto.md

# Refinar a constituicao com Tree-of-Thought
krab spec refine .sdd/specs/spec.constitution.constituicao-do-projeto.md
```
"""
