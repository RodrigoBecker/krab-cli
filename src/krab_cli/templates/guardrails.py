"""spec.guardrails — Project GuardRails spec template.

GuardRails define quality gates, validation rules, and automated checks
that every spec and implementation must pass. They act as project-wide
constraints that prevent regressions and maintain standards.

This spec is global — it influences the refining process and defines
the gates in workflows.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class GuardRailsTemplate(SpecTemplate):
    template_type = "guardrails"
    description = "Project guardrails — quality gates, validation rules, and automated checks"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# {ctx.name}",
            "",
            "> GuardRails sao gates de qualidade que toda spec e implementacao",
            "> devem passar. Eles previnem regressoes e mantem os padroes do projeto.",
            "> Este documento e global e define os gates dos workflows.",
            "",
            self._project_context_section(ctx),
            self._spec_gates(ctx),
            self._code_gates(ctx),
            self._security_gates(ctx),
            self._workflow_gates(ctx),
            self._agent_gates(ctx),
            self._monitoring_section(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _spec_gates(self, ctx: TemplateContext) -> str:
        return """## Gates de Spec (Pre-Implementacao)

> Estes gates devem passar ANTES de iniciar a implementacao.
> Use `krab analyze` para validar automaticamente.

### Gate 1: Completude Estrutural
- **Criterio**: Todas as secoes obrigatorias preenchidas (sem placeholders)
- **Validacao**: `krab analyze risk <spec>` — score < 40
- **Bloqueante**: Sim
- **Acao se falhar**: Rodar `krab spec refine <spec>` e preencher gaps

### Gate 2: Precisao Linguistica
- **Criterio**: Menos de 5 termos ambiguos por spec
- **Validacao**: `krab analyze ambiguity <spec>` — grade A ou B
- **Bloqueante**: Sim
- **Acao se falhar**: Substituir termos vagos por valores concretos

### Gate 3: Cenarios Gherkin
- **Criterio**: Minimo 3 cenarios (happy path, erro, edge case)
- **Validacao**: Contagem automatica no refining
- **Bloqueante**: Sim (para specs do tipo task)
- **Acao se falhar**: Adicionar cenarios faltantes

### Gate 4: Coerencia com Constituicao
- **Criterio**: Spec respeita principios e limites da constituicao
- **Validacao**: Review manual ou via agente
- **Bloqueante**: Sim
- **Acao se falhar**: Revisar spec contra constituicao

### Gate 5: Token Budget
- **Criterio**: Spec nao excede janela de contexto do agente
- **Validacao**: `krab analyze tokens <spec>` — < 8192 tokens
- **Bloqueante**: Nao (warning)
- **Acao se falhar**: `krab optimize run <spec>`
"""

    def _code_gates(self, ctx: TemplateContext) -> str:
        test_cmd = "uv run pytest"
        lint_cmd = "uv run ruff check src/ tests/"
        if ctx.memory and ctx.memory.tech_stack:
            stack = ctx.memory.tech_stack
            if "node" in str(stack).lower() or "javascript" in str(stack).lower():
                test_cmd = "npm test"
                lint_cmd = "npm run lint"

        return f"""## Gates de Codigo (Pos-Implementacao)

> Estes gates devem passar DEPOIS da implementacao, antes do merge.

### Gate 6: Testes Automatizados
- **Criterio**: Todos os cenarios Gherkin implementados como testes
- **Validacao**: `{test_cmd}`
- **Bloqueante**: Sim
- **Acao se falhar**: Implementar testes faltantes

### Gate 7: Lint e Type Check
- **Criterio**: Zero erros de lint e type check
- **Validacao**: `{lint_cmd}`
- **Bloqueante**: Sim
- **Acao se falhar**: Corrigir erros reportados

### Gate 8: Cobertura de Testes
- **Criterio**: Cobertura >= 80% nas areas modificadas
- **Validacao**: pytest --cov
- **Bloqueante**: Nao (warning se < 80%)
- **Acao se falhar**: Adicionar testes para areas descobertas

### Gate 9: Conformidade com Spec
- **Criterio**: Implementacao corresponde exatamente aos cenarios da spec
- **Validacao**: Review via agente (`krab workflow run review`)
- **Bloqueante**: Sim
- **Acao se falhar**: Ajustar implementacao ou atualizar spec
"""

    def _security_gates(self, ctx: TemplateContext) -> str:
        return """## Gates de Seguranca

### Gate 10: Dados Sensiveis
- **Criterio**: Nenhum segredo (API keys, passwords) no codigo ou specs
- **Validacao**: git-secrets / gitleaks
- **Bloqueante**: Sim (critico)
- **Acao se falhar**: Remover segredos, rotacionar credenciais

### Gate 11: Validacao de Input
- **Criterio**: Todo input externo e validado e sanitizado
- **Validacao**: Review de cenarios Gherkin de validacao
- **Bloqueante**: Sim
- **Acao se falhar**: Adicionar cenarios de input invalido na spec

### Gate 12: Autorizacao
- **Criterio**: Endpoints protegidos com autenticacao/autorizacao
- **Validacao**: Cenarios Gherkin de permissao
- **Bloqueante**: Sim
- **Acao se falhar**: Adicionar cenarios de autorizacao na spec
"""

    def _workflow_gates(self, ctx: TemplateContext) -> str:
        return """## Gates de Workflow (Pipeline)

> Estes gates sao automaticamente avaliados durante workflows.
> Configure-os nos arquivos YAML de workflow em `.sdd/workflows/`.

### Mapeamento Gate -> Workflow Step

| Gate | Workflow Step | Tipo | Condicao |
|------|-------------|------|----------|
| Completude | spec-plan | gate | `krab analyze risk {spec}` score < 40 |
| Precisao | spec-refining | gate | `krab analyze ambiguity {spec}` grade A/B |
| Cenarios | spec-task | gate | Minimo 3 cenarios Gherkin |
| Testes | spec-implementation | shell | `uv run pytest` exit code 0 |
| Lint | spec-implementation | shell | `uv run ruff check` exit code 0 |
| Review | spec-review | agent | Agente valida conformidade |

### Como Adicionar Gates Customizados

```yaml
# Em .sdd/workflows/custom.yaml
steps:
  - name: custom-gate
    type: gate
    condition: "file_exists:{root}/.sdd/specs/spec.constitution.*.md"
  - name: quality-check
    type: shell
    command: "krab analyze risk {spec}"
    on_failure: stop
```
"""

    def _agent_gates(self, ctx: TemplateContext) -> str:
        agent = ""
        if ctx.memory and ctx.memory.agent_preference:
            agent = ctx.memory.agent_preference

        return f"""## Gates para Agente IA

> Regras que o agente IA deve seguir em toda interacao.

### Antes de Implementar
- [ ] Ler a spec completa (incluindo cenarios Gherkin)
- [ ] Verificar se a constituicao foi consultada
- [ ] Confirmar que todos os gates de spec passaram
- [ ] Identificar dependencias com outras specs

### Durante a Implementacao
- [ ] Seguir convencoes de codigo definidas na constituicao
- [ ] Implementar testes para cada cenario Gherkin
- [ ] Nao modificar areas fora do escopo da spec
- [ ] Registrar decisoes tecnicas como comentarios

### Apos a Implementacao
- [ ] Rodar todos os testes
- [ ] Verificar lint e type check
- [ ] Reportar conformidade com a spec
- [ ] Sugerir atualizacoes para specs relacionadas

### Agente Configurado
{f'Agente atual: **{agent}**' if agent else '<!-- Definido durante `krab init` -->'}
"""

    def _monitoring_section(self, ctx: TemplateContext) -> str:
        return """## Monitoramento de GuardRails

### Dashboard de Qualidade

```bash
# Verificar todos os gates de uma spec
krab workflow run verify --spec <spec>

# Verificar conformidade do projeto
krab analyze batch .sdd/specs/ -a quality

# Status dos arquivos de agente
krab agent status
```

### Alertas
| Condicao | Severidade | Acao |
|----------|-----------|------|
| Risk score > 60 | Critico | Bloquear implementacao |
| Risk score 40-60 | Warning | Revisar spec |
| Ambiguidade grade C/D | Warning | Refinar spec |
| Cobertura < 60% | Critico | Adicionar testes |
| Cobertura 60-80% | Warning | Revisar cobertura |

### Evolucao dos GuardRails
> Atualize este documento quando:
> - Novos padroes de qualidade forem definidos
> - Gates existentes precisarem de ajuste
> - Novas ferramentas de validacao forem adotadas
"""
