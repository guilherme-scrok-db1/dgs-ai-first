# Desenvolvedor - Exercicio 3.1

## Analise dos resultados atuais (antes da resolucao)
- A pasta de entrega de Pratica 3 estava vazia.
- Ja existia implementacao tecnica em Pratica 2 no modulo de validacao de resposta, com Zod e guardrails basicos.
- Gap real identificado: o guardrail de carga perigosa/devolucao tinha heuristica fragil por busca de substring (podia interpretar "assim" como "sim" e "nao pode" como afirmacao por conter "pode").

## Implementacao final

### 1. Structured output com Zod
Schema aplicado com os campos obrigatorios solicitados e validacao estrita:
- `answer`: string obrigatoria
- `source_document`: string obrigatoria
- `confidence_score`: numero entre 0 e 1
- `.strict()` para rejeitar campos extras

Implementado em:
- `Pratica 2/Entregas/novatech-assistant/src/services/response-validator.ts`

### 2. Guardrail deterministico 1 - fonte obrigatoria
- Resposta sem `source_document` valido e rejeitada.
- Em falha: motivo vai para log estruturado e a resposta e substituida por fallback seguro.

### 3. Guardrail deterministico 2 - carga perigosa + devolucao
- Se a resposta mencionar carga perigosa e devolucao, ela deve manter a negativa.
- Se houver afirmacao de permissao, a resposta e bloqueada.
- Cobertura expandida para variacoes linguisticas adicionais (ex.: mercadoria/produto perigoso, devolvida/devolvido/devolucoes).

## Code review rapido (rodada de correcao)
Problemas reais encontrados e corrigidos:

1. Falso positivo por substring `sim`
- Problema: `includes("sim")` marcava "assim" como afirmacao.
- Correcao: tokenizacao e verificacao por token isolado.

2. Conflito entre afirmacao e negacao (`pode` em `nao pode`)
- Problema: `includes("pode")` classificava frases negativas como afirmativas.
- Correcao: deteccao contextual com token anterior (`nao`) e regra especifica para `e possivel` versus `nao e possivel`.

3. Robustez lexical
- Melhoria: normalizacao de pontuacao e espacos antes da analise de termos.

4. Cobertura insuficiente de variacoes linguisticas
- Problema: a validacao estava correta, mas com cobertura de testes curta para variacoes reais de linguagem.
- Correcao: ampliacao de regras deterministicas e inclusao de testes para caixa alta, variacoes de termos e schema strict com campo extra.

## Distincao probabilistico x deterministico
- Prompt e probabilistico: orienta o modelo, mas nao garante formato nem cumprimento exato.
- Validador em codigo e deterministico: rejeita resposta fora do schema e bloqueia violacoes dos guardrails com comportamento reproduzivel.

## Conexao explicita com Cenarios 1 e 2 (D5)
- Cenario 1 (fundacao de RAG): a exigencia de rastreabilidade "toda resposta deve citar fonte" foi transformada em bloqueio deterministico no schema com `source_document` obrigatorio.
- Cenario 1 (dominio NovaTech): a regra de POL-001 sobre devolucao de carga perigosa foi convertida em guardrail de codigo que bloqueia afirmacao indevida, mesmo que o prompt falhe.
- Cenario 2 (governanca de agentes): a regra de padronizacao e validação contratual foi aplicada com Zod strict + fallback seguro, reduzindo variabilidade do output gerado por IA.
- Cenario 2 (revisao critica): o ciclo humano -> segunda revisao -> correcao foi seguido para transformar heuristica fragil em regra mais robusta e testavel.

## Evidencia explicita de uso de Claude/Copilot
- Registro de prompt, resposta e decisao da rodada de implementacao/revisao: `Pratica 3/Entrega/evidencias/dev-ex3.1-interacoes-claude-copilot.md`

## Evidencia real de execucao

Comando executado no repositorio tecnico:
- `npm run test` em `Pratica 2/Entregas/novatech-assistant`

Resultado:
- 2 arquivos de teste executados
- 10 testes passando
- Casos cobrindo schema invalido, bloqueio de afirmacao em carga perigosa/devolucao, ausencia de falso positivo para "assim", variacoes linguisticas e rejeicao de campo extra por schema strict.

Comando executado:
- `npm run build`

Resultado:
- Build TypeScript concluido com sucesso.

## Artefatos de auditabilidade
- Log bruto da execucao de testes: `Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt`
- Log bruto da execucao de build: `Pratica 3/Entrega/evidencias/dev-ex3-build-output.txt`
- Diff dos arquivos alterados: `Pratica 3/Entrega/evidencias/dev-ex3-diff.txt`
- Registro de interacoes Claude/Copilot (prompt -> resposta -> decisao): `Pratica 3/Entrega/evidencias/dev-ex3.1-interacoes-claude-copilot.md`

## Arquivos alterados/criados nesta resolucao
- `Pratica 2/Entregas/novatech-assistant/src/services/response-validator.ts`
- `Pratica 2/Entregas/novatech-assistant/tests/unit/response-validator.spec.ts`
- `Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3-build-output.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3-diff.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3.1-interacoes-claude-copilot.md`
