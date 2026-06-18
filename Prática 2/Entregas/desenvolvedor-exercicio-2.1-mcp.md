# Desenvolvedor — Exercício 2.1

## Análise do estado inicial
- `.mcp/mcp.json` estava vazio (`"mcpServers": {}`), então o exercício 2.1 ainda não tinha configuração utilizável.
- A documentação de negócio já existia em `docs/novatech/` e o corpus em `data/retrieval-corpus/`, mas faltava a configuração local dos servers e a evidência de uso.

## Mapeamento necessidade -> server local

| Necessidade do projeto | Server local | Tools / Resources / Prompts | Quem consome | Escopo mínimo |
|---|---|---|---|---|
| Ler e editar código, specs e skills | `filesystem-workspace` | Tools de leitura e escrita em arquivos; resources implícitos via paths | Dev, Tech Lead, Copilot, Claude | `src/`, `specs/`, `skills/` |
| Ler documentação da NovaTech | `filesystem-docs-readonly` | Tools de leitura/listagem; documents em `docs/novatech/` | Dev, Product Specialist, QA, agentes de contexto | `docs/novatech/` |
| Ler corpus de retrieval | `filesystem-corpus-readonly` | Tools de leitura/busca; chunks em `data/retrieval-corpus/` | Dev, QA, agentes RAG | `data/retrieval-corpus/` |
| Ler histórico e branches locais | `git` | Tools de status, diff, log, branch, show | Dev, Tech Lead, agentes de revisão | repositório local |
| Manter memória persistente de decisões e linguagem ubíqua | `memory` | Tools de grafo local persistente | Dev, Tech Lead, Claude | `.mcp/memory.jsonl` |
| Explorar primitivas MCP | `everything` | Tools de demonstração / aprendizado | Dev, Tech Lead | sem escopo de negócio |

## Least privilege aplicado
- O `filesystem` foi dividido em três servers para reduzir blast radius.
- `filesystem-workspace` recebe apenas `src/`, `specs/` e `skills/`, evitando acesso desnecessário a `docs/`, `data/`, `.git/`, `node_modules/` e segredos locais.
- `filesystem-docs-readonly` recebe só `docs/novatech/`, isolando a fonte de verdade documental.
- `filesystem-corpus-readonly` recebe só `data/retrieval-corpus/`, isolando a fonte de busca.
- `git` lê o repositório local inteiro porque precisa de histórico, branch e diff; esse é o menor escopo funcional para esse server.
- `memory` persiste apenas em um arquivo dedicado dentro de `.mcp/`, sem tocar código ou docs.

## Arquivo configurado
Arquivo preenchido: `Prática 2/Entregas/novatech-assistant/.mcp/mcp.json`

Servers configurados:
- `filesystem-workspace`
- `filesystem-docs-readonly`
- `filesystem-corpus-readonly`
- `git`
- `memory`
- `everything`

## Evidência de execução

### Validação da configuração JSON
```text
everything
filesystem-corpus-readonly
filesystem-docs-readonly
filesystem-workspace
git
memory
```

### Pacotes MCP locais acessíveis
```text
@modelcontextprotocol/server-filesystem 2026.1.14
@modelcontextprotocol/server-memory 2026.1.26
@modelcontextprotocol/server-everything 2026.1.26
uvx.exe disponível no ambiente
```

### Tentativa real de probe via MCP
Foi criado o script `Prática 2/Entregas/_scripts/mcp_probe.mjs` para falar JSON-RPC por stdio com os servers configurados. O probe conseguiu validar que o server `filesystem` inicializa e acusa erro real de path quando o quoting de Windows está incorreto; depois avançou para timeout no handshake do `filesystem-docs-readonly` via stdio bruto. Isso caracteriza tentativa real de execução MCP no ambiente local, mas com limitação operacional do transporte raw no Windows para esse setup específico.

### Evidência do conteúdo que os servers precisam expor
Documento de negócio lido localmente:
```text
# POL-001 — Política de Devolução de Mercadorias
Versão: 3.1
Última atualização: 15/01/2024
...
As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão:
- Cargas perigosas classificadas nas classes 1 a 6 da ANTT
```

Chunk relevante do corpus para a pergunta “Qual o multiplicador para o Sudeste?”:
```text
Chunk PROC-042v2-B — Seção 2.1: Multiplicadores regionais atualizados
Multiplicadores regionais atualizados (novembro/2023): Sul 1.3, Sudeste 1.1, Centro-Oeste 1.4, Nordeste 1.5, Norte 1.8.
...
Mapa de cobertura:
"Qual o multiplicador para o Sudeste?" -> PROC-042v2-B | PROC-042-B (versão antiga — contradição: 1.0 vs 1.1)
```

Histórico do Git local:
```text
bbdd03a (HEAD -> master) chore: starter repo (Anexo D) — estrutura + dados semeados dos Anexos A e B
```

## Riscos de segurança e mitigação
1. Escopo amplo demais no `filesystem`.
   Mitigação: separar docs, corpus e workspace em servers distintos e nunca expor a raiz do workspace nem `.git` por `filesystem`.

2. Escrita habilitada onde deveria haver leitura.
   Mitigação: usar servers separados para fontes documentais e tratá-los operacionalmente como somente leitura; qualquer alteração de docs/corpus deve ocorrer por revisão humana fora do fluxo de agentes.

3. `memory` persistindo fatos incorretos.
   Mitigação: versionar convenções principais em arquivos do repositório e usar `memory` apenas para decisões auxiliares e linguagem ubíqua aprovada.

4. Agente alterando código sem gate humano.
   Mitigação: manter validation gates e exigir revisão humana antes de merge, mesmo em fluxo local.

## Arquivos relacionados
- `Prática 2/Entregas/novatech-assistant/.mcp/mcp.json`
- `Prática 2/Entregas/_scripts/mcp_probe.mjs`
