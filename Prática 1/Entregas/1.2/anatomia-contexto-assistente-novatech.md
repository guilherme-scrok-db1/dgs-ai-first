# Anatomia de Contexto — Assistente NovaTech

> **Versão:** 1.0  
> **Data:** 01/06/2026  
> **Modelo:** GPT-4o (128K context window)  
> **Encoding:** cl100k_base (~4 caracteres/token para português)

---

## 1. Mapa de Componentes do Contexto

| # | Componente | Tipo | Estimativa de Tokens | % do Total | Descrição | Frequência de Mudança |
|---|---|---|---|---|---|---|
| 1 | System Prompt (identidade + regras) | Estático | ~1.800 | 1,4% | Seções 1-4 do prompt: identidade, regras invioláveis, hierarquia de fontes, formato | Raro — apenas em releases do assistente |
| 2 | Instruções de uso de chunks | Estático | ~800 | 0,6% | Seção 5: como processar e avaliar chunks do RAG | Raro — ajustes após avaliações de qualidade |
| 3 | Comportamento de fallback | Estático | ~600 | 0,5% | Seção 6: tabela de encaminhamentos, templates de fallback | Mensal — quando mudam áreas/contatos |
| 4 | Template de contexto dinâmico (estrutura XML) | Estático | ~200 | 0,2% | Tags XML que delimitam o contexto dinâmico | Raro |
| 5 | Metadados do atendente/sessão | Dinâmico | ~50 | <0,1% | Nome, canal, sessão, timestamp | A cada query |
| 6 | Dados do cliente (tier, contrato) | Dinâmico | ~100 | <0,1% | Tier, ID contrato, vigência, volume mensal | A cada query (varia por cliente) |
| 7 | Chunks recuperados pelo RAG | Dinâmico | ~2.000–6.000 | 1,6%–4,7% | Top-K chunks do Azure AI Search (tipicamente 3-8 chunks) | A cada query (varia por pergunta) |
| 8 | Pergunta do atendente | Dinâmico | ~50–200 | <0,2% | A pergunta atual em linguagem natural | A cada query |
| 9 | Histórico de conversa (sessão Teams) | Dinâmico (crescente) | ~500–8.000 | 0,4%–6,3% | Pares pergunta/resposta anteriores na mesma sessão | Cresce a cada turno |
| 10 | Output reservado (resposta do modelo) | Reservado | ~500–1.000 | 0,4%–0,8% | Espaço reservado para geração da resposta | A cada query |

---

## 2. Orçamento de Tokens

### 2.1. Capacidade Total

| Parâmetro | Valor |
|---|---|
| Context window (GPT-4o) | **128.000 tokens** |
| Max output tokens (configurável) | **1.000 tokens** |
| **Orçamento disponível para input** | **127.000 tokens** |

### 2.2. Alocação por Camada

| Camada | Componentes | Orçamento Alocado | % do Total | Prioridade de Corte |
|---|---|---|---|---|
| **Estática (fixa)** | System prompt + instruções + fallback + template | **3.400 tokens** | 2,7% | Nunca cortado |
| **Semi-estática (sessão)** | Metadados atendente + dados cliente | **150 tokens** | 0,1% | Nunca cortado |
| **Dinâmica — Chunks RAG** | Top-K chunks recuperados | **6.000 tokens (máx)** | 4,7% | Reduzir K se necessário |
| **Dinâmica — Pergunta** | Pergunta atual | **200 tokens (máx)** | 0,2% | Nunca cortado |
| **Dinâmica — Histórico** | Conversas anteriores da sessão | **8.000 tokens (máx)** | 6,3% | Primeiro a ser truncado |
| **Reserva de output** | Geração da resposta | **1.000 tokens** | 0,8% | Fixo |
| **Margem de segurança** | Buffer para variações | **2.000 tokens** | 1,6% | — |
| **TOTAL ALOCADO (caso máximo)** | — | **~20.750 tokens** | ~16% | — |
| **Headroom não utilizado** | — | **~107.250 tokens** | ~84% | — |

### 2.3. Por que não usar toda a janela?

Embora o GPT-4o tenha 128K tokens, **não devemos preencher todo o contexto**:

| Fator | Impacto |
|---|---|
| **Context rot / Lost in the middle** | Modelos perdem atenção em informações no meio de contextos muito longos. Acima de ~20K tokens de input, a qualidade de atenção a chunks específicos degrada significativamente |
| **Latência** | Mais tokens = mais tempo de processamento. Para atendimento em tempo real, manter input compacto (<20K) garante respostas em <3 segundos |
| **Custo** | GPT-4o cobra por token processado. Input inflado sem ganho de qualidade é desperdício |
| **Consistência** | Contextos menores produzem respostas mais consistentes e rastreáveis |

**Regra prática:** Manter o input total abaixo de **20.000 tokens** para operação normal, com hard limit de **30.000 tokens** em casos excepcionais (perguntas multi-domínio com histórico longo).

---

## 3. Política de Gerenciamento por Componente

### 3.1. Chunks RAG

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Top-K padrão | **5 chunks** | Balanço entre cobertura e ruído |
| Top-K máximo | **8 chunks** | Para perguntas multi-domínio |
| Tamanho máximo por chunk | **800 tokens** | Chunks maiores devem ser re-segmentados |
| Score mínimo de relevância | **0.65** | Abaixo disso, o chunk é ruído |
| Orçamento total chunks | **6.000 tokens** | Hard limit — se exceder, remover chunk de menor score |

**Risco se crescer demais:** Chunks irrelevantes diluem a atenção do modelo, aumentando chance de o modelo responder com base em chunk errado ou misturar informações de documentos diferentes.

**Mitigação:** Aplicar reranking após retrieval; filtrar por score; limitar chunks por documento-fonte (máx 3 chunks do mesmo documento).

### 3.2. Histórico de Conversa

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Turnos recentes (integrais) | **Últimos 4 turnos** | Contexto conversacional imediato |
| Turnos anteriores | **Resumidos em 1 parágrafo** | Manter referência sem ocupar espaço |
| Orçamento total histórico | **8.000 tokens** | Hard limit |
| Trigger de truncamento | **>6 turnos OU >6.000 tokens** | O que ocorrer primeiro |
| Estratégia de truncamento | **Sliding window + resumo** | Manter últimos 4 integrais, resumir anteriores |

**Risco se crescer demais:** Histórico longo compete com chunks RAG pela atenção do modelo. O modelo pode responder com base em informações de turnos anteriores (que podem ser de outro cliente/tema) em vez dos chunks atuais.

**Mitigação:** 
- Truncar com sliding window (manter apenas últimos N turnos integrais)
- Gerar resumo dos turnos descartados (1 parágrafo contextual)
- Em nova sessão Teams, resetar histórico

### 3.3. Dados do Cliente

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Orçamento fixo | **150 tokens** | Dados estruturados, previsíveis |
| Campos obrigatórios | tier, contrato_id | Necessários para aplicar SLA correto |
| Campos opcionais | vigência, operações/mês | Úteis para desconto de volume |

**Risco:** Mínimo — tamanho fixo e previsível. O risco é dados AUSENTES (não saber o tier do cliente), não excesso.

---

## 4. Cenários de Orçamento

### 4.1. Query Simples (caso típico — 80% das queries)

```
System prompt estático:                3.400 tokens
Metadados + dados cliente:               150 tokens
Chunks RAG (3 chunks × ~500 tok):      1.500 tokens
Pergunta:                                 50 tokens
Histórico (2 turnos anteriores):         800 tokens
Reserva output:                          500 tokens
─────────────────────────────────────────────────
TOTAL:                                ~6.400 tokens
```

**Headroom:** ~121.600 tokens livres. Operação confortável, resposta rápida.

### 4.2. Query Complexa Multi-Domínio (15% das queries)

```
System prompt estático:                3.400 tokens
Metadados + dados cliente:               150 tokens
Chunks RAG (7 chunks × ~700 tok):      4.900 tokens
Pergunta:                                150 tokens
Histórico (5 turnos):                  4.000 tokens
Reserva output:                        1.000 tokens
─────────────────────────────────────────────────
TOTAL:                               ~13.600 tokens
```

**Headroom:** ~114.400 tokens livres. Ainda confortável, mas monitorar latência.

### 4.3. Sessão Longa sem Truncamento (edge case — 5%)

```
System prompt estático:                3.400 tokens
Metadados + dados cliente:               150 tokens
Chunks RAG (8 chunks × ~800 tok):      6.400 tokens
Pergunta:                                200 tokens
Histórico (12 turnos, sem truncar):   12.000 tokens
Reserva output:                        1.000 tokens
─────────────────────────────────────────────────
TOTAL:                               ~23.150 tokens
```

**⚠️ Excede o target de 20K.** Trigger de truncamento DEVE ativar neste ponto.

Após truncamento (resumo de turnos 1-8 + turnos 9-12 integrais):
```
Histórico truncado:                    5.500 tokens
TOTAL ajustado:                      ~16.650 tokens  ✓
```

---

## 5. Limites Práticos e Recomendações

### 5.1. Limite de Chunks por Query

| Cenário | Chunks Máximos | Justificativa |
|---|---|---|
| Query simples (1 tema) | 3–5 | Suficiente para cobrir 1 documento + FAQ complementar |
| Query multi-domínio (2-3 temas) | 6–8 | Necessário para cobrir devolução + frete + SLA |
| Hard limit absoluto | 8 | Acima de 8 chunks, qualidade de atenção degrada |

### 5.2. Quando Truncar Histórico

| Condição | Ação |
|---|---|
| Histórico > 6 turnos | Resumir turnos 1 a (N-4), manter últimos 4 integrais |
| Histórico > 6.000 tokens | Truncar independente do número de turnos |
| Mudança de tema/cliente na sessão | Resetar histórico (nova "sub-sessão" lógica) |
| Input total > 20.000 tokens | Truncar histórico primeiro, depois reduzir K de chunks |

### 5.3. Ordem de Corte (quando contexto excede orçamento)

Quando o input total precisa ser reduzido, cortar nesta ordem:

| Prioridade de Corte | Componente | Estratégia |
|:---:|---|---|
| 1 (cortar primeiro) | Histórico de conversa | Sliding window + resumo |
| 2 | Chunks de baixo score (<0.70) | Remover do contexto |
| 3 | Chunks do FAQ (tipo=informal) | Remover se há chunks normativos suficientes |
| 4 | Chunks excedentes (>5) | Manter apenas Top-5 por score |
| 5 (nunca cortar) | System prompt + dados cliente + pergunta | Invariável |

---

## 6. Riscos de Contexto e Mitigações

| Risco | Descrição | Impacto | Mitigação |
|---|---|---|---|
| **Context rot** | Informação relevante "perdida" no meio de contexto longo | Modelo ignora chunk importante, responde com base em knowledge prévio | Manter contexto <20K; posicionar chunks relevantes no início e fim |
| **Conflito de versão** | Chunks de PROC-042 v1 e v2 no mesmo contexto | Modelo mistura multiplicadores de versões diferentes | Hierarquia de fontes no prompt + reranker que priorize versão mais recente |
| **Chunk poisoning** | Chunk do FAQ contradiz documento normativo | Modelo usa informação informal como se fosse oficial | Tag de tipo no chunk (`informal` vs `normativo`) + instrução explícita de hierarquia |
| **Histórico como ruído** | Resposta anterior errada no histórico influencia nova resposta | Modelo repete erro anterior em vez de consultar chunks atuais | Instrução de que chunks atuais sempre têm prioridade sobre histórico |
| **Pergunta multi-hop** | Pergunta requer combinação de informações que nenhum chunk individual contém | Modelo infere/alucina a conexão entre documentos | Instrução de não criar regras compostas; fallback para escalação |
| **Tier desconhecido** | Dados do cliente não disponíveis no momento da query | Modelo assume tier ou responde genericamente | Instrução para perguntar ao atendente; não assumir |

---

## 7. Métricas de Monitoramento em Produção

| Métrica | Threshold de Alerta | Ação |
|---|---|---|
| Tokens de input médio por query | > 15.000 | Investigar: histórico longo? Chunks demais? |
| % queries com truncamento de histórico | > 30% | Considerar resumo mais agressivo ou sessões mais curtas |
| % queries com fallback (sem resposta) | > 15% | Gaps na base de conhecimento — alimentar novos documentos |
| % respostas sem citação de fonte | > 5% | System prompt não está sendo seguido — revisar |
| Score médio de chunks utilizados | < 0.70 | Qualidade de embeddings/chunking precisa revisão |
| Latência P95 da resposta completa | > 5s | Reduzir contexto ou otimizar pipeline |

---

## 8. Diagrama de Composição do Contexto

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT WINDOW (128K tokens)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  CAMADA ESTÁTICA (~3.400 tokens)                        │     │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │     │
│  │  │ Identidade  │ │ Regras       │ │ Hierarquia      │  │     │
│  │  │ & Domínio   │ │ Invioláveis  │ │ de Fontes       │  │     │
│  │  └─────────────┘ └──────────────┘ └─────────────────┘  │     │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │     │
│  │  │ Formato de  │ │ Instruções   │ │ Fallback        │  │     │
│  │  │ Resposta    │ │ de Chunks    │ │                 │  │     │
│  │  └─────────────┘ └──────────────┘ └─────────────────┘  │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  CAMADA DINÂMICA (~3.000–17.000 tokens)                 │     │
│  │                                                          │     │
│  │  ┌──────────────────┐  ┌─────────────────────────────┐  │     │
│  │  │ Dados Cliente     │  │ Histórico (sliding window)  │  │     │
│  │  │ ~150 tok          │  │ ~500–8.000 tok              │  │     │
│  │  └──────────────────┘  └─────────────────────────────┘  │     │
│  │                                                          │     │
│  │  ┌───────────────────────────────────────────────────┐   │     │
│  │  │ Chunks RAG (Top-K, ordenados por relevância)      │   │     │
│  │  │ ~1.500–6.000 tok                                  │   │     │
│  │  │ ┌─────────┐┌─────────┐┌─────────┐┌─────────┐    │   │     │
│  │  │ │Chunk 1  ││Chunk 2  ││Chunk 3  ││ ... K   │    │   │     │
│  │  │ │score:0.9││score:0.8││score:0.7││         │    │   │     │
│  │  │ └─────────┘└─────────┘└─────────┘└─────────┘    │   │     │
│  │  └───────────────────────────────────────────────────┘   │     │
│  │                                                          │     │
│  │  ┌──────────────────────────────────────────────────┐    │     │
│  │  │ Pergunta do Atendente (~50–200 tok)              │    │     │
│  │  └──────────────────────────────────────────────────┘    │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  RESERVA DE OUTPUT (~1.000 tokens)                      │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  HEADROOM NÃO UTILIZADO (~107K tokens)                  │     │
│  │  Mantido intencionalmente vazio para evitar context rot  │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Resumo Executivo

| Pergunta | Resposta |
|---|---|
| Orçamento total disponível | 128.000 tokens (127.000 para input) |
| Alocação para partes estáticas | ~3.400 tokens (2,7%) |
| Sobra para partes dinâmicas | ~123.600 tokens |
| Target operacional de input | < 20.000 tokens |
| Limite prático de chunks por query | 5 (padrão), 8 (máximo absoluto) |
| Quando truncar histórico | > 6 turnos OU > 6.000 tokens |
| Estratégia de truncamento | Sliding window (últimos 4) + resumo dos anteriores |
| Principal risco de contexto | Context rot + conflito PROC-042 v1/v2 |
| Headroom mantido intencionalmente | ~84% — para qualidade, velocidade e custo |
