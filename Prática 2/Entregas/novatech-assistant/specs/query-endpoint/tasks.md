# Tasks — Query Endpoint

## T-01 — Bootstrap do endpoint HTTP com validação de contrato
- ID: `T-01`
- Descrição: Criar o handler HTTP do endpoint `POST /api/query` com validação de input via Zod, resposta JSON padronizada e logging estruturado.
- Critérios de aceite:
	- Requisições sem body JSON válido retornam `400` com código `INVALID_JSON`.
	- Requisições sem o campo `question` retornam `400` com código `INVALID_REQUEST` e detalhe do campo inválido.
	- Requisições válidas retornam resposta JSON com `answer`, `source_document` e `confidence`.
	- O handler não usa `console.log`; todo log passa por `pino`.
- Dependências: nenhuma.
- Estimativa: `P`

## T-02 — Carregamento do system prompt versionado
- ID: `T-02`
- Descrição: Ler `/prompts/system-prompt.md`, aplicar cache em memória do processo e falhar com erro explícito se o prompt não existir.
- Critérios de aceite:
	- O conteúdo do prompt é carregado a partir do path versionado definido no plan.
	- Falha de leitura gera erro observável em log estruturado.
	- O carregamento é reutilizável por chamadas subsequentes do endpoint.
- Dependências: `T-01`.
- Estimativa: `P`

## T-03 — Cliente de embeddings com retry
- ID: `T-03`
- Descrição: Implementar cliente de embeddings do Azure OpenAI com retry exponencial e timeout para transformar a pergunta do atendente em embedding.
- Critérios de aceite:
	- Chamadas transitórias são reexecutadas com exponential backoff.
	- Timeout encerra a chamada e retorna erro técnico rastreável.
	- O payload enviado ao Azure é tipado e validado.
- Dependências: `T-01`.
- Estimativa: `M`

## T-04 — Busca top-5 no Azure AI Search com vigência
- ID: `T-04`
- Descrição: Consultar o índice do Azure AI Search para recuperar os 5 chunks mais relevantes, priorizando documentos vigentes conforme ADR-0003.
- Critérios de aceite:
	- A busca retorna no máximo 5 chunks.
	- Chunks de versões obsoletas só aparecem quando a versão vigente também é sinalizada.
	- O resultado inclui metadados mínimos: `documentId`, `section`, `effectiveFrom`, `score`.
- Dependências: `T-03`.
- Estimativa: `M`

## T-05 — Montagem do prompt com context budget
- ID: `T-05`
- Descrição: Combinar system prompt, chunks recuperados, pergunta atual e até 3 turnos de histórico dentro do orçamento de contexto definido na ADR-0002.
- Critérios de aceite:
	- O builder respeita o orçamento aproximado de `~4K` tokens para system prompt e `~8K` para chunks.
	- O histórico é limitado a 3 turnos.
	- Quando o orçamento estoura, chunks menos relevantes são removidos antes do envio ao modelo.
- Dependências: `T-02`, `T-04`.
- Estimativa: `M`

## T-06 — Orquestração de completion e validação da resposta
- ID: `T-06`
- Descrição: Enviar o prompt para o GPT-4o, validar a saída com Zod e garantir retorno com `source_document` em todas as respostas.
- Critérios de aceite:
	- A resposta válida sempre contém `answer`, `source_document` e `confidence`.
	- Respostas de baixa confiança incluem `warning` com fallback orientado ao atendente.
	- Resposta inválida do modelo é rejeitada antes de chegar ao consumidor.
- Dependências: `T-05`.
- Estimativa: `M`

## T-07 — Observabilidade e testes do endpoint
- ID: `T-07`
- Descrição: Cobrir o fluxo principal com testes e adicionar logs estruturados para tempo de resposta, busca e falhas de integração.
- Critérios de aceite:
	- Há testes para input inválido, fluxo feliz e ausência de match.
	- Logs incluem `requestId`, duração e status final da query.
	- Cenários derivados do protótipo open-source do cenário 1 permanecem representados nos fixtures.
- Dependências: `T-01`, `T-04`, `T-06`.
- Estimativa: `M`
