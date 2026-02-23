"""spec.task — Feature specification template with Gherkin BDD.

Generates task/feature specs using Given/When/Then format for clear,
testable requirements that AI agents can implement directly.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class TaskTemplate(SpecTemplate):
    template_type = "task"
    description = "Feature/task spec with Gherkin BDD scenarios (Given/When/Then)"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# {ctx.name}",
            "",
            f"> {ctx.description or 'Descrição da feature/task.'}",
            "",
            self._project_context_section(ctx),
            self._overview_section(ctx),
            self._acceptance_criteria(ctx),
            self._scenarios_section(ctx),
            self._edge_cases_section(ctx),
            self._technical_notes(ctx),
            self._dependencies_section(ctx),
            self._definition_of_done(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _overview_section(self, ctx: TemplateContext) -> str:
        return """## Visão Geral

### Objetivo
<!-- Qual problema esta feature resolve? -->

### Usuário-alvo
<!-- Quem se beneficia desta feature? -->

### Escopo
- **Inclui**: <!-- O que faz parte desta entrega -->
- **Não inclui**: <!-- O que está fora do escopo -->

### Prioridade
- [ ] P0 — Crítico (bloqueia release)
- [ ] P1 — Alto (feature principal)
- [ ] P2 — Médio (melhoria importante)
- [ ] P3 — Baixo (nice-to-have)
"""

    def _acceptance_criteria(self, ctx: TemplateContext) -> str:
        return """## Critérios de Aceitação

> Condições que **devem** ser verdadeiras para a feature ser considerada completa.

- [ ] <!-- Critério 1: condição mensurável -->
- [ ] <!-- Critério 2: condição mensurável -->
- [ ] <!-- Critério 3: condição mensurável -->
"""

    def _scenarios_section(self, ctx: TemplateContext) -> str:
        feature_name = ctx.name or "Nome da Feature"
        return f"""## Cenários BDD (Gherkin)

### Feature: {feature_name}

```gherkin
Feature: {feature_name}
  Como <tipo de usuário>
  Eu quero <ação desejada>
  Para que <benefício esperado>

  Scenario: Fluxo principal (happy path)
    Given <pré-condição estabelecida>
    And <outra pré-condição>
    When <ação executada pelo usuário>
    And <ação complementar>
    Then <resultado esperado>
    And <outro resultado verificável>

  Scenario: Validação de entrada inválida
    Given <pré-condição>
    When <ação com dados inválidos>
    Then <mensagem de erro específica>
    And <estado do sistema preservado>

  Scenario: Usuário sem permissão
    Given <usuário sem role necessária>
    When <tentativa de acesso>
    Then <resposta 403 Forbidden>
    And <log de tentativa registrado>

  Scenario Outline: Múltiplas variações
    Given <pré-condição>
    When o usuário envia <input>
    Then o sistema retorna <output>

    Examples:
      | input           | output          |
      | valor_válido_1  | resultado_1     |
      | valor_válido_2  | resultado_2     |
      | valor_inválido  | erro_esperado   |
```
"""

    def _edge_cases_section(self, ctx: TemplateContext) -> str:
        return """## Casos de Borda

```gherkin
  Scenario: Timeout na integração externa
    Given o serviço externo está lento (> 5s)
    When a requisição é feita
    Then o sistema retorna timeout após <SLA>ms
    And uma mensagem amigável é exibida ao usuário
    And o erro é registrado com correlation_id

  Scenario: Dados concorrentes
    Given dois usuários editam o mesmo recurso
    When ambos salvam simultaneamente
    Then o sistema aplica <estratégia: optimistic locking | last-write-wins>
    And o usuário perdedor é notificado

  Scenario: Volume extremo
    Given o sistema recebe <N> requisições/segundo
    When o rate limit é atingido
    Then retorna 429 Too Many Requests
    And o header Retry-After indica tempo de espera
```
"""

    def _technical_notes(self, ctx: TemplateContext) -> str:
        stack_hint = ""
        if ctx.memory and ctx.memory.tech_stack:
            items = [f"- **{k}**: {v}" for k, v in ctx.memory.tech_stack.items()]
            stack_hint = "\n".join(items)

        return f"""## Notas Técnicas

### Stack Utilizada
{stack_hint or '<!-- Definir stack ou usar `krab memory set tech_stack.backend "Node.js"` -->'}

### API Endpoints

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `POST` | `/api/v1/...` | <!-- ação --> | Bearer |
| `GET` | `/api/v1/...` | <!-- consulta --> | Bearer |
| `PUT` | `/api/v1/...` | <!-- atualização --> | Bearer |
| `DELETE` | `/api/v1/...` | <!-- remoção --> | Bearer |

### Modelo de Dados

```
<!-- Entidade principal e campos -->
Entity {{
  id: UUID (PK)
  ...
  created_at: timestamp
  updated_at: timestamp
}}
```

### Regras de Negócio
1. <!-- Regra clara e mensurável -->
2. <!-- Regra clara e mensurável -->
"""

    def _dependencies_section(self, ctx: TemplateContext) -> str:
        return """## Dependências

### Specs Relacionadas
<!-- Links para specs que esta feature depende -->
- [ ] `spec.architecture.*.md` — <!-- qual aspecto -->
- [ ] `spec.task.*.md` — <!-- qual feature -->

### Serviços Externos
<!-- APIs, bancos, filas que esta feature consome -->

### Bloqueios
<!-- O que precisa estar pronto antes desta task começar -->
"""

    def _definition_of_done(self, ctx: TemplateContext) -> str:
        return """## Definition of Done

- [ ] Todos os cenários Gherkin passando (testes automatizados)
- [ ] Critérios de aceitação validados
- [ ] Code review aprovado
- [ ] Documentação da API atualizada
- [ ] Sem warnings de lint/type-check
- [ ] Testes de integração cobrindo happy path + edge cases
- [ ] Deploy em ambiente de staging validado
- [ ] Métricas de observabilidade configuradas (logs, traces, metrics)
"""
