"""spec.runbook — Project Runbook spec template.

The Runbook defines operational procedures for running, deploying,
monitoring, and maintaining the project. It is the ops-focused spec
that ensures the project can be reliably operated.

This spec is global — it provides operational context for all
implementations and influences the review process.
"""

from __future__ import annotations

from krab_cli.templates import SpecTemplate, TemplateContext, register_template


@register_template
class RunbookTemplate(SpecTemplate):
    template_type = "runbook"
    description = "Project runbook — operational procedures, deploy, monitoring, maintenance"

    def render(self, ctx: TemplateContext) -> str:
        sections = [
            self._header(ctx),
            "",
            f"# {ctx.name}",
            "",
            "> Procedimentos operacionais do projeto. Define como rodar, deployar,",
            "> monitorar e manter o sistema em producao.",
            "> Este documento e global e fornece contexto operacional para todas as specs.",
            "",
            self._project_context_section(ctx),
            self._quickstart_section(ctx),
            self._environment_section(ctx),
            self._commands_section(ctx),
            self._deploy_section(ctx),
            self._monitoring_section(ctx),
            self._troubleshooting_section(ctx),
            self._maintenance_section(ctx),
        ]
        return "\n".join(s for s in sections if s)

    def _quickstart_section(self, ctx: TemplateContext) -> str:
        tech_stack = ""
        if ctx.memory and ctx.memory.tech_stack:
            items = []
            for k, v in ctx.memory.tech_stack.items():
                items.append(f"- **{k}**: {v}")
            tech_stack = "\n".join(items)

        return f"""## Quickstart

### Pre-requisitos
{tech_stack or '<!-- Listar dependencias do sistema: runtime, database, etc. -->'}

### Setup Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd <project>

# 2. Instalar dependencias
<!-- Comando de instalacao -->

# 3. Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com valores locais

# 4. Rodar o projeto
<!-- Comando para iniciar -->

# 5. Verificar que esta rodando
<!-- Comando de health check -->
```

### Verificacao Rapida

```bash
# Rodar testes
<!-- Comando de testes -->

# Verificar lint
<!-- Comando de lint -->

# Health check
curl -s http://localhost:<PORT>/health | jq .
```
"""

    def _environment_section(self, ctx: TemplateContext) -> str:
        return """## Ambientes

### Variaveis de Ambiente

| Variavel | Descricao | Obrigatoria | Exemplo |
|----------|-----------|-------------|---------|
| `DATABASE_URL` | <!-- Conexao do banco --> | Sim | `postgresql://...` |
| `API_KEY` | <!-- Chave de API --> | Sim | `sk-...` |
| `LOG_LEVEL` | <!-- Nivel de log --> | Nao | `INFO` |
| `PORT` | <!-- Porta do servico --> | Nao | `8000` |

### Ambientes Disponiveis

| Ambiente | URL | Proposito | Deploy |
|----------|-----|-----------|--------|
| Local | `localhost:<PORT>` | Desenvolvimento | Manual |
| Staging | <!-- URL --> | Validacao | <!-- CI/CD --> |
| Production | <!-- URL --> | Producao | <!-- CI/CD --> |

### Configuracao por Ambiente

```bash
# Local
export ENV=local
export DEBUG=true

# Staging
export ENV=staging
export DEBUG=false

# Production
export ENV=production
export DEBUG=false
export LOG_LEVEL=WARNING
```
"""

    def _commands_section(self, ctx: TemplateContext) -> str:
        commands = ""
        if ctx.memory and ctx.memory.tech_stack:
            stack = ctx.memory.tech_stack
            if any("python" in str(v).lower() for v in stack.values()):
                commands = """| `uv run pytest` | Rodar testes | Qualquer | Sempre |
| `uv run ruff check src/ tests/` | Verificar lint | Qualquer | Antes de commit |
| `uv run ruff format src/ tests/` | Formatar codigo | Qualquer | Antes de commit |"""
            elif any("node" in str(v).lower() or "javascript" in str(v).lower() for v in stack.values()):
                commands = """| `npm test` | Rodar testes | Qualquer | Sempre |
| `npm run lint` | Verificar lint | Qualquer | Antes de commit |
| `npm run build` | Build | Qualquer | Antes de deploy |"""

        return f"""## Comandos Operacionais

### Comandos do Projeto

| Comando | Descricao | Ambiente | Quando Usar |
|---------|-----------|----------|-------------|
{commands or '| `<!-- comando -->` | <!-- descricao --> | <!-- ambiente --> | <!-- quando --> |'}

### Comandos SDD (Krab)

| Comando | Descricao | Quando Usar |
|---------|-----------|-------------|
| `krab init` | Inicializar projeto SDD | Uma vez |
| `krab spec new task -n "feature"` | Criar spec de feature | Antes de implementar |
| `krab spec refine <spec>` | Refinar spec | Apos criar spec |
| `krab spec clarify <spec>` | Enriquecer spec com Q&A | Para melhorar precisao |
| `krab workflow run sdd-lifecycle -s "feature"` | Ciclo completo SDD | Para features completas |
| `krab analyze risk <spec>` | Avaliar risco de hallucination | Antes de enviar ao agente |
| `krab agent sync all` | Sincronizar instrucoes do agente | Apos mudancas em specs |
"""

    def _deploy_section(self, ctx: TemplateContext) -> str:
        return """## Deploy

### Pipeline de Deploy

```mermaid
graph LR
    A[Commit] --> B[CI: Tests]
    B --> C[CI: Lint]
    C --> D[CI: Build]
    D --> E{Branch?}
    E -->|main| F[Deploy Staging]
    E -->|release| G[Deploy Production]
    F --> H[Smoke Tests]
    G --> I[Health Check]
```

### Procedimento de Deploy

#### Staging
```bash
# 1. Merge para main
git checkout main && git pull

# 2. Deploy automatico via CI/CD
# ou manual:
<!-- Comando de deploy para staging -->

# 3. Validar
<!-- Comando de smoke test -->
```

#### Production
```bash
# 1. Criar release
git tag -a v<VERSION> -m "Release v<VERSION>"
git push origin v<VERSION>

# 2. Deploy automatico via CI/CD
# ou manual:
<!-- Comando de deploy para producao -->

# 3. Validar
<!-- Comando de health check em producao -->
```

### Rollback

```bash
# Em caso de problema em producao:
# 1. Reverter para versao anterior
<!-- Comando de rollback -->

# 2. Verificar recuperacao
<!-- Comando de health check -->

# 3. Investigar causa raiz
<!-- Procedimento de investigacao -->
```
"""

    def _monitoring_section(self, ctx: TemplateContext) -> str:
        return """## Monitoramento

### Metricas Chave

| Metrica | Alvo | Alerta | Critico |
|---------|------|--------|---------|
| Latencia P95 | < 200ms | > 500ms | > 1s |
| Error Rate | < 0.1% | > 1% | > 5% |
| Uptime | 99.9% | < 99.5% | < 99% |
| CPU Usage | < 70% | > 80% | > 95% |
| Memory Usage | < 70% | > 80% | > 95% |

### Logs

```bash
# Ver logs em tempo real
<!-- Comando para ver logs -->

# Filtrar erros
<!-- Comando para filtrar erros -->

# Buscar por correlation_id
<!-- Comando para buscar por ID -->
```

### Alertas Configurados

| Alerta | Condicao | Acao | Responsavel |
|--------|----------|------|-------------|
| High Error Rate | Error rate > 1% por 5min | <!-- Acao --> | <!-- Equipe --> |
| High Latency | P95 > 500ms por 5min | <!-- Acao --> | <!-- Equipe --> |
| Disk Full | Disco > 90% | <!-- Acao --> | <!-- Equipe --> |

### Dashboards
<!-- Links para dashboards de monitoramento -->
- [ ] Grafana: <!-- URL -->
- [ ] Datadog: <!-- URL -->
- [ ] CloudWatch: <!-- URL -->
"""

    def _troubleshooting_section(self, ctx: TemplateContext) -> str:
        return """## Troubleshooting

### Problemas Comuns

#### Aplicacao nao inicia
```bash
# 1. Verificar variaveis de ambiente
env | grep -E "(DATABASE|API_KEY|PORT)"

# 2. Verificar conexao com banco
<!-- Comando para testar banco -->

# 3. Verificar portas em uso
lsof -i :<PORT>
```

#### Testes falhando
```bash
# 1. Rodar teste especifico para isolar
<!-- Comando para rodar teste especifico -->

# 2. Verificar estado do banco de testes
<!-- Comando para resetar banco de teste -->

# 3. Verificar dependencias
<!-- Comando para verificar deps -->
```

#### Deploy falhou
```bash
# 1. Verificar logs do CI/CD
<!-- Como ver logs do CI -->

# 2. Verificar build local
<!-- Comando de build local -->

# 3. Rollback se necessario
<!-- Comando de rollback -->
```

### Escalonamento
| Nivel | Quem | Quando | Como |
|-------|------|--------|------|
| L1 | <!-- Dev on-call --> | Alertas automaticos | <!-- Procedimento --> |
| L2 | <!-- Tech Lead --> | Problema persiste > 30min | <!-- Procedimento --> |
| L3 | <!-- CTO/Arquiteto --> | Incidente critico | <!-- Procedimento --> |
"""

    def _maintenance_section(self, ctx: TemplateContext) -> str:
        return """## Manutencao

### Tarefas Periodicas

| Tarefa | Frequencia | Comando | Responsavel |
|--------|-----------|---------|-------------|
| Atualizar dependencias | Semanal | <!-- comando --> | <!-- equipe --> |
| Limpar logs antigos | Mensal | <!-- comando --> | <!-- equipe --> |
| Backup de dados | Diario | <!-- comando --> | Automatico |
| Rotacionar credenciais | Trimestral | <!-- procedimento --> | <!-- equipe --> |
| Review de specs | Sprint | `krab analyze batch .sdd/specs/ -a quality` | <!-- equipe --> |

### Atualizacao de Dependencias

```bash
# Verificar atualizacoes disponiveis
<!-- Comando para verificar updates -->

# Atualizar e testar
<!-- Comando para atualizar -->
<!-- Comando para testar apos update -->
```

### Evolucao do Runbook
> Atualize este documento quando:
> - Novos procedimentos operacionais forem definidos
> - Infraestrutura mudar
> - Novos alertas forem configurados
> - Problemas recorrentes forem identificados
"""
