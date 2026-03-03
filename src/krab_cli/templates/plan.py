"""spec.plan — Planning specification template.

Generates a structured plan that references the project's skills (spec.skill)
and architecture (spec.architecture) to produce an actionable implementation
plan with phases, milestones, and resource allocation.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class PlanTemplate(SpecTemplate):
    template_type = "plan"
    description = "Implementation plan referencing skills + architecture"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# Plano: {ctx.name}",
            "",
            f"> {ctx.description or 'Plano de implementação estruturado.'}",
            "",
            self._project_context_section(ctx),
            self._objective_section(ctx),
            self._skills_assessment(ctx),
            self._architecture_alignment(ctx),
            self._phases_section(ctx),
            self._milestones_section(ctx),
            self._risk_assessment(ctx),
            self._resources_section(ctx),
            self._timeline_section(ctx),
            self._success_criteria(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _objective_section(self, ctx: TemplateContext) -> str:
        return """## Objetivo do Plano

### Problema
<!-- Qual problema este plano resolve? Qual a dor atual? -->

### Resultado Esperado
<!-- Estado desejado após execução completa do plano -->

### Métricas de Sucesso
| Métrica | Baseline | Meta | Prazo |
|---------|----------|------|-------|
| <!-- ex: Tempo de resposta API --> | <!-- 800ms --> | <!-- 200ms --> | <!-- 4 semanas --> |
| <!-- ex: Cobertura de testes --> | <!-- 30% --> | <!-- 80% --> | <!-- 6 semanas --> |
| <!-- ex: Deploys por semana --> | <!-- 1 --> | <!-- 5 --> | <!-- 8 semanas --> |

### Escopo
- **In-scope**: <!-- O que será entregue -->
- **Out-of-scope**: <!-- O que NÃO faz parte deste plano -->
- **Assumimos**: <!-- Premissas que sustentam o plano -->
"""

    def _skills_assessment(self, ctx: TemplateContext) -> str:
        skills_content = ""
        if ctx.skills_block:
            skills_content = f"""### Skills Disponíveis no Projeto

```
{ctx.skills_block}
```"""
        else:
            skills_content = """### Skills Disponíveis
<!-- Carregar com `krab memory skills` ou definir via spec.skill -->
"""

        return f"""## Avaliação de Skills

{skills_content}

### Mapa de Competências vs Necessidades

| Necessidade | Skill Existente | Gap | Ação |
|-------------|----------------|-----|------|
| <!-- ex: API REST --> | <!-- Node.js/Express --> | Nenhum | — |
| <!-- ex: Event Sourcing --> | <!-- Nenhum --> | Alto | Treinamento ou contratação |
| <!-- ex: CI/CD --> | <!-- GitHub Actions básico --> | Médio | Evolução incremental |
| <!-- ex: Monitoramento --> | <!-- Logs básicos --> | Médio | Implementar APM |

### Decisão sobre Gaps
<!-- Para cada gap identificado, qual a estratégia? -->
- **Aprender**: Investir tempo do time em capacitação
- **Contratar/Consultar**: Buscar expertise externa
- **Simplificar**: Escolher alternativa dentro das skills existentes
- **Postergar**: Mover para fase futura quando skills estiverem disponíveis
"""

    def _architecture_alignment(self, ctx: TemplateContext) -> str:
        arch_ref = ""
        if ctx.memory and ctx.memory.architecture_style:
            arch_ref = f"**Estilo vigente**: {ctx.memory.architecture_style}"

        return f"""## Alinhamento com Arquitetura

{arch_ref}

### Specs de Arquitetura Referenciadas
<!-- Links para specs.architecture que sustentam este plano -->
- `.sdd/specs/spec.architecture.*.md` — <!-- qual aspecto utilizado -->
- `.sdd/specs/spec.architecture.*.md` — <!-- qual aspecto utilizado -->

### Componentes Afetados
| Componente | Impacto | Tipo de Mudança |
|------------|---------|-----------------|
| <!-- API Gateway --> | Alto | Novo endpoint |
| <!-- Database --> | Médio | Migration |
| <!-- Worker --> | Baixo | Configuração |

### Conformidade Arquitetural
- [ ] Respeita os princípios de design documentados
- [ ] Segue padrões de API estabelecidos
- [ ] Compatível com topologia de deploy existente
- [ ] Não introduz acoplamento circular entre módulos
"""

    def _phases_section(self, ctx: TemplateContext) -> str:
        return """## Fases de Implementação

### Fase 1: Fundação (Sprint 1-2)

> Setup inicial e infraestrutura base.

```gherkin
Feature: Fundação do projeto
  Scenario: Setup do ambiente
    Given o repositório está criado
    When o desenvolvedor clona e executa setup
    Then todos os serviços sobem localmente em < 5 min

  Scenario: Pipeline CI básico
    Given código é pushado para main
    When o pipeline executa
    Then testes rodam, lint passa, build completa
```

**Entregas:**
- [ ] Estrutura do projeto (monorepo/polyrepo)
- [ ] Docker Compose para dev local
- [ ] Pipeline CI/CD básico
- [ ] Modelo de dados inicial (migration)
- [ ] Health check endpoints

### Fase 2: Core Features (Sprint 3-5)

> Implementação das funcionalidades principais.

```gherkin
Feature: Core business logic
  Scenario: CRUD principal
    Given o schema está migrado
    When o endpoint de criação é chamado com dados válidos
    Then o recurso é persistido e retornado com ID

  Scenario: Integração com serviço externo
    Given as credenciais estão configuradas
    When o fluxo de integração é acionado
    Then os dados são sincronizados com sucesso
```

**Entregas:**
- [ ] <!-- Feature principal 1 -->
- [ ] <!-- Feature principal 2 -->
- [ ] <!-- Integração principal -->
- [ ] Testes de integração

### Fase 3: Hardening (Sprint 6-7)

> Qualidade, segurança e observabilidade.

**Entregas:**
- [ ] Testes end-to-end
- [ ] Security audit (OWASP checklist)
- [ ] Rate limiting e throttling
- [ ] Logging estruturado + traces
- [ ] Alertas e dashboards
- [ ] Documentação de API (OpenAPI/Swagger)

### Fase 4: Go-Live (Sprint 8)

> Deploy e estabilização.

**Entregas:**
- [ ] Runbook operacional
- [ ] Rollback plan documentado
- [ ] Smoke tests em produção
- [ ] Métricas de negócio validadas
"""

    def _milestones_section(self, ctx: TemplateContext) -> str:
        return """## Milestones

```mermaid
gantt
    title Roadmap de Implementação
    dateFormat  YYYY-MM-DD
    section Fase 1
    Setup & Infra           :a1, 2025-01-01, 2w
    CI/CD Pipeline          :a2, after a1, 1w
    section Fase 2
    Feature Core A          :b1, after a2, 2w
    Feature Core B          :b2, after b1, 2w
    Integrações             :b3, after b1, 3w
    section Fase 3
    Testes E2E              :c1, after b3, 1w
    Security & Monitoring   :c2, after c1, 2w
    section Fase 4
    Staging Validation      :d1, after c2, 1w
    Go-Live                 :milestone, after d1, 0d
```

| # | Milestone | Critério de Aceite | Data Alvo |
|---|-----------|-------------------|-----------|
| M1 | Setup completo | Dev local funcional | <!-- data --> |
| M2 | MVP funcional | Happy path E2E | <!-- data --> |
| M3 | Quality gate | Testes > 80%, zero P0 bugs | <!-- data --> |
| M4 | Go-Live | Produção estável 48h | <!-- data --> |
"""

    def _risk_assessment(self, ctx: TemplateContext) -> str:
        return """## Avaliação de Riscos

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|---------------|---------|-----------|
| R1 | Skill gap no time | Média | Alto | Pair programming + spike técnico |
| R2 | API externa instável | Alta | Médio | Circuit breaker + fallback |
| R3 | Mudança de requisitos | Média | Alto | Entregas incrementais, feedback loop curto |
| R4 | Performance abaixo do SLA | Baixa | Alto | Load test na Fase 3, profiling precoce |
| R5 | <!-- Risco específico --> | <!-- P --> | <!-- I --> | <!-- Mitigação --> |

### Plano de Contingência
- **Se R1 ocorrer**: Contratar consultoria pontual ou simplificar escopo
- **Se R2 ocorrer**: Ativar mock service para desenvolvimento, notificar stakeholder
- **Se R3 ocorrer**: Re-priorizar backlog, proteger Fase 1 como mínimo viável
"""

    def _resources_section(self, ctx: TemplateContext) -> str:
        return """## Recursos Necessários

### Time
| Papel | Quantidade | Alocação | Fase |
|-------|-----------|----------|------|
| Backend Dev | <!-- 2 --> | Full-time | Todas |
| Frontend Dev | <!-- 1 --> | Full-time | Fase 2+ |
| QA | <!-- 1 --> | Part-time | Fase 2-3 |
| DevOps | <!-- 1 --> | Part-time | Fase 1, 4 |

### Infraestrutura
- <!-- Cloud provider e tier -->
- <!-- Serviços gerenciados (DB, Cache, Queue) -->
- <!-- Licenças de ferramentas -->

### Budget Estimado
| Item | Custo Mensal | Observação |
|------|-------------|------------|
| Infra Cloud | <!-- R$ --> | <!-- detalhes --> |
| Tooling | <!-- R$ --> | <!-- detalhes --> |
| Consultoria | <!-- R$ --> | <!-- se aplicável --> |
"""

    def _timeline_section(self, ctx: TemplateContext) -> str:
        return """## Timeline

| Semana | Atividade Principal | Entrega |
|--------|-------------------|---------|
| S1-S2 | Setup, CI/CD, DB schema | M1: Ambiente funcional |
| S3-S4 | Feature Core A + testes | Feature A em staging |
| S5-S6 | Feature Core B + integrações | M2: MVP funcional |
| S7-S8 | E2E, security, monitoring | M3: Quality gate |
| S9 | Staging validation + docs | M4: Go-Live ready |
| S10 | Go-Live + stabilization | Produção estável |
"""

    def _success_criteria(self, ctx: TemplateContext) -> str:
        return """## Critérios de Sucesso do Plano

### Técnicos
- [ ] Todos os milestones atingidos dentro do prazo
- [ ] Cobertura de testes >= 80%
- [ ] Zero bugs P0/P1 em produção após 48h
- [ ] Latência p99 dentro do SLA
- [ ] Pipeline CI/CD < 10min

### Negócio
- [ ] Stakeholders validaram as entregas
- [ ] Métricas de negócio atingidas
- [ ] Documentação completa e atualizada
- [ ] Time capacitado para manutenção autônoma
"""
