# Evidencia de interacao - Exercicio 3.1

## Rodada 1 - Copilot (implementacao)
### Prompt utilizado
Implementar validador de resposta com structured output em Zod para os campos answer, source_document e confidence_score, com fallback seguro em falhas e guardrail deterministico para bloquear qualquer resposta afirmativa sobre devolucao de carga perigosa.

### Resposta gerada (resumo tecnico)
- Schema Zod com answer, source_document, confidence_score e strict.
- Fallback seguro em falha de schema.
- Guardrail lexical para carga perigosa + devolucao.

### Decisao tomada
Aceito parcialmente. Mantive a estrutura geral e abri revisao critica para reduzir risco de falso positivo/negativo na heuristica lexical.

## Rodada 2 - Claude (revisao critica)
### Prompt utilizado
Revise criticamente o validador em TypeScript e identifique problemas reais em regras de linguagem natural que possam aprovar ou bloquear resposta incorretamente no guardrail de carga perigosa/devolucao.

### Resposta gerada (resumo tecnico)
- Risco de falso positivo em includes("sim") para palavras como "assim".
- Risco de falso bloqueio por includes("pode") em frases negativas como "nao pode".
- Recomendacao de tokenizacao e avaliacao contextual com negacao.

### Decisao tomada
Aprovada a recomendacao. Implementei tokenizacao normalizada, regras contextuais de afirmacao/negacao e cobertura de testes para variacoes linguisticas.

## Resultado aplicado no codigo
- Arquivo: Pratica 2/Entregas/novatech-assistant/src/services/response-validator.ts
- Evidencia de execucao: Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt
