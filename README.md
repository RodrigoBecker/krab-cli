# Krab CLI

```
██╗  ██╗██████╗  █████╗ ██████╗      ██████╗██╗     ██╗
██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗    ██╔════╝██║     ██║
█████╔╝ ██████╔╝███████║██████╔╝    ██║     ██║     ██║
██╔═██╗ ██╔══██╗██╔══██║██╔══██╗    ██║     ██║     ██║
██║  ██╗██║  ██║██║  ██║██████╔╝    ╚██████╗███████╗██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝      ╚═════╝╚══════╝╚═╝
```

Toolkit CLI para **Spec-Driven Development (SDD)** — otimize, analise, converta e gere especificacoes para agentes de IA com foco em economia de tokens e qualidade de contexto. Inclui um **workflow engine** que encadeia operacoes e delega execucao para agentes reais (Claude Code, Codex, Copilot).

## Sumario

- [Instalacao](#instalacao)
- [Quick Start](#quick-start)
- [Comandos](#comandos)
  - [optimize](#krab-optimize) — Otimizacao de specs
  - [convert](#krab-convert) — Conversao de formatos
  - [analyze](#krab-analyze) — Analise de qualidade
  - [search](#krab-search) — Busca e indexacao
  - [diff](#krab-diff) — Delta entre versoes
  - [spec](#krab-spec) — Geracao de specs via templates
  - [memory](#krab-memory) — Memoria do projeto
  - [agent](#krab-agent) — Instrucoes para agentes IA
  - [workflow](#krab-workflow) — Pipelines multi-step com agentes
  - [cache](#krab-cache) — Cache de resultados
- [Slash Commands (Geracao Nativa)](#slash-commands-geracao-nativa)
- [Exemplos End-to-End](#exemplos-end-to-end)
- [Performance](#performance)
- [Algoritmos](#algoritmos-25)
- [Arquitetura](#arquitetura)
- [Desenvolvimento](#desenvolvimento)
- [Stack](#stack)
- [Licenca](#licenca)

---

## Instalacao

### Via pipx (recomendado)

```bash
pipx install -e .
```

### Via pip

```bash
pip install -e .
```

### Desenvolvimento

```bash
git clone <repo>
cd krab-cli
uv sync
```

Apos a instalacao, o comando `krab` fica disponivel globalmente:

```bash
krab --version
```

---

## Quick Start

```bash
# 1. Inicializar memoria do projeto
krab memory init -n "meu-projeto" -d "API REST para e-commerce"
krab memory set tech_stack.backend "Python/FastAPI"
krab memory set architecture_style "hexagonal"

# 2. Gerar uma spec de tarefa
krab spec new task -n "Autenticacao OAuth2" -d "Login com Google e GitHub"

# 3. Analisar qualidade da spec
krab analyze risk spec.task.autenticacao-oauth2.md
krab analyze ambiguity spec.task.autenticacao-oauth2.md

# 4. Otimizar spec para economia de tokens
krab optimize run spec.task.autenticacao-oauth2.md -o spec-otimizada.md

# 5. Gerar instrucoes para agentes IA
krab agent sync

# 6. Executar workflow completo com um agente
krab workflow run implement --spec spec.task.autenticacao-oauth2.md --agent claude

# 7. Ou rodar o ciclo completo (cria spec -> implementa -> review)
krab workflow run full-cycle --spec autenticacao-oauth2 --agent claude --dry-run
```

---

## Comandos

### `krab optimize`

Otimiza specs para eficiencia de tokens via compressao Huffman e deduplicacao fuzzy.

#### `krab optimize run`

Pipeline completo de otimizacao.

```bash
krab optimize run spec.md                           # Otimiza com defaults
krab optimize run spec.md -o optimized.md           # Salva em arquivo
krab optimize run spec.md --no-compress             # Pula compressao
krab optimize run spec.md --no-dedup                # Pula deduplicacao
krab optimize run spec.md --min-freq 2              # Frequencia minima para aliases
krab optimize run spec.md --max-aliases 100         # Maximo de aliases
krab optimize run spec.md --threshold 85            # Limiar de similaridade para dedup
krab optimize run spec.md --context-window 16384    # Janela de contexto alvo
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `-o, --output` | stdout | Arquivo de saida |
| `--no-compress` | false | Pular compressao Huffman |
| `--no-dedup` | false | Pular deduplicacao |
| `--min-freq` | 3 | Frequencia minima para gerar aliases |
| `--max-aliases` | 50 | Numero maximo de aliases |
| `--threshold` | 90.0 | Limiar de similaridade (0-100) |
| `--context-window` | 8192 | Tamanho da janela de contexto |

#### `krab optimize aliases`

Visualiza o dicionario de aliases que seria gerado sem aplicar.

```bash
krab optimize aliases spec.md
krab optimize aliases spec.md --min-freq 2 --max-aliases 100
```

#### `krab optimize dedup`

Encontra secoes duplicadas dentro de uma spec.

```bash
krab optimize dedup spec.md
krab optimize dedup spec.md --threshold 80 --method weighted
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--threshold` | 80.0 | Limiar de similaridade |
| `--method` | weighted | Metodo: `weighted`, `ratio`, `token_set` |

---

### `krab convert`

Converte specs entre Markdown, JSON e YAML.

#### `krab convert md2json`

```bash
krab convert md2json spec.md                # Imprime JSON no stdout
krab convert md2json spec.md -o spec.json   # Salva em arquivo
krab convert md2json spec.md --indent 4     # Indentacao customizada
```

#### `krab convert json2md`

```bash
krab convert json2md spec.json -o spec.md
```

#### `krab convert md2yaml`

```bash
krab convert md2yaml spec.md -o spec.yaml
```

#### `krab convert yaml2md`

```bash
krab convert yaml2md spec.yaml -o spec.md
```

#### `krab convert auto`

Auto-detecta o formato de entrada e converte para o formato alvo.

```bash
krab convert auto spec.md --to json
krab convert auto spec.json --to yaml
krab convert auto spec.yaml --to md
```

---

### `krab analyze`

Analise completa de qualidade, tokens, similaridade e risco de alucinacao.

Os comandos `tokens`, `quality`, `entropy`, `readability` e `freq` possuem **cache automatico** — execucoes repetidas sobre o mesmo arquivo retornam instantaneamente. Use `--no-cache` para forcar recomputacao.

#### `krab analyze tokens`

Conta tokens e analisa eficiencia.

```bash
krab analyze tokens spec.md
krab analyze tokens spec.md --encoding o200k_base   # Encoding do GPT-4o
krab analyze tokens spec.md --no-cache              # Ignora cache
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--encoding` | cl100k_base | Encoding tiktoken (`cl100k_base`, `o200k_base`) |
| `--no-cache` | false | Ignora cache, forca recomputacao |

#### `krab analyze quality`

Densidade informacional e utilizacao da janela de contexto.

```bash
krab analyze quality spec.md
krab analyze quality spec.md --context-window 16384
krab analyze quality spec.md --no-cache
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--context-window` | 8192 | Tamanho da janela de contexto |
| `--no-cache` | false | Ignora cache |

#### `krab analyze compare`

Compara duas specs por similaridade (Jaccard, Cosine, N-gram, TF-IDF).

```bash
krab analyze compare spec_v1.md spec_v2.md
```

#### `krab analyze freq`

Frequencia de termos — identifica candidatos a compressao.

```bash
krab analyze freq spec.md
krab analyze freq spec.md --min-freq 3 --top 50
krab analyze freq spec.md --no-cache
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--min-freq` | 2 | Frequencia minima |
| `--top` | 30 | Quantidade de termos |
| `--no-cache` | false | Ignora cache |

#### `krab analyze entropy`

Entropia de Shannon, previsibilidade Markov e perplexidade estimada.

```bash
krab analyze entropy spec.md
krab analyze entropy spec.md --no-cache
```

Metricas retornadas:
- **Shannon Entropy** — conteudo informacional real (bits/token)
- **Markov Predictability** — detecta boilerplate e texto repetitivo
- **Perplexity** — quao "surpreendente" o texto e para um modelo

#### `krab analyze readability`

Scores de legibilidade — complexidade alta aumenta risco de alucinacao.

```bash
krab analyze readability spec.md
krab analyze readability spec.md --no-cache
```

Metricas retornadas:
- **Flesch-Kincaid Grade** — nivel escolar necessario
- **Flesch Reading Ease** — facilidade de leitura (0-100)
- **Gunning Fog Index** — anos de educacao necessarios
- **Coleman-Liau Index** — baseado em caracteres (bom para codigo)
- **ARI** — Automated Readability Index

#### `krab analyze ambiguity`

Detecta termos vagos que aumentam risco de alucinacao.

```bash
krab analyze ambiguity spec.md
krab analyze ambiguity spec.md --top 30
```

Detecta termos como: `etc`, `TBD`, `various`, `approximately`, `some`, `usually`, `might`, `possibly`.

#### `krab analyze substrings`

Encontra frases repetidas que desperdicam tokens.

```bash
krab analyze substrings spec.md
krab analyze substrings spec.md --min-words 3 --top 30
```

#### `krab analyze risk`

Score combinado de risco de alucinacao do agente.

```bash
krab analyze risk spec.md
krab analyze risk spec.md --context-window 16384
```

Combina: ambiguidade, legibilidade, entropia e utilizacao de contexto em um score unico.

#### `krab analyze chunking`

Compara estrategias de split para contexto otimo.

```bash
krab analyze chunking spec.md
```

Estrategias comparadas: `heading`, `paragraph`, `semantic`, `fixed-size`.

#### `krab analyze keywords`

Extrai termos-chave via RAKE e TextRank.

```bash
krab analyze keywords spec.md
krab analyze keywords spec.md --top 30
```

#### `krab analyze batch`

Executa analise em lote sobre todos os arquivos de um diretorio. Produz uma tabela-resumo com uma linha por arquivo. Integrado com cache — execucoes repetidas sobre arquivos inalterados sao instantaneas.

```bash
krab analyze batch ./specs/                              # Tokens (default)
krab analyze batch ./specs/ -a quality                   # Qualidade
krab analyze batch ./specs/ -a entropy                   # Entropia
krab analyze batch ./specs/ -a readability               # Legibilidade
krab analyze batch ./specs/ -p "spec.*.md"               # Glob customizado
krab analyze batch ./specs/ -a tokens --no-cache         # Sem cache
krab analyze batch ./specs/ --context-window 16384       # Janela custom
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `-a, --analysis` | tokens | Tipo: `tokens`, `quality`, `entropy`, `readability` |
| `-p, --pattern` | `*.md` | Glob pattern para filtrar arquivos |
| `--context-window` | 8192 | Janela de contexto (para quality) |
| `--encoding` | cl100k_base | Encoding tiktoken (para tokens) |
| `--no-cache` | false | Ignora cache |

---

### `krab search`

Busca, indexacao e otimizacao de budget para corpus de specs.

#### `krab search bm25`

Busca ranqueada por relevancia usando BM25 (superior ao TF-IDF).

```bash
krab search bm25 ./specs/ -q "authentication OAuth2"
krab search bm25 ./specs/ -q "database migration" --top 5
```

#### `krab search duplicates`

Detecta specs near-duplicates no corpus usando MinHash + LSH (escalavel, O(n)).

```bash
krab search duplicates ./specs/
krab search duplicates ./specs/ --threshold 0.7
```

#### `krab search budget`

Seleciona as melhores specs para carregar dentro de um budget de tokens (0/1 Knapsack).

```bash
krab search budget ./specs/
krab search budget ./specs/ --budget 16384 --strategy greedy
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--budget` | 8192 | Budget de tokens |
| `--strategy` | knapsack | `knapsack` (otimo) ou `greedy` (rapido) |

---

### `krab diff`

Delta encoding entre versoes de specs.

#### `krab diff versions`

Diff completo entre duas versoes com calculo de savings.

```bash
krab diff versions v1.md v2.md
```

#### `krab diff sections`

Diff por secao — mostra o que mudou em cada heading.

```bash
krab diff sections v1.md v2.md
```

---

### `krab spec`

Geracao de specs via templates SDD com suporte a memoria do projeto.

#### `krab spec new`

Gera uma nova spec a partir de um template.

```bash
krab spec new task -n "Login OAuth2" -d "Autenticacao via Google"
krab spec new architecture -n "API Gateway" -o spec.architecture.api-gateway.md
krab spec new plan -n "MVP Sprint 1"
krab spec new skill -n "FastAPI Backend"
krab spec new refining -n "Revisao de Specs"
```

| Template | Descricao |
|----------|-----------|
| `task` | Spec de tarefa/feature com cenarios Gherkin (Given/When/Then) |
| `architecture` | Spec de arquitetura com diagramas C4, ADRs e topologia |
| `plan` | Plano de implementacao com fases, Gantt e analise de risco |
| `skill` | Definicao de skills/capacidades tecnicas do projeto |
| `refining` | Refinamento Tree-of-Thought com analise multi-dimensional |

| Opcao | Descricao |
|-------|-----------|
| `-n, --name` | Nome da spec |
| `-d, --desc` | Descricao |
| `-o, --output` | Arquivo de saida |

#### `krab spec refine`

Analisa uma spec existente com Tree-of-Thought e gera plano de refinamento.

```bash
krab spec refine spec.task.login.md
krab spec refine spec.task.login.md -o refinamento.md
```

Analisa 5 dimensoes:
1. **Completude Estrutural** — secoes faltando, placeholders
2. **Precisao** — termos vagos, ambiguidade
3. **Coerencia** — contradicoes, inconsistencias
4. **Agent-Readiness** — clareza para agentes IA
5. **Testabilidade** — criterios de aceitacao verificaveis

#### `krab spec list`

Lista todos os templates disponiveis.

```bash
krab spec list
```

---

### `krab memory`

Gerencia a memoria persistente do projeto em `.sdd/`. Armazena stack, convencoes, termos de dominio e skills que sao usados automaticamente na geracao de specs e instrucoes para agentes.

#### `krab memory init`

Inicializa o diretorio `.sdd/` com a memoria do projeto.

```bash
krab memory init
krab memory init -n "meu-projeto" -d "Descricao do projeto"
```

#### `krab memory show`

Exibe a memoria atual do projeto.

```bash
krab memory show
```

#### `krab memory set`

Define campos na memoria. Suporta dot notation para dicts aninhados.

```bash
# Campos simples
krab memory set project_name "Meu Projeto"
krab memory set description "API REST para e-commerce"
krab memory set architecture_style "hexagonal"

# Tech stack (dot notation)
krab memory set tech_stack.backend "Python/FastAPI"
krab memory set tech_stack.frontend "React/TypeScript"
krab memory set tech_stack.database "PostgreSQL"
krab memory set tech_stack.cache "Redis"

# Convencoes
krab memory set conventions.commits "conventional commits"
krab memory set conventions.branches "gitflow"
krab memory set conventions.naming "snake_case para Python, camelCase para JS"

# Termos de dominio
krab memory set domain_terms.tenant "Organizacao cliente no sistema multi-tenant"
krab memory set domain_terms.SKU "Stock Keeping Unit - identificador unico do produto"

# Listas (append automatico)
krab memory set constraints "Sem dependencias externas em runtime"
krab memory set integrations "Stripe para pagamentos"

# Contexto do time
krab memory set team_context.size "5 devs"
krab memory set team_context.methodology "Scrum"
```

#### `krab memory add-skill`

Registra uma skill/capacidade tecnica do projeto.

```bash
krab memory add-skill Python -c language -v "3.11" -d "Backend principal"
krab memory add-skill FastAPI -c framework -v "0.100" -t "web,api,async"
krab memory add-skill Docker -c infra -d "Containerizacao"
krab memory add-skill "Repository Pattern" -c pattern -d "Acesso a dados"
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `-c, --cat` | tool | Categoria: `language`, `framework`, `tool`, `pattern`, `infra`, `service` |
| `-v, --ver` | | Versao |
| `-d, --desc` | | Descricao |
| `-t, --tags` | | Tags separadas por virgula |

#### `krab memory remove-skill`

Remove uma skill do projeto.

```bash
krab memory remove-skill Docker
```

#### `krab memory skills`

Lista todas as skills registradas.

```bash
krab memory skills
```

#### `krab memory history`

Exibe historico de geracao de specs.

```bash
krab memory history
krab memory history --top 10
```

---

### `krab agent`

Gera arquivos de instrucao para agentes de IA a partir da memoria e specs do projeto.

#### Agentes suportados

| Agente | Arquivo gerado | Formato |
|--------|---------------|---------|
| **Claude Code** | `CLAUDE.md` | Conciso, progressive disclosure |
| **GitHub Copilot** | `.github/copilot-instructions.md` + `.github/instructions/krab-specs.instructions.md` | Statements curtos, contextuais |
| **OpenAI Codex** | `AGENTS.md` + `.agents/skills/krab-workflow/SKILL.md` | Hierarquico, com skills |

#### `krab agent sync`

Gera arquivos de instrucao para todos os agentes (ou um especifico). Alem dos arquivos de instrucao, tambem gera automaticamente os slash commands nativos (use `--no-commands` para pular).

```bash
krab agent sync              # Todos os agentes + slash commands
krab agent sync claude       # Apenas Claude Code + commands
krab agent sync copilot      # Apenas GitHub Copilot + commands
krab agent sync codex        # Apenas OpenAI Codex
krab agent sync --no-commands  # Apenas instrucoes, sem gerar slash commands
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `--no-commands` | false | Pula geracao de slash commands nativos |

#### `krab agent preview`

Visualiza o conteudo que seria gerado sem escrever arquivos.

```bash
krab agent preview claude
krab agent preview copilot
krab agent preview codex
```

#### `krab agent status`

Verifica quais arquivos de instrucao existem no projeto.

```bash
krab agent status
```

#### `krab agent diff`

Mostra o que mudaria se `sync` fosse executado (diff contra arquivos existentes).

```bash
krab agent diff claude
krab agent diff copilot
```

---

### `krab workflow`

Pipelines multi-step que encadeiam operacoes de spec, analise, otimizacao e delegacao para agentes de IA reais. Workflows podem ser built-in ou customizados via YAML.

#### Workflows built-in

| Workflow | Steps | Descricao |
|----------|-------|-----------|
| `spec-create` | 4 | Cria spec -> refine -> analyze risk -> sync agents |
| `implement` | 5 | Gate -> risk check -> sync -> delega ao agente -> testa |
| `review` | 3 | Gate -> ambiguity check -> agente revisa codigo vs spec |
| `full-cycle` | 8 | Cria -> refine -> risk -> optimize -> sync -> implementa -> testa -> review |
| `verify` | 6 | Risk + ambiguity + readability + entropy + refine |
| `agent-init` | 3 | Checa memory -> sync todos -> status |

#### Agentes suportados pelo executor

| Agente | Comando executado | Pre-requisito |
|--------|-------------------|---------------|
| Claude Code | `claude -p "<prompt com spec + contexto>"` | `npm i -g @anthropic-ai/claude-code` |
| Codex | `codex exec "<prompt>"` | `npm i -g codex` |
| Copilot | `gh issue create --body "<prompt>" --label copilot` | `gh` CLI + auth |

O prompt enviado ao agente inclui automaticamente: conteudo da spec, projeto (do `.sdd/memory.json`), stack, constraints e instrucoes de implementacao.

#### `krab workflow list`

Lista todos os workflows disponiveis (built-in + custom).

```bash
krab workflow list
```

#### `krab workflow show`

Mostra os passos de um workflow especifico.

```bash
krab workflow show implement
krab workflow show full-cycle
```

#### `krab workflow run`

Executa um pipeline de workflow.

```bash
# Implementar uma feature com Claude Code
krab workflow run implement --spec spec.task.auth.md --agent claude

# Mesma feature usando Codex
krab workflow run implement --spec spec.task.auth.md --agent codex

# Ciclo completo (cria spec -> implementa -> review)
krab workflow run full-cycle --spec auth --agent claude

# Dry-run: mostra o que faria sem executar
krab workflow run implement --spec spec.task.auth.md --dry-run

# Apenas verificar qualidade da spec
krab workflow run verify --spec spec.task.auth.md
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `-s, --spec` | | Caminho do arquivo de spec |
| `-a, --agent` | claude | Agente: `claude`, `codex`, `copilot` |
| `--dry-run` | false | Preview sem executar |

#### `krab workflow new`

Cria um template YAML para workflow customizado em `.sdd/workflows/`.

```bash
krab workflow new deploy-staging --desc "Deploy para staging apos implementacao"
```

#### `krab workflow export`

Exporta um workflow built-in como YAML para customizacao.

```bash
krab workflow export implement > .sdd/workflows/implement.yaml
krab workflow export full-cycle
```

#### `krab workflow agents-check`

Verifica quais CLIs de agentes estao instalados no PATH.

```bash
krab workflow agents-check
```

#### `krab workflow commands`

Gera arquivos nativos de slash commands para cada agente de IA a partir dos workflows do krab.

```bash
# Gerar para todos os agentes
krab workflow commands

# Apenas para Claude Code
krab workflow commands --agent claude

# Apenas para Copilot
krab workflow commands --agent copilot

# Filtrar por workflow especifico
krab workflow commands --workflow implement

# Preview: ver o que seria gerado sem escrever arquivos
krab workflow commands --preview

# Preview filtrado por agente e workflow
krab workflow commands --preview --agent claude --workflow review

# Limpar todos os arquivos gerados
krab workflow commands --clean
```

| Opcao | Default | Descricao |
|-------|---------|-----------|
| `-a, --agent` | todos | Agente alvo: `claude`, `copilot` |
| `-w, --workflow` | todos | Nome do workflow especifico |
| `--preview` | false | Preview sem escrever arquivos |
| `--clean` | false | Remove todos os arquivos gerados |

**Arquivos gerados por agente:**

| Agente | Diretorio | Formato | Exemplo de uso |
|--------|-----------|---------|----------------|
| Claude Code | `.claude/commands/krab.md` | Router `/project:krab` | `/project:krab implement spec.task.auth.md` |
| Claude Code | `.claude/commands/krab-{wf}.md` | Per-workflow | `/project:krab-implement spec.task.auth.md` |
| Copilot | `.github/agents/krab.agent.md` | Agent `@krab` | `@krab implement this feature` |
| Copilot | `.github/prompts/krab-{wf}.prompt.md` | Prompt `/krab-{wf}` | `/krab-implement` no chat |
| Copilot | `.github/skills/krab-{wf}/SKILL.md` | Skill auto-loaded | Carregado automaticamente |

#### Estrutura do YAML de workflow

```yaml
name: my-workflow
description: Custom workflow
default_agent: claude
steps:
  - name: check-spec
    type: gate
    condition: "file_exists:{spec}"

  - name: analyze
    type: krab
    command: "analyze risk {spec}"
    on_failure: continue

  - name: implement
    type: agent
    agent: claude
    prompt: "Implement {spec} following Gherkin scenarios"

  - name: test
    type: shell
    command: "npm test"
    on_failure: continue
```

**5 tipos de step:** `krab` (comando interno), `shell` (qualquer comando), `agent` (delega ao AI), `gate` (condicao), `prompt` (interacao com usuario).

**Variaveis:** `{spec}`, `{agent}`, `{root}` sao resolvidas automaticamente em runtime.

**on_failure:** `stop` (padrao) para a pipeline, `continue` pula e segue para o proximo step.

---

### `krab cache`

Gerencia o cache de resultados de analise. O cache fica em `.sdd/cache/` e usa hash SHA-256 do conteudo do arquivo como chave — se o arquivo mudar, o cache e automaticamente invalidado.

#### `krab cache stats`

Mostra quantidade de entradas e uso de disco.

```bash
krab cache stats
```

#### `krab cache clear`

Remove todas as entradas do cache.

```bash
krab cache clear
```

---

## Slash Commands (Geracao Nativa)

O krab gera automaticamente arquivos de slash commands no formato nativo de cada agente de IA. Isso transforma os workflows do krab em comandos que voce pode chamar diretamente dentro do agente — sem precisar copiar/colar prompts ou lembrar sintaxe.

### Como funciona

Cada workflow do krab (built-in ou custom) e transformado em:

1. **Claude Code**: Arquivos `.claude/commands/*.md` com YAML frontmatter e `$ARGUMENTS`
2. **Copilot**: Agent `.github/agents/krab.agent.md`, prompts `.github/prompts/*.prompt.md`, e skills `.github/skills/*/SKILL.md`
3. **Cross-agent Skills**: `.github/skills/*/SKILL.md` no padrao Agent Skills (funciona em todos os agentes)

### Geracao

```bash
# Gerar tudo de uma vez (integrado com agent sync)
krab agent sync

# Ou gerar apenas os slash commands
krab workflow commands

# Filtrar por agente
krab workflow commands --agent claude

# Ver o que seria gerado
krab workflow commands --preview
```

### Uso no Claude Code

Apos gerar, os comandos ficam disponiveis como `/project:krab-*`:

```bash
# Router geral — passa o workflow e a spec como argumento
/project:krab implement spec.task.auth.md

# Comandos diretos por workflow
/project:krab-implement spec.task.auth.md
/project:krab-review spec.task.auth.md
/project:krab-verify spec.task.auth.md
/project:krab-full-cycle autenticacao-oauth2
/project:krab-spec-create login-social
/project:krab-agent-init
```

O comando router `/project:krab` aceita qualquer workflow por nome:

```
> /project:krab full-cycle spec.task.pagamentos.md
```

Cada comando inclui automaticamente:
- Contexto do projeto (do `.sdd/memory.json`)
- Steps do workflow em formato de instrucoes numeradas
- Comandos `krab` que o agente deve rodar no terminal
- Regras de execucao (gate, on_failure, Gherkin)

**Exemplo de arquivo gerado** (`.claude/commands/krab-implement.md`):

```markdown
---
description: "Krab workflow: implement — Implement a feature from spec"
---

## User Input

$ARGUMENTS

You **MUST** consider the user input before proceeding (if not empty).
If `$ARGUMENTS` contains a file path, use it as the spec file.

## Project Context

- **Project**: meu-projeto
- **Architecture**: hexagonal
- **Tech stack**: backend: Python/FastAPI, database: PostgreSQL

## Workflow: implement

1. **Gate**: Check condition `file_exists:{spec}`
2. **Run**: `krab analyze risk {spec}`
   - On failure: continue to next step
3. **Run**: `krab agent sync all`
   - On failure: continue to next step
4. **Agent** (claude): Implement the feature described in the specification...
5. **Shell**: `uv run pytest`
   - On failure: continue to next step

## Execution Rules

- For **krab** and **shell** steps: run the command in the terminal.
- For **agent** steps: you ARE the agent — execute the task directly.
- For **gate** steps: check the condition and stop if it fails.
```

### Uso no GitHub Copilot

Tres superficies de integracao:

**1. Agent `@krab`** — Dropdown no chat do Copilot:

```
@krab implementa a feature de autenticacao OAuth2 conforme a spec
```

**2. Prompts `/krab-*`** — Slash commands no chat:

```
/krab-implement     → pede o caminho da spec e executa
/krab-review        → pede o caminho da spec e faz code review
/krab-verify        → roda todas as checagens de qualidade
/krab-full-cycle    → ciclo completo de SDD
```

Cada prompt usa variaveis interativas do Copilot:

```markdown
---
agent: 'agent'
description: "Krab workflow: implement — Implement a feature from spec"
---

Spec file: ${input:spec:Path to spec file (e.g. spec.task.auth.md)}
```

**3. Skills auto-loaded** — O Copilot carrega automaticamente as skills de `.github/skills/*/SKILL.md` quando o contexto e relevante.

### Arquivos gerados (6 workflows built-in)

```
.claude/commands/
├── krab.md              → /project:krab (router)
├── krab-spec-create.md  → /project:krab-spec-create
├── krab-implement.md    → /project:krab-implement
├── krab-review.md       → /project:krab-review
├── krab-full-cycle.md   → /project:krab-full-cycle
├── krab-verify.md       → /project:krab-verify
└── krab-agent-init.md   → /project:krab-agent-init

.github/
├── agents/
│   └── krab.agent.md    → @krab no Copilot
├── prompts/
│   ├── krab-spec-create.prompt.md  → /krab-spec-create
│   ├── krab-implement.prompt.md    → /krab-implement
│   ├── krab-review.prompt.md       → /krab-review
│   ├── krab-full-cycle.prompt.md   → /krab-full-cycle
│   ├── krab-verify.prompt.md       → /krab-verify
│   └── krab-agent-init.prompt.md   → /krab-agent-init
└── skills/
    ├── krab-spec-create/SKILL.md
    ├── krab-implement/SKILL.md
    ├── krab-review/SKILL.md
    ├── krab-full-cycle/SKILL.md
    ├── krab-verify/SKILL.md
    └── krab-agent-init/SKILL.md
```

### Limpeza

```bash
# Remove todos os arquivos krab-* gerados
krab workflow commands --clean
```

---

## Exemplos End-to-End

### Exemplo 1: Implementar feature com Claude Code

```bash
# 1. Setup inicial (uma vez por projeto)
krab memory init -n "ecommerce-api" -d "API REST para e-commerce"
krab memory set tech_stack.backend "Python/FastAPI"
krab memory set tech_stack.database "PostgreSQL"
krab memory set architecture_style "hexagonal"
krab memory set conventions.commits "conventional commits"

# 2. Criar spec da feature
krab spec new task -n "Carrinho de Compras" -d "CRUD de carrinho com calculo de totais"

# 3. Refinar e analisar qualidade
krab spec refine spec.task.carrinho-de-compras.md
krab analyze risk spec.task.carrinho-de-compras.md

# 4. Sincronizar agentes (gera instrucoes + slash commands)
krab agent sync

# 5. Executar implementacao via workflow
krab workflow run implement --spec spec.task.carrinho-de-compras.md --agent claude

# 6. Ou, no Claude Code, usar o slash command diretamente:
#    /project:krab-implement spec.task.carrinho-de-compras.md
```

### Exemplo 2: Ciclo completo de SDD

```bash
# Um unico comando que faz tudo: cria spec -> refina -> analisa ->
# otimiza -> sincroniza agentes -> implementa -> testa -> review
krab workflow run full-cycle --spec pagamentos-pix --agent claude

# Dry-run primeiro para ver o que vai acontecer
krab workflow run full-cycle --spec pagamentos-pix --dry-run
```

Saida do dry-run:

```
Workflow: full-cycle (8 steps)
  [1/8] create-spec     (krab)  → spec new task -n "pagamentos-pix"
  [2/8] refine-spec     (krab)  → spec refine spec.task.pagamentos-pix.md
  [3/8] risk-analysis   (krab)  → analyze risk spec.task.pagamentos-pix.md
  [4/8] optimize-spec   (krab)  → optimize run spec.task.pagamentos-pix.md
  [5/8] sync-agents     (krab)  → agent sync all
  [6/8] implement       (agent) → claude: Implement the feature...
  [7/8] run-tests       (shell) → uv run pytest
  [8/8] review          (agent) → claude: Review the implementation...
```

### Exemplo 3: Verificar qualidade de uma spec

```bash
# Pipeline de 6 checagens automaticas
krab workflow run verify --spec spec.task.auth.md

# Ou no Claude Code:
#    /project:krab-verify spec.task.auth.md
```

O workflow `verify` executa em sequencia:
1. Gate: verifica se o arquivo existe
2. `krab analyze risk` — score de risco de alucinacao
3. `krab analyze ambiguity` — detecta termos vagos
4. `krab analyze readability` — complexidade do texto
5. `krab analyze entropy` — redundancia informacional
6. `krab spec refine` — gera plano de refinamento

### Exemplo 4: Workflow customizado via YAML

```bash
# Criar template de workflow customizado
krab workflow new deploy-staging --desc "Deploy para staging apos testes"

# Editar o YAML em .sdd/workflows/deploy-staging.yaml
```

```yaml
name: deploy-staging
description: "Deploy para staging apos testes passarem"
default_agent: claude
steps:
  - name: check-tests
    type: gate
    condition: "file_exists:tests/"

  - name: run-tests
    type: shell
    command: "uv run pytest tests/ -v"

  - name: lint
    type: shell
    command: "ruff check src/"
    on_failure: continue

  - name: build-image
    type: shell
    command: "docker build -t app:staging ."

  - name: deploy
    type: shell
    command: "kubectl apply -f k8s/staging/"

  - name: notify
    type: agent
    prompt: "Summarize what was deployed and any test results"
    on_failure: continue
```

```bash
# Executar o workflow customizado
krab workflow run deploy-staging --spec spec.task.deploy.md

# Gerar slash commands incluindo o custom
krab workflow commands
```

### Exemplo 5: Review de codigo com Copilot

```bash
# Gerar arquivos do Copilot
krab workflow commands --agent copilot

# No chat do VS Code Copilot, usar:
#   @krab review the authentication module against spec.task.auth.md
#
# Ou via prompt:
#   /krab-review
#   (o Copilot pede o caminho da spec interativamente)
```

### Exemplo 6: Exportar e personalizar workflow built-in

```bash
# Exportar o workflow 'implement' como YAML
krab workflow export implement > .sdd/workflows/implement-custom.yaml

# Editar para adicionar steps extras (ex: lint antes de implementar)
# O custom sobrescreve o built-in ao rodar workflows

# Ver a estrutura do workflow
krab workflow show implement
```

---

## Performance

O Krab CLI usa tres estrategias para performance:

**1. Lazy imports** — Rich e modulos de analise sao carregados sob demanda, nao no startup. Apenas Typer e carregado no topo.

**2. Cache de analise** — Resultados de `analyze tokens/quality/entropy/readability/freq` sao armazenados em `.sdd/cache/` com chave baseada no hash do conteudo. Execucoes repetidas sobre o mesmo arquivo retornam instantaneamente.

**3. Batch mode** — `krab analyze batch` processa multiplos arquivos em uma unica invocacao, evitando o custo de startup do Python (~400ms) para cada arquivo.

| Cenario | Sem otimizacao | Com otimizacao | Ganho |
|---------|---------------|----------------|-------|
| `analyze tokens` (100KB, cache hit) | 878ms | 405ms | 54% |
| `analyze readability` (100KB, cache hit) | 657ms | 386ms | 41% |
| 10 arquivos individuais vs batch | 8097ms | 435ms | 18.6x |

---

## Algoritmos (25)

| # | Algoritmo | Modulo | Finalidade |
|---|-----------|--------|------------|
| 1 | **Huffman-inspired Aliases** | `core/huffman.py` | Compressao de termos repetidos em aliases curtos |
| 2 | **Fuzzy Matching** (RapidFuzz) | `core/fuzzy.py` | Deteccao de secoes duplicadas e near-duplicates |
| 3 | **Jaccard Similarity** | `core/similarity.py` | Comparacao baseada em conjuntos de termos |
| 4 | **Cosine Similarity (TF)** | `core/similarity.py` | Similaridade vetorial por frequencia de termos |
| 5 | **N-gram Overlap** | `core/similarity.py` | Similaridade estrutural por bigramas |
| 6 | **TF-IDF Cosine** | `core/similarity.py` | Similaridade ponderada pela importancia no corpus |
| 7 | **Context Quality Score** | `core/similarity.py` | Densidade informacional e uso da janela de contexto |
| 8 | **Shannon Entropy** | `core/entropy.py` | Conteudo informacional real — identifica redundancia |
| 9 | **Markov Chain (ordem 1-2)** | `core/entropy.py` | Previsibilidade do texto — detecta boilerplate |
| 10 | **Perplexity estimada** | `core/entropy.py` | Quao "surpreendente" o texto e para um modelo |
| 11 | **Flesch-Kincaid / Gunning Fog** | `core/readability.py` | Legibilidade — complexidade aumenta hallucination |
| 12 | **Coleman-Liau / ARI** | `core/readability.py` | Legibilidade baseada em caracteres (bom para codigo) |
| 13 | **Ambiguity Detector** | `core/ambiguity.py` | Detecta termos vagos (etc, TBD, approximately) |
| 14 | **Suffix Array + LCP** | `core/substrings.py` | Substrings repetidos exatos de qualquer tamanho |
| 15 | **N-gram Phrase Counter** | `core/substrings.py` | Frases repetidas multi-palavra |
| 16 | **0/1 Knapsack** | `core/budget.py` | Selecao otima de secoes dentro de um budget de tokens |
| 17 | **MinHash + LSH** | `core/minhash.py` | Deteccao escalavel de near-duplicates em O(n) |
| 18 | **BM25 Ranking** | `core/bm25.py` | Busca ranqueada por relevancia (superior ao TF-IDF) |
| 19 | **Delta Encoding** | `core/delta.py` | Diff compacto entre versoes de specs |
| 20 | **Dependency Graph** | `core/depgraph.py` | Grafo de referencias cruzadas entre specs |
| 21 | **Chunking Analyzer** | `core/chunking.py` | Comparacao de estrategias de split para contexto |
| 22 | **RAKE** | `core/semantic.py` | Extracao de keywords (Rapid Automatic Keyword Extraction) |
| 23 | **TextRank** | `core/semantic.py` | Sentencas mais importantes via PageRank |
| 24 | **Semantic Compression** | `core/semantic.py` | Compressao semantica preservando conceitos-chave |
| 25 | **Hallucination Risk Score** | `core/risk.py` | Score combinado de risco de alucinacao do agente |

---

## Arquitetura

```
src/krab_cli/
├── __init__.py                 # Versao
├── cli.py                      # Entry point (10 grupos, 50+ comandos)
├── core/
│   ├── huffman.py              # Huffman aliases + compressao
│   ├── fuzzy.py                # Fuzzy matching (RapidFuzz)
│   ├── similarity.py           # Jaccard, Cosine, N-gram, TF-IDF
│   ├── optimizer.py            # Pipeline unificado
│   ├── tokens.py               # Contagem de tokens (tiktoken)
│   ├── entropy.py              # Shannon Entropy, Markov, Perplexity
│   ├── readability.py          # Flesch-Kincaid, Gunning Fog, Coleman-Liau, ARI
│   ├── ambiguity.py            # Detector de termos vagos/ambiguos
│   ├── substrings.py           # Suffix Array, repeated phrases
│   ├── budget.py               # Token Budget Optimizer (Knapsack)
│   ├── minhash.py              # MinHash + LSH
│   ├── bm25.py                 # BM25 ranking/search
│   ├── delta.py                # Delta encoding
│   ├── depgraph.py             # Dependency Graph
│   ├── chunking.py             # Chunking Strategy Analyzer
│   ├── semantic.py             # RAKE, TextRank, Semantic Compression
│   └── risk.py                 # Hallucination Risk Score
├── converters/
│   ├── converter.py            # Dispatcher de conversao
│   ├── md_parser.py            # Markdown -> Dict
│   └── md_builder.py           # Dict -> Markdown
├── models/
│   └── spec.py                 # Modelo de dados
├── templates/
│   ├── __init__.py             # Engine de templates + registry
│   ├── task.py                 # Template: spec de tarefa (Gherkin)
│   ├── architecture.py         # Template: spec de arquitetura (C4, ADR)
│   ├── plan.py                 # Template: plano de implementacao
│   ├── skill.py                # Template: skills do projeto
│   └── refining.py             # Template: refinamento Tree-of-Thought
├── workflows/
│   ├── __init__.py             # Workflow engine: steps, runner, YAML persistence
│   ├── executor.py             # Agent executor: wraps claude/codex/copilot CLIs
│   ├── builtins.py             # 6 built-in workflow definitions
│   └── commands.py             # Slash command generator (Claude, Copilot, Skills)
├── agents/
│   └── __init__.py             # Geradores: Claude, Copilot, Codex
├── memory/
│   └── __init__.py             # MemoryStore (.sdd/ persistence)
└── utils/
    ├── display.py              # Rich console helpers (lazy loading)
    └── cache.py                # Cache de analise (.sdd/cache/)

tests/                          # 20 arquivos, 364 testes
├── test_agents.py
├── test_cache.py               # Cache module (18 testes)
├── test_cli.py
├── test_cli_new.py
├── test_cli_spec.py
├── test_commands.py            # Slash command generator + CLI integration (41 testes)
├── test_converters.py
├── test_fuzzy.py
├── test_huffman.py
├── test_memory.py
├── test_optimizer.py
├── test_similarity.py
├── test_templates.py
├── test_wave1.py               # Entropy, Readability, Ambiguity, Substrings
├── test_wave2.py               # Budget, MinHash, BM25, Delta
├── test_wave3.py               # Chunking, DepGraph, Semantic, Risk
└── test_workflows.py           # Workflow engine, executor, builtins, CLI (67 testes)
```

---

## Desenvolvimento

```bash
# Setup
uv sync

# Testes
uv run pytest tests/ -v             # 364 testes

# Lint
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

---

## Stack

Python 3.11+ · Typer · Rich · RapidFuzz · tiktoken · PyYAML · Hatchling · pytest · ruff

---

## Licenca

MIT
