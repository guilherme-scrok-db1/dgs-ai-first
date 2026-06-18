# Desenvolvedor — Exercício 2.3

## Análise do estado inicial
- `skills/foundation/typescript-conventions.md` estava vazio, então a skill foundation mais importante ainda não existia.
- A árvore de skills já estava sugerida pela estrutura do repo (`foundation/`, `domain/`, `artifact/`), mas faltava formalizar criação, consumo e frequência de uso.

## Árvore de skills proposta

### Foundation
- `typescript-conventions`
- `error-handling`
- `project-structure`
- `logging-and-observability`
- `environment-config`

### Domain
- `azure-functions-endpoint`
- `azure-ai-search-integration`
- `testing-patterns`
- `react-components`
- `feedback-workflow`

### Artifact
- `create-rag-endpoint`
- `create-integration-test`
- `create-react-card`
- `create-endpoint-readme`
- `create-sdd-spec`

## Criação e consumo por papel

| Skill | Quem cria | Quem consome | Frequência estimada |
|---|---|---|---|
| `typescript-conventions` | Tech Lead + Dev sênior | Devs, Copilot, Claude | Muito alta |
| `error-handling` | Tech Lead | Devs, Copilot | Alta |
| `project-structure` | Tech Lead | Devs, Copilot | Alta |
| `azure-functions-endpoint` | Tech Lead | Devs, Copilot | Alta |
| `testing-patterns` | QA + Tech Lead | Devs, QA, Copilot | Alta |
| `react-components` | Dev front + Product Specialist | Devs front, Copilot | Média |
| `create-rag-endpoint` | Dev sênior | Devs, Copilot | Média |
| `create-integration-test` | QA | Devs, QA, Copilot | Média |
| `create-sdd-spec` | Product Specialist + Tech Lead | PS, TL, Claude | Média |
| `create-endpoint-readme` | Dev + Delivery Manager | Devs, Claude | Baixa |

## Skill Foundation criada
Arquivo preenchido: `Prática 2/Entregas/novatech-assistant/skills/foundation/typescript-conventions.md`

Conteúdo incluído:
- contexto de uso
- frase de ativação
- regras prescritivas
- exemplos `DO` / `DON'T` em TypeScript
- anti-padrões úteis para LLMs
- checklist de revisão

## Por que essa é a skill foundation mais importante
Ela é a base de todas as demais porque força:
- strict mode
- contratos explícitos
- validação Zod em fronteiras externas
- imports estáticos ESM
- logging via `pino`
- proibição de atalhos inseguros (`as any`, `console.log`, `@ts-ignore`)

Sem essa camada, o Copilot tende a produzir exatamente os anti-padrões que o projeto quer evitar.

## Anti-padrões cobertos
- `as any` para contornar contrato de SDK ou request HTTP.
- `console.log` em handler, teste ou utilitário compartilhado.
- `export default` em utilitários pequenos, dificultando imports consistentes.
- validação parcial de payload
- retorno inconsistente sem schema ou tipo discriminado

## Arquivos relacionados
- `Prática 2/Entregas/novatech-assistant/skills/foundation/typescript-conventions.md`
- `Prática 2/Entregas/novatech-assistant/skills/domain/azure-functions-endpoint.md`
- `Prática 2/Entregas/novatech-assistant/skills/artifact/create-rag-endpoint.md`
