# Desenvolvedor - Exercicio 3.2

## Analise dos resultados atuais (antes da resolucao)
- A pasta de entrega de Pratica 3 estava vazia.
- O modulo de feedback em Pratica 2 ja estava refatorado para padroes seguros (Zod + pino + import estatico).
- Faltava registrar a revisao critica comparativa e anexar evidencia executavel.

## 1) Minha revisao ANTES da segunda rodada
Classificacao por problema:

### Violacoes do AGENTS.md
- Uso de `as any` sem validacao de input (quebra contrato strict).
- Uso de `console.log` em vez de logger estruturado.
- Uso de `require` dinamico em runtime.

### Seguranca
- Log de dado pessoal (`attendantEmail`) em texto claro.

### Bugs potenciais
- Sem tratamento consistente para JSON invalido.
- Sem resposta padronizada de erro por contrato.

## 2) Segunda revisao (co-review independente)
Observacoes adicionais da segunda rodada:
- Necessidade de schema `.strict()` para rejeitar chaves nao previstas.
- Separacao da persistencia em repositorio injetavel para testabilidade e resiliencia.
- Logs de sucesso devem incluir somente metadados nao sensiveis.

## 3) Comparacao humano vs segunda revisao
- Concordancias: `as any`, `console.log`, `require` dinamico e PII em log foram detectados por ambas as rodadas.
- Complemento da segunda rodada: reforco em testabilidade (injeccao de repositorio) e padronizacao de respostas de erro.
- Diferenca principal: a minha primeira revisao focou mais em conformidade/sigilo; a segunda aumentou foco em arquitetura e observabilidade.

## Conexao explicita com Cenarios 1 e 2 (D5)
- Cenario 1: continuidade do principio de confiabilidade de resposta e rastreabilidade operacional, agora aplicado ao endpoint de feedback para evitar entrada invalida e efeitos colaterais silenciosos.
- Cenario 2: aderencia ao AGENTS/skills de TypeScript strict e validacao em fronteira (Zod), com logging estruturado e sem vazamento de PII.
- Cenario 2: reforco de governanca de codigo gerado por IA via revisao critica em duas rodadas (humano primeiro, IA depois).

## Evidencia explicita de uso de Claude/Copilot
- Registro de prompt, resposta e decisao da revisao/reescrita: `Pratica 3/Entrega/evidencias/dev-ex3.2-interacoes-claude-copilot.md`

## 4) Codigo reescrito (resultado final)
Implementacao consolidada em:
- `Pratica 2/Entregas/novatech-assistant/src/functions/feedback/handler.ts`
- `Pratica 2/Entregas/novatech-assistant/src/functions/feedback/validator.ts`

Caracteristicas finais:
- Validacao de input com Zod (`safeParse`) e schema estrito.
- Logging via pino (sem `console.log`).
- Sem `require` dinamico; imports estaticos no topo.
- Sem logar `attendantEmail` ou outro dado pessoal.
- Contratos de erro consistentes (`INVALID_JSON`, `INVALID_REQUEST`, `PERSISTENCE_ERROR`).

## Evidencia real de execucao

Comando executado no repositorio tecnico:
- `npm run test` em `Pratica 2/Entregas/novatech-assistant`

Resultado:
- 10 testes passando.
- Cobertura direta dos cenarios de feedback:
  - JSON invalido retorna 400.
  - Campo pessoal extra (`attendantEmail`) e rejeitado por schema strict.
  - Payload valido persiste apenas dados saneados.
  - Suite tambem valida o guardrail de structured output e variacoes linguisticas do bloqueio deterministico.

Comando executado:
- `npm run build`

Resultado:
- Build TypeScript concluido com sucesso.

## Artefatos de auditabilidade
- Log bruto da execucao de testes: `Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt`
- Log bruto da execucao de build: `Pratica 3/Entrega/evidencias/dev-ex3-build-output.txt`
- Diff dos arquivos alterados: `Pratica 3/Entrega/evidencias/dev-ex3-diff.txt`
- Registro de interacoes Claude/Copilot (prompt -> resposta -> decisao): `Pratica 3/Entrega/evidencias/dev-ex3.2-interacoes-claude-copilot.md`

Esses artefatos elevam a rastreabilidade da revisao, pois registram saida real de execucao e delta objetivo de codigo.

## Arquivos alterados/criados nesta resolucao
- `Pratica 2/Entregas/novatech-assistant/tests/unit/feedback-handler.spec.ts`
- `Pratica 3/Entrega/evidencias/dev-ex3-test-output.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3-build-output.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3-diff.txt`
- `Pratica 3/Entrega/evidencias/dev-ex3.2-interacoes-claude-copilot.md`
