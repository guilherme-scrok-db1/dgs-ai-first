# Desenvolvedor — Exercício 2.2

## Análise do estado inicial
- `specs/query-endpoint/tasks.md` estava vazio, então a transição `plan -> tasks` ainda não havia sido feita.
- `src/functions/query/handler.ts` estava apenas com stub e sem validação de contrato.
- O repositório já tinha a estrutura correta em `src/functions/query/`, então a implementação pôde seguir o path esperado pelo cenário.

## Tasks atômicas geradas
Arquivo preenchido: `Prática 2/Entregas/novatech-assistant/specs/query-endpoint/tasks.md`

Tasks criadas:
- `T-01` Bootstrap do endpoint HTTP com validação de contrato
- `T-02` Carregamento do system prompt versionado
- `T-03` Cliente de embeddings com retry
- `T-04` Busca top-5 no Azure AI Search com vigência
- `T-05` Montagem do prompt com context budget
- `T-06` Orquestração de completion e validação da resposta
- `T-07` Observabilidade e testes do endpoint

Cada task contém:
- ID
- descrição
- critérios de aceite verificáveis
- dependências
- estimativa `P/M/G`

## Primeira task implementada
Foi implementado o primeiro slice em `Prática 2/Entregas/novatech-assistant/src/functions/query/`:
- `handler.ts`: parsing de JSON, validação Zod, respostas `400` tipadas e resposta `202` de bootstrap.
- `validator.ts`: schemas Zod para request e response do endpoint.

## Contrato implementado
- Body inválido em JSON -> `400 INVALID_JSON`
- Body sem `question` -> `400 INVALID_REQUEST`
- Body válido -> `202` com `answer`, `source_document`, `confidence` e `warning`
- Logging estruturado via `pino`
- Nenhum uso de `console.log`

## Validação executável
Build executado com sucesso após instalar dependências:
```text
> novatech-assistant@0.1.0 build
> tsc -p .
```

## Revisão crítica do código gerado
Antes de um code review real, eu exigiria pelo menos estes ajustes adicionais:

1. O handler ainda retorna uma resposta placeholder.
   Motivo: a task 1 cumpre bootstrap e contrato, mas ainda não chama prompt builder, retrieval nem completion. Isso é aceitável para `T-01`, porém insuficiente para o endpoint final.

2. O código tipa uma interface `HttpRequestLike` local em vez de usar diretamente os tipos oficiais de Azure Functions v4.
   Motivo: isso reduz acoplamento no primeiro slice e facilita build local, mas o próximo passo deve alinhar o contrato ao runtime oficial.

3. Ainda não há teste automatizado do contrato de validação.
   Motivo: o build passou, mas faltam testes unitários para `INVALID_JSON`, `INVALID_REQUEST` e fluxo válido.

## Conexão com o cenário 1
A decomposição considera explicitamente a transição do protótipo open-source para produção:
- o retrieval passa de corpus local/Chroma para Azure AI Search em `T-04`
- o embedding passa a Azure OpenAI em `T-03`
- a montagem de prompt respeita o context budget da ADR-0002 em `T-05`
- o tratamento de vigência/contradição da ADR-0003 entra na busca e priorização

## Arquivos relacionados
- `Prática 2/Entregas/novatech-assistant/specs/query-endpoint/tasks.md`
- `Prática 2/Entregas/novatech-assistant/src/functions/query/handler.ts`
- `Prática 2/Entregas/novatech-assistant/src/functions/query/validator.ts`
- `Prática 2/Entregas/novatech-assistant/package.json`
