"""spec.architecture — Architecture specification template.

Generates architecture specs with Mermaid diagrams, component definitions,
data flow, deployment topology, and decision records.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class ArchitectureTemplate(SpecTemplate):
    template_type = "architecture"
    description = "Architecture spec with Mermaid diagrams, C4 model, ADRs"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# Arquitetura: {ctx.name}",
            "",
            f"> {ctx.description or 'Definição arquitetural do sistema/módulo.'}",
            "",
            self._project_context_section(ctx),
            self._overview_section(ctx),
            self._c4_context(ctx),
            self._c4_containers(ctx),
            self._c4_components(ctx),
            self._data_flow(ctx),
            self._data_model(ctx),
            self._api_contracts(ctx),
            self._deployment(ctx),
            self._security(ctx),
            self._decisions(ctx),
            self._constraints_section(ctx),
            self._evolution(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _overview_section(self, ctx: TemplateContext) -> str:
        arch_style = ""
        if ctx.memory and ctx.memory.architecture_style:
            arch_style = f"**Estilo**: {ctx.memory.architecture_style}"

        return f"""## Visão Geral

### Objetivo Arquitetural
<!-- Qual problema de design esta arquitetura resolve? -->

### Estilo Arquitetural
{arch_style or "<!-- monolith | microservices | hexagonal | event-driven | serverless | modular-monolith -->"}

### Princípios de Design
- **Separação de responsabilidades** — cada módulo tem uma única razão para mudar
- **Inversão de dependência** — módulos dependem de abstrações, não de implementações
- **Fail-fast** — erros são detectados e reportados o mais cedo possível
- <!-- Adicionar princípios específicos do projeto -->

### Requisitos Não-Funcionais
| Atributo | Meta | Métrica |
|----------|------|---------|
| Disponibilidade | <!-- 99.9% --> | Uptime mensal |
| Latência | <!-- p99 < 200ms --> | Percentil 99 |
| Throughput | <!-- 1000 rps --> | Requests/segundo |
| Escalabilidade | <!-- horizontal --> | Instâncias |
| Segurança | <!-- OWASP Top 10 --> | Compliance |
"""

    def _c4_context(self, ctx: TemplateContext) -> str:
        return """## Diagrama de Contexto (C4 Level 1)

> Visão macro: sistema, usuários e sistemas externos.

```mermaid
graph TB
    subgraph Usuários
        U1[Usuário Final]
        U2[Administrador]
    end

    subgraph Sistema["Sistema Principal"]
        APP[Aplicação]
    end

    subgraph Externos
        EXT1[Serviço Externo A]
        EXT2[Banco de Dados]
        EXT3[Fila de Mensagens]
    end

    U1 -->|"HTTP/REST"| APP
    U2 -->|"HTTP/REST"| APP
    APP -->|"API"| EXT1
    APP -->|"SQL/ORM"| EXT2
    APP -->|"AMQP/Kafka"| EXT3
```
"""

    def _c4_containers(self, ctx: TemplateContext) -> str:
        return """## Diagrama de Containers (C4 Level 2)

> Quais processos/deploys compõem o sistema.

```mermaid
graph TB
    subgraph Frontend
        WEB[Web App<br/>React/Next.js]
        MOBILE[Mobile App<br/>React Native]
    end

    subgraph Backend
        API[API Gateway<br/>REST/GraphQL]
        SVC1[Serviço A<br/><!-- domínio -->]
        SVC2[Serviço B<br/><!-- domínio -->]
        WORKER[Worker<br/>Jobs assíncronos]
    end

    subgraph Data
        DB[(PostgreSQL<br/>Dados principais)]
        CACHE[(Redis<br/>Cache/Session)]
        QUEUE[RabbitMQ/Kafka<br/>Mensageria]
        STORAGE[S3/MinIO<br/>Arquivos]
    end

    WEB --> API
    MOBILE --> API
    API --> SVC1
    API --> SVC2
    SVC1 --> DB
    SVC1 --> CACHE
    SVC2 --> DB
    SVC1 --> QUEUE
    QUEUE --> WORKER
    WORKER --> DB
    WORKER --> STORAGE
```
"""

    def _c4_components(self, ctx: TemplateContext) -> str:
        return """## Diagrama de Componentes (C4 Level 3)

> Estrutura interna de um container específico.

```mermaid
graph LR
    subgraph "Serviço Principal"
        direction TB
        CTRL[Controller<br/>HTTP handlers]
        UC[Use Cases<br/>Application layer]
        DOM[Domain<br/>Entities + Rules]
        REPO[Repository<br/>Data access]
        PORT[Ports<br/>Interfaces]
        ADAPT[Adapters<br/>Implementations]
    end

    CTRL --> UC
    UC --> DOM
    UC --> PORT
    PORT -.-> ADAPT
    ADAPT --> REPO

    style DOM fill:#e1f5fe
    style PORT fill:#fff3e0
    style ADAPT fill:#f3e5f5
```

### Responsabilidades dos Componentes

| Componente | Responsabilidade | Depende de |
|------------|-----------------|------------|
| **Controller** | Recebe HTTP, valida input, chama use case | Use Case |
| **Use Case** | Orquestra lógica de aplicação | Domain, Ports |
| **Domain** | Regras de negócio puras | Nenhum |
| **Repository** | Persistência de dados | Adapter DB |
| **Ports** | Interfaces/contratos (abstrações) | Nenhum |
| **Adapters** | Implementações concretas | Ports |
"""

    def _data_flow(self, ctx: TemplateContext) -> str:
        return """## Fluxo de Dados

### Fluxo Principal (Happy Path)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as API Gateway
    participant SVC as Service
    participant DB as Database
    participant CACHE as Cache

    User->>FE: Ação do usuário
    FE->>API: POST /api/v1/resource
    API->>API: Valida JWT
    API->>SVC: Processa request
    SVC->>CACHE: Verifica cache
    alt Cache hit
        CACHE-->>SVC: Dados em cache
    else Cache miss
        SVC->>DB: SELECT query
        DB-->>SVC: Resultado
        SVC->>CACHE: SET (TTL: 5min)
    end
    SVC-->>API: Response DTO
    API-->>FE: 200 OK + JSON
    FE-->>User: Atualiza UI
```

### Fluxo Assíncrono

```mermaid
sequenceDiagram
    participant SVC as Service
    participant QUEUE as Message Queue
    participant WORKER as Worker
    participant EXT as Serviço Externo
    participant DB as Database

    SVC->>QUEUE: Publish event
    QUEUE-->>WORKER: Consume event
    WORKER->>EXT: Chamada externa
    alt Sucesso
        EXT-->>WORKER: 200 OK
        WORKER->>DB: Atualiza status
    else Falha
        EXT-->>WORKER: Erro
        WORKER->>QUEUE: Retry (backoff exponencial)
        Note over WORKER,QUEUE: Max 3 retries, depois DLQ
    end
```
"""

    def _data_model(self, ctx: TemplateContext) -> str:
        return """## Modelo de Dados

### Diagrama ER

```mermaid
erDiagram
    USER ||--o{ ORDER : "realiza"
    USER {
        uuid id PK
        string email UK
        string name
        string role
        timestamp created_at
        timestamp updated_at
    }
    ORDER ||--|{ ORDER_ITEM : "contém"
    ORDER {
        uuid id PK
        uuid user_id FK
        string status
        decimal total
        timestamp created_at
    }
    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        string product_name
        integer quantity
        decimal unit_price
    }
```

### Decisões de Modelagem
- **IDs**: UUID v4 para todas as entidades (evita sequence scanning)
- **Timestamps**: UTC always, com timezone
- **Soft delete**: `deleted_at` nullable (quando aplicável)
- **Audit trail**: `created_by`, `updated_by` para rastreabilidade
"""

    def _api_contracts(self, ctx: TemplateContext) -> str:
        return """## Contratos de API

### Endpoints

```yaml
# POST /api/v1/resource
request:
  headers:
    Authorization: Bearer <jwt>
    Content-Type: application/json
  body:
    field_a: string (required, max: 255)
    field_b: integer (optional, default: 0)

response:
  200:
    id: uuid
    field_a: string
    created_at: ISO8601
  400:
    error: "VALIDATION_ERROR"
    details: [{field: "field_a", message: "..."}]
  401:
    error: "UNAUTHORIZED"
  500:
    error: "INTERNAL_ERROR"
    correlation_id: uuid
```

### Padrões de API
- **Versionamento**: URL path (`/api/v1/`)
- **Paginação**: cursor-based (`?after=<cursor>&limit=20`)
- **Erros**: RFC 7807 Problem Details
- **Rate limiting**: 100 req/min por API key (header `X-RateLimit-*`)
"""

    def _deployment(self, ctx: TemplateContext) -> str:
        return """## Topologia de Deploy

```mermaid
graph TB
    subgraph "Cloud Provider"
        LB[Load Balancer<br/>nginx/ALB]

        subgraph "Cluster"
            N1[Node 1<br/>API + Service]
            N2[Node 2<br/>API + Service]
            N3[Node 3<br/>Worker]
        end

        subgraph "Data Layer"
            DB_PRIMARY[(DB Primary<br/>Write)]
            DB_REPLICA[(DB Replica<br/>Read)]
            REDIS[(Redis Cluster)]
        end

        subgraph "Observability"
            LOGS[Log Aggregator]
            METRICS[Metrics/APM]
            TRACES[Distributed Tracing]
        end
    end

    LB --> N1
    LB --> N2
    N1 --> DB_PRIMARY
    N2 --> DB_REPLICA
    N1 --> REDIS
    N1 --> LOGS
    N2 --> LOGS
    N3 --> LOGS
    DB_PRIMARY --> DB_REPLICA
```

### Ambientes
| Ambiente | Propósito | Infra |
|----------|-----------|-------|
| `dev` | Desenvolvimento local | Docker Compose |
| `staging` | Validação pré-prod | <!-- Cloud --> |
| `production` | Produção | <!-- Cloud HA --> |
"""

    def _security(self, ctx: TemplateContext) -> str:
        return """## Segurança

### Autenticação e Autorização
- **Método**: JWT (access_token + refresh_token)
- **Expiração**: access: 15min, refresh: 7d
- **RBAC**: roles definidas por entidade
- **Secrets**: gerenciados via <!-- Vault / AWS Secrets Manager / env -->

### Checklist OWASP
- [ ] Injection (SQL, NoSQL, Command)
- [ ] Broken Authentication
- [ ] Sensitive Data Exposure
- [ ] XXE (XML External Entities)
- [ ] Broken Access Control
- [ ] Security Misconfiguration
- [ ] XSS (Cross-Site Scripting)
- [ ] Insecure Deserialization
- [ ] Known Vulnerabilities (deps)
- [ ] Insufficient Logging
"""

    def _decisions(self, ctx: TemplateContext) -> str:
        existing = ""
        if ctx.memory and ctx.memory.decisions:
            items = []
            for d in ctx.memory.decisions:
                items.append(f"- **{d.title}** [{d.status}]: {d.decision}")
            existing = "\n".join(items)

        return f"""## Decisões Arquiteturais (ADRs)

{existing or "<!-- Decisões carregadas da memória do projeto -->"}

### ADR-001: <!-- Título da Decisão -->

- **Status**: proposed | accepted | deprecated | superseded
- **Contexto**: <!-- Qual problema motivou a decisão? -->
- **Decisão**: <!-- O que foi decidido? -->
- **Consequências**:
  - [+] <!-- Beneficio 1 -->
  - [+] <!-- Beneficio 2 -->
  - [!] <!-- Trade-off 1 -->
  - [!] <!-- Trade-off 2 -->

### ADR-002: <!-- Próxima decisão -->
"""

    def _constraints_section(self, ctx: TemplateContext) -> str:
        constraints_list = ""
        if ctx.memory and ctx.memory.constraints:
            constraints_list = "\n".join(f"- {c}" for c in ctx.memory.constraints)

        return f"""## Restrições e Limites

### Restrições do Projeto
{constraints_list or '<!-- Usar `krab memory set constraints "descrição"` para adicionar -->'}

### Limites Técnicos
- **Tamanho máximo de payload**: <!-- 10MB -->
- **Conexões simultâneas DB**: <!-- pool: 20 -->
- **Timeout de request**: <!-- 30s -->
- **Tamanho máximo de fila**: <!-- 10K mensagens -->
"""

    def _evolution(self, ctx: TemplateContext) -> str:
        return """## Evolução e Roadmap Técnico

### Fase 1 (MVP)
- [ ] <!-- Componente mínimo viável -->
- [ ] <!-- Integração principal -->

### Fase 2 (Scaling)
- [ ] <!-- Cache layer -->
- [ ] <!-- Async processing -->

### Fase 3 (Maturity)
- [ ] <!-- Observability completa -->
- [ ] <!-- Multi-region -->

### Débitos Técnicos Conhecidos
- <!-- Débito 1: impacto e plano de resolução -->
- <!-- Débito 2: impacto e plano de resolução -->
"""
