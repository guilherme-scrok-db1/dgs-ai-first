# Relatório de Teste — Pipeline RAG NovaTech

Total de perguntas testadas: 5


---

## Pergunta 1: "Qual o prazo de devolução?"

### Chunks recuperados

| Rank | Score | Fonte | Seção | Preview |
|------|-------|-------|-------|---------|
| 1 | 0.3710 | POL-001-politica-devolucao.md | 3.5. Custos de devolução | ## 3.5. Custos de devolução  - Defeito ou erro da NovaTech (carga errada, avaria… |
| 2 | 0.4356 | FAQ-atendimento.md | Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?" | ## Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?"… |
| 3 | 0.4390 | POL-001-politica-devolucao.md | 3.3. Procedimento de devolução | ## 3.3. Procedimento de devolução  1. O cliente abre chamado no Portal do Client… |
| 4 | 0.4517 | PROC-042-frete-especial-v1.md | 3. Prazo de entrega para frete especial | ## 3. Prazo de entrega para frete especial  O prazo de entrega para frete especi… |
| 5 | 0.4765 | FAQ-atendimento.md | Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?" | ## Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?"  Respo… |

### Chunks esperados (gabarito)

- POL-001 (Seção 3.1 — Prazo geral)
- POL-001 (Seção 3.2 — Exceções ao prazo geral)

### Chunks possíveis (relevância menor)

- POL-001 (Seção 3.3 — Procedimento de devolução)

### Análise

Chunks retornados (doc_id/seção): POL-001/3.5. Custos de devolução, FAQ/Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?", POL-001/3.3. Procedimento de devolução, PROC-042/3. Prazo de entrega para frete especial, FAQ/Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?"

✅ **Todos os chunks esperados foram recuperados.**


---

## Pergunta 2: "Posso devolver carga perigosa?"

### Chunks recuperados

| Rank | Score | Fonte | Seção | Preview |
|------|-------|-------|-------|---------|
| 1 | 0.3917 | FAQ-atendimento.md | Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?" | ## Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?"… |
| 2 | 0.4275 | FAQ-atendimento.md | Item 22 — "Cliente quer saber sobre seguro de carga. O que falar?" | ## Item 22 — "Cliente quer saber sobre seguro de carga. O que falar?"  A NovaTec… |
| 3 | 0.4540 | FAQ-atendimento.md | Item 38 — "Cliente quer saber a política para carga que chegou danificada." | ## Item 38 — "Cliente quer saber a política para carga que chegou danificada."  … |
| 4 | 0.4824 | FAQ-atendimento.md | Item 32 — "Pode enviar carga perigosa com frete expresso?" | ## Item 32 — "Pode enviar carga perigosa com frete expresso?"  Sim, mas precisa … |
| 5 | 0.4917 | PROC-042-frete-especial-v1.md | 4. Condições especiais | ## 4. Condições especiais  - Cargas acima de 5.000kg requerem aprovação prévia d… |

### Chunks esperados (gabarito)

- POL-001 (Seção 3.2 — Exceções ao prazo geral)

### Chunks possíveis (relevância menor)

- FAQ Item 3
- POL-001 (Seção 3.1 — Prazo geral)

### Análise

Chunks retornados (doc_id/seção): FAQ/Item 3 — "Cliente perguntou se pode devolver carga perigosa. O que respondo?", FAQ/Item 22 — "Cliente quer saber sobre seguro de carga. O que falar?", FAQ/Item 38 — "Cliente quer saber a política para carga que chegou danificada.", FAQ/Item 32 — "Pode enviar carga perigosa com frete expresso?", PROC-042/4. Condições especiais

⚠️ **Chunks esperados não encontrados no top-5:** POL-001


---

## Pergunta 3: "Qual o SLA do cliente Gold?"

### Chunks recuperados

| Rank | Score | Fonte | Seção | Preview |
|------|-------|-------|-------|---------|
| 1 | 0.4507 | FAQ-atendimento.md | Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?" | ## Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?"  Respo… |
| 2 | 0.4508 | SLA-2024-tabela-sla-clientes.md | 5. Medição e reportes | ## 5. Medição e reportes  Os SLAs são medidos pelo sistema de chamados (Azure De… |
| 3 | 0.4626 | FAQ-atendimento.md | Item 15 — "Cliente diz que é Platinum. Existe esse tier?" | ## Item 15 — "Cliente diz que é Platinum. Existe esse tier?"  Não existe tier Pl… |
| 4 | 0.4864 | SLA-2024-tabela-sla-clientes.md | 1. Classificação de clientes | ## 1. Classificação de clientes  A NovaTech classifica seus clientes em 3 (três)… |
| 5 | 0.5340 | SLA-2024-tabela-sla-clientes.md | Cabeçalho | # SLA-2024 — Tabela de SLA por Tipo de Cliente  **Versão:** 2024.1 **Última atua… |

### Chunks esperados (gabarito)

- SLA-2024 (Seção 2 — Tabela de SLAs)

### Chunks possíveis (relevância menor)

- SLA-2024 (Seção 1 — Classificação de clientes)
- SLA-2024 (Seção 3 — Definição de incidente crítico)

### Análise

Chunks retornados (doc_id/seção): FAQ/Item 41 — "Qual a diferença entre SLA de resposta e SLA de resolução?", SLA-2024/5. Medição e reportes, FAQ/Item 15 — "Cliente diz que é Platinum. Existe esse tier?", SLA-2024/1. Classificação de clientes, SLA-2024/Cabeçalho

✅ **Todos os chunks esperados foram recuperados.**


---

## Pergunta 4: "Quanto custa o frete para 600kg para Manaus?"

### Chunks recuperados

| Rank | Score | Fonte | Seção | Preview |
|------|-------|-------|-------|---------|
| 1 | 0.4660 | PROC-042-frete-especial-v1.md | 1. Objetivo | ## 1. Objetivo  Definir a fórmula e os parâmetros para cálculo de frete especial… |
| 2 | 0.4740 | PROC-042-v2-frete-especial-revisado.md | 2. Fórmula de cálculo | ## 2. Fórmula de cálculo  O frete especial é calculado como:  Valor do frete = V… |
| 3 | 0.4742 | PROC-042-v2-frete-especial-revisado.md | 1. Objetivo | ## 1. Objetivo  Definir a fórmula e os parâmetros atualizados para cálculo de fr… |
| 4 | 0.4750 | PROC-042-frete-especial-v1.md | 2. Fórmula de cálculo | ## 2. Fórmula de cálculo  O frete especial é calculado como:  Valor do frete = V… |
| 5 | 0.4805 | FAQ-atendimento.md | Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?" | ## Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?"  Depende d… |

### Chunks esperados (gabarito)

- PROC-042-v2 (Seção 2.1 — Multiplicadores atualizados)
- PROC-042-v2 (Seção 2 — Fórmula de cálculo)

### Chunks possíveis (relevância menor)

- PROC-042 v1 (Seção 2.1 — Multiplicadores — risco de contradição)

### Análise

Chunks retornados (doc_id/seção): PROC-042/1. Objetivo, PROC-042/2. Fórmula de cálculo, PROC-042/1. Objetivo, PROC-042/2. Fórmula de cálculo, FAQ/Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?"

✅ **Todos os chunks esperados foram recuperados.**


---

## Pergunta 5: "Qual o multiplicador para o Sudeste?"

### Chunks recuperados

| Rank | Score | Fonte | Seção | Preview |
|------|-------|-------|-------|---------|
| 1 | 0.4753 | POL-001-politica-devolucao.md | 3.4. Devoluções parciais | ## 3.4. Devoluções parciais  Quando a entrega envolver múltiplos volumes, o clie… |
| 2 | 0.4904 | FAQ-atendimento.md | Item 8 — "Como funciona o frete especial?" | ## Item 8 — "Como funciona o frete especial?"  Acima de 500kg, aplica a tabela d… |
| 3 | 0.4968 | PROC-042-v2-frete-especial-revisado.md | 2.1. Multiplicadores regionais (atualizados em novembro/2023) | ## 2.1. Multiplicadores regionais (atualizados em novembro/2023)  \| Região \| Mul… |
| 4 | 0.5039 | PROC-042-frete-especial-v1.md | 2.1. Multiplicadores regionais | ## 2.1. Multiplicadores regionais  \| Região \| Multiplicador \| \|--------\|--------… |
| 5 | 0.5173 | FAQ-atendimento.md | Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?" | ## Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?"  Depende d… |

### Chunks esperados (gabarito)

- PROC-042-v2 (Seção 2.1 — Multiplicadores atualizados)

### Chunks possíveis (relevância menor)

- PROC-042 v1 (Seção 2.1 — Multiplicadores — contradição: 1.0 vs 1.1)

### Análise

Chunks retornados (doc_id/seção): POL-001/3.4. Devoluções parciais, FAQ/Item 8 — "Como funciona o frete especial?", PROC-042/2.1. Multiplicadores regionais (atualizados em novembro/2023), PROC-042/2.1. Multiplicadores regionais, FAQ/Item 27 — "O tracking mostra 'em trânsito' há 5 dias. O que faço?"

✅ **Todos os chunks esperados foram recuperados.**
