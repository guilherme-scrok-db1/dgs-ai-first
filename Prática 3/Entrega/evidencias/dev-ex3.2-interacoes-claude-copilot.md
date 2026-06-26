# Evidencia de interacao - Exercicio 3.2

## Rodada 1 - Revisao humana antes de IA
### Checklist proprio aplicado
- as any sem validacao de input.
- console.log em vez de pino.
- require dinamico.
- Exposicao de attendantEmail em log.

### Decisao tomada
Classifiquei como violacoes criticas de padrao e seguranca; reescrita completa obrigatoria antes de merge.

## Rodada 2 - Claude (co-review)
### Prompt utilizado
Atue como segundo revisor e compare com minha lista de problemas em um handler de feedback para Azure Functions, destacando lacunas de validacao, logging, import e privacidade.

### Resposta gerada (resumo tecnico)
- Confirmou os quatro problemas principais.
- Reforcou schema strict e retorno de erros padronizados.
- Reforcou separar persistencia por repositorio injetavel para testabilidade.

### Decisao tomada
Mantive os quatro bloqueadores como criterios de aceite e incorporei os reforcos de testabilidade e contrato de erro na versao final.

## Rodada 3 - Copilot (reescrita guiada)
### Prompt utilizado
Reescreva o modulo de feedback em TypeScript strict com Zod safeParse, pino, sem require dinamico e sem log de dados pessoais; inclua tratamento para JSON invalido, request invalida e erro de persistencia.

### Resposta gerada (resumo tecnico)
- Handler com validacao Zod e respostas padronizadas.
- Logging estruturado com pino sem PII.
- Persistencia injetavel e testes diretos por contrato.

### Decisao tomada
Aprovado com pequenos ajustes finais de nomenclatura e testes de regressao.

## Resultado aplicado no codigo
- Arquivos: Pratica 2/Entregas/novatech-assistant/src/functions/feedback/handler.ts e Pratica 2/Entregas/novatech-assistant/src/functions/feedback/validator.ts
- Evidencia de execucao: Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt
