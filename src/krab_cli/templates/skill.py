"""spec.skill — Project skills and capabilities specification.

Defines the project's technical capabilities, team expertise, tools,
patterns, and conventions. This spec feeds into spec.plan for gap
analysis and into templates for context-aware generation.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class SkillTemplate(SpecTemplate):
    template_type = "skill"
    description = "Project skills, capabilities, patterns, and conventions"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# Skills: {ctx.name}",
            "",
            f"> {ctx.description or 'Definição de skills, capabilities e convenções do projeto.'}",
            "",
            self._project_context_section(ctx),
            self._languages_section(ctx),
            self._frameworks_section(ctx),
            self._patterns_section(ctx),
            self._tools_section(ctx),
            self._infra_section(ctx),
            self._conventions_section(ctx),
            self._team_section(ctx),
            self._growth_section(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _languages_section(self, ctx: TemplateContext) -> str:
        return """## Linguagens

| Linguagem | Versão | Nível | Uso Principal |
|-----------|--------|-------|---------------|
| <!-- TypeScript --> | <!-- 5.x --> | ⭐⭐⭐ Avançado | Backend + Frontend |
| <!-- Python --> | <!-- 3.12 --> | ⭐⭐ Intermediário | Scripts, ML, CLI |
| <!-- SQL --> | <!-- PostgreSQL 16 --> | ⭐⭐⭐ Avançado | Queries, migrations |
| <!-- --> | <!-- --> | <!-- --> | <!-- --> |

### Convenções de Linguagem
- **Naming**: <!-- camelCase/snake_case por contexto -->
- **Tipos**: <!-- strict mode, no any, explicit return types -->
- **Imports**: <!-- absolute paths, barrel exports -->
"""

    def _frameworks_section(self, ctx: TemplateContext) -> str:
        return """## Frameworks e Bibliotecas

### Backend
| Framework | Versão | Responsabilidade |
|-----------|--------|-----------------|
| <!-- Express/Fastify/NestJS --> | <!-- v10 --> | HTTP Server |
| <!-- Prisma/TypeORM/Drizzle --> | <!-- v5 --> | ORM/Query Builder |
| <!-- Zod/Joi --> | <!-- v3 --> | Validação |
| <!-- Jest/Vitest --> | <!-- v30 --> | Testes |

### Frontend
| Framework | Versão | Responsabilidade |
|-----------|--------|-----------------|
| <!-- React/Vue/Svelte --> | <!-- v19 --> | UI Framework |
| <!-- Next.js/Nuxt --> | <!-- v15 --> | Meta-framework |
| <!-- TailwindCSS --> | <!-- v4 --> | Styling |
| <!-- React Query/SWR --> | <!-- v5 --> | Data fetching |

### Bibliotecas Transversais
| Lib | Uso |
|-----|-----|
| <!-- winston/pino --> | Logging |
| <!-- bullmq --> | Job queue |
| <!-- ioredis --> | Cache client |
"""

    def _patterns_section(self, ctx: TemplateContext) -> str:
        arch_style = ""
        if ctx.memory and ctx.memory.architecture_style:
            arch_style = f"**Estilo principal**: {ctx.memory.architecture_style}\n"

        return f"""## Patterns e Práticas

{arch_style}
### Arquiteturais
- [ ] **Hexagonal Architecture** — Ports & Adapters para desacoplamento
- [ ] **CQRS** — Separação de leitura e escrita
- [ ] **Event Sourcing** — Histórico completo de eventos
- [ ] **Domain-Driven Design** — Bounded contexts, aggregates
- [ ] **Repository Pattern** — Abstração de persistência
- [ ] **Circuit Breaker** — Resiliência em integrações
- [ ] **Saga Pattern** — Transações distribuídas
- [ ] <!-- Outro pattern utilizado -->

### Desenvolvimento
- [ ] **SOLID** — Single Responsibility, Open/Closed, Liskov, ISP, DIP
- [ ] **Clean Code** — Naming, funções pequenas, sem side effects
- [ ] **TDD** — Test-Driven Development
- [ ] **BDD** — Behavior-Driven (Gherkin scenarios)
- [ ] **Trunk-Based Development** — Short-lived branches
- [ ] **Feature Flags** — Toggles para releases graduais
- [ ] <!-- Outra prática -->

### API Design
- [ ] **REST** — Resource-oriented, HTTP verbs corretos
- [ ] **GraphQL** — Query language para frontend flexível
- [ ] **gRPC** — Comunicação inter-serviço performática
- [ ] **OpenAPI 3.x** — Contract-first design
- [ ] **Versionamento via URL** — `/api/v1/`
"""

    def _tools_section(self, ctx: TemplateContext) -> str:
        return """## Ferramentas

### Desenvolvimento
| Ferramenta | Finalidade | Config |
|------------|-----------|--------|
| <!-- VSCode --> | IDE | `.vscode/settings.json` |
| <!-- ESLint --> | Linting JS/TS | `.eslintrc.js` |
| <!-- Prettier --> | Formatting | `.prettierrc` |
| <!-- Husky --> | Git hooks | `.husky/` |
| <!-- Commitlint --> | Conventional commits | `commitlint.config.js` |

### CI/CD
| Ferramenta | Finalidade |
|------------|-----------|
| <!-- GitHub Actions --> | Pipeline CI/CD |
| <!-- Docker --> | Containerização |
| <!-- Docker Compose --> | Dev local |
| <!-- Terraform/Pulumi --> | IaC |

### Observabilidade
| Ferramenta | Finalidade |
|------------|-----------|
| <!-- Datadog/Grafana --> | Métricas + dashboards |
| <!-- ELK/Loki --> | Log aggregation |
| <!-- Jaeger/Tempo --> | Distributed tracing |
| <!-- PagerDuty/OpsGenie --> | Alerting |
"""

    def _infra_section(self, ctx: TemplateContext) -> str:
        return """## Infraestrutura

### Cloud & Serviços
| Serviço | Provider | Tier |
|---------|----------|------|
| Compute | <!-- AWS ECS / GCP Cloud Run / K8s --> | <!-- tier --> |
| Database | <!-- RDS PostgreSQL / Cloud SQL --> | <!-- tier --> |
| Cache | <!-- ElastiCache Redis / Memorystore --> | <!-- tier --> |
| Queue | <!-- SQS / RabbitMQ / Kafka --> | <!-- tier --> |
| Storage | <!-- S3 / GCS --> | <!-- tier --> |
| CDN | <!-- CloudFront / Cloudflare --> | <!-- tier --> |
| DNS | <!-- Route53 / Cloudflare --> | <!-- tier --> |

### Ambientes
| Ambiente | URL | Propósito | Auto-deploy |
|----------|-----|-----------|-------------|
| `local` | `localhost:3000` | Desenvolvimento | — |
| `staging` | `staging.app.com` | QA/Demo | Branch `main` |
| `production` | `app.com` | Produção | Tag release |
"""

    def _conventions_section(self, ctx: TemplateContext) -> str:
        conventions_block = ""
        if ctx.memory and ctx.memory.conventions:
            items = [f"- **{k}**: {v}" for k, v in ctx.memory.conventions.items()]
            conventions_block = "\n".join(items)

        return f"""## Convenções do Projeto

{conventions_block or '<!-- Usar `krab memory set conventions.commits "conventional commits"` -->'}

### Git
- **Branching**: `feature/TICKET-description`, `fix/TICKET-description`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
- **PR**: Template obrigatório, mínimo 1 reviewer
- **Merge**: Squash merge para `main`

### Código
- **Naming**: <!-- camelCase para variáveis, PascalCase para types/classes -->
- **Estrutura de pastas**: <!-- por feature / por layer -->
- **Testes**: colocados em `__tests__/` ou `*.test.ts` ao lado do source
- **Erros**: Custom error classes, sempre com context
- **Logs**: Estruturados (JSON), com `correlation_id`

### Documentação
- **API**: OpenAPI 3.x, gerada do código ou contract-first
- **Specs**: Formato SDD (este projeto!)
- **ADRs**: Em `docs/adr/` ou na spec.architecture
- **README**: Sempre atualizado com setup instructions
"""

    def _team_section(self, ctx: TemplateContext) -> str:
        team_block = ""
        if ctx.memory and ctx.memory.team_context:
            items = [f"- **{k}**: {v}" for k, v in ctx.memory.team_context.items()]
            team_block = "\n".join(items)

        return f"""## Contexto do Time

{team_block or '<!-- Usar `krab memory set team_context.size "5 devs"` -->'}

### Perfil do Time
- **Tamanho**: <!-- N pessoas -->
- **Senioridade**: <!-- Junior/Mid/Senior mix -->
- **Fuso horário**: <!-- UTC-3 / distributed -->
- **Cerimônias**: <!-- daily, planning, retro -->

### Áreas de Expertise
<!-- Quem sabe o quê — para referência no planning -->
| Membro | Especialidade Principal | Especialidade Secundária |
|--------|------------------------|-------------------------|
| <!-- Nome --> | <!-- Backend API --> | <!-- DevOps --> |
| <!-- Nome --> | <!-- Frontend React --> | <!-- UX --> |
"""

    def _growth_section(self, ctx: TemplateContext) -> str:
        return """## Plano de Crescimento de Skills

### Gaps Identificados
| Skill | Nível Atual | Nível Desejado | Estratégia | Prazo |
|-------|-------------|----------------|-----------|-------|
| <!-- Event Sourcing --> | [!!] Nenhum | [~] Basico | Spike + PoC | <!-- 2 sprints --> |
| <!-- K8s --> | [~] Basico | [+] Operacional | Curso + pair | <!-- 4 sprints --> |

### Recursos de Aprendizado
- <!-- Link para curso/doc relevante -->
- <!-- Repositório de referência -->
- <!-- Contato de especialista -->

### Spike Técnicos Planejados
1. **<!-- Título do spike -->**: <!-- objetivo, timebox, critério de sucesso -->
2. **<!-- Título do spike -->**: <!-- objetivo, timebox, critério de sucesso -->
"""
