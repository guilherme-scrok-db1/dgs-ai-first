# Análise Técnica de Viabilidade — Assistente RAG NovaTech

**Autor:** Desenvolvedor Sênior — Pipeline RAG  
**Data:** 01/06/2026  
**Projeto:** Assistente de IA para Atendimento NovaTech  
**Status:** Análise inicial para validação com Tech Lead

---

## 1. Desafios por Tipo de Fonte

### 1.1. PDFs com tabelas complexas (15+ colunas)

**(a) Desafio para o pipeline de RAG:**  
Tabelas de frete da NovaTech com 15+ colunas (ex: região × faixa de peso × tipo de carga × tier de cliente) perdem estrutura quando extraídas por parsers PDF convencionais. A linearização (converter tabela para texto sequencial) destrói a relação coluna-valor. Um parser como PyMuPDF ou pdfplumber pode extrair o texto, mas a associação "multiplicador 1.3 pertence à região Sul na v2" se perde se o chunking cortar a tabela no meio.

**(b) Impacto na qualidade das respostas:**  
Se o chunk contém apenas parte da tabela (ex: as primeiras 8 colunas de uma tabela de multiplicadores regionais), o modelo pode responder com dados incompletos ou associar um multiplicador à região errada. No caso concreto da NovaTech: se a tabela de multiplicadores da PROC-042-v2 for cortada entre "Centro-Oeste 1.4" e "Nordeste 1.5", e o atendente perguntar sobre o Norte, o modelo pode alucinar um valor ou responder "informação não disponível" mesmo tendo a tabela na base.

**(c) Estratégia de tratamento:**  
- **Extração estruturada:** Usar Azure AI Document Intelligence (form recognizer) com modelo `prebuilt-layout` para preservar a estrutura tabular. Representar tabelas em formato Markdown dentro dos chunks, mantendo cabeçalhos em cada chunk.
- **Chunking atômico para tabelas:** Cada tabela completa deve ser um chunk único, mesmo que exceda o tamanho padrão de 500 tokens. Tabelas muito grandes (>1.000 tokens) devem ser divididas por segmento lógico (ex: por região), mas cada sub-chunk deve conter os cabeçalhos da tabela replicados.
- **Metadata enriquecida:** Adicionar metadata indicando `tipo: tabela`, `documento: PROC-042-v2`, `seção: multiplicadores regionais` para melhorar o retrieval semântico.

---

### 1.2. PDFs escaneados (~15% da base, OCR necessário)

**(a) Desafio para o pipeline de RAG:**  
~120 documentos (15% de 800) exigem OCR antes da indexação. OCR introduz erros de reconhecimento — especialmente em: números com vírgulas (ex: "1,5" pode virar "1.5" ou "15"), caracteres acentuados (frequentes em português), e tabelas onde o alinhamento espacial é crítico para associar dados. Documentos escaneados em baixa resolução ou com carimbos/anotações manuscritas degradam ainda mais a qualidade.

**(b) Impacto na qualidade das respostas:**  
Erros de OCR se propagam para os embeddings e para o texto recuperado. Se "R$ 500.000" for lido como "R$ 500 000" ou "R$ 5OO.OOO" (com letras O), o retrieval semântico pode não associar esse chunk a perguntas sobre valores de contrato. Mais grave: um multiplicador "1.5" lido como "15" ou "1,5" (com vírgula) pode gerar respostas financeiramente incorretas.

**(c) Estratégia de tratamento:**  
- **Azure AI Document Intelligence com modelo `prebuilt-read`** para OCR de alta qualidade com suporte a português brasileiro.
- **Pipeline de validação pós-OCR:** Verificação automatizada de padrões numéricos (valores monetários, multiplicadores, prazos) com regex para detectar erros comuns. Documentos com confidence score < 0.85 devem ser sinalizados para revisão humana.
- **Priorização:** Identificar quais dos ~120 documentos OCR são consultados frequentemente (análise de chamados históricos). Priorizar revisão humana dos 20% mais acessados.
- **Fallback:** Para documentos OCR de baixa qualidade, manter link para o PDF original na resposta para que o atendente possa verificar visualmente.

---

### 1.3. Wiki Confluence com links internos e macros

**(a) Desafio para o pipeline de RAG:**  
Páginas Confluence têm semântica distribuída: uma página sobre "Frete Especial" pode linkar para "Tabela de Regiões" e "Política de Descontos" sem repetir o conteúdo. Se o pipeline ingere cada página isoladamente, o chunk perde contexto referenciado. Macros customizadas (ex: `{status}`, `{expand}`, `{jira}`) renderizam conteúdo dinâmico que não está no texto-fonte.

**(b) Impacto na qualidade das respostas:**  
O assistente pode dar respostas incompletas porque o chunk recuperado diz "conforme a tabela de multiplicadores (link)" sem conter os multiplicadores em si. Ou pode ignorar conteúdo dentro de macros `{expand}` que contém exceções críticas.

**(c) Estratégia de tratamento:**  
- **Ingestão via Confluence REST API** (não via export HTML): Usar endpoint `/rest/api/content/{id}?expand=body.storage` para obter o conteúdo renderizado, e resolver links internos durante a ingestão.
- **Dereference de links:** Para links internos dentro da mesma seção temática, expandir o conteúdo linkado inline (até 1 nível de profundidade) antes do chunking.
- **Processamento de macros:** Mapear macros conhecidas para texto equivalente. `{status:colour=Green|title=Ativo}` → "[Status: Ativo]". Macros `{expand}` devem ter seu conteúdo incluído no chunk.
- **Atualização incremental:** Como a wiki atualiza semanalmente, implementar webhook Confluence → re-ingestão seletiva (apenas páginas modificadas).

---

### 1.4. Planilhas com fórmulas interdependentes

**(a) Desafio para o pipeline de RAG:**  
As 50 planilhas XLSX contêm fórmulas que referenciam outras abas ou outras planilhas (ex: `=VLOOKUP(A2, 'Tabela Base'!A:C, 3, FALSE) * Multiplicadores!B5`). Ingerir apenas os valores calculados perde a lógica de cálculo. Ingerir as fórmulas produz texto ininteligível para o modelo. Algumas células podem ter valores condicionais que mudam mensalmente.

**(b) Impacto na qualidade das respostas:**  
Se a planilha de frete-base tem fórmulas que referenciam a tabela de multiplicadores, e o pipeline ingere apenas valores estáticos, o assistente terá dados de um ponto no tempo que podem estar desatualizados. Pior: se a fórmula resolve para um valor diferente dependendo do mês, o chunk terá um valor congelado sem indicar a temporalidade.

**(c) Estratégia de tratamento:**  
- **Ingestão de valores calculados (não fórmulas):** Usar `openpyxl` com `data_only=True` para capturar os valores resolvidos.
- **Contextualização temporal:** Cada ingestão deve registrar a data de captura como metadata do chunk: `{fonte: frete-base-202401.xlsx, capturado_em: 2024-01-15}`.
- **Estruturação semântica:** Converter tabelas para formato narrativo quando possível. Ex: ao invés de ingerir uma linha da planilha como `"Sul | 1.3 | 1.0 | 1.15 | 1.4"`, gerar: "Região Sul: multiplicador 1.3. Fator de peso: 1.0 (500-1000kg), 1.15 (1001-3000kg), 1.4 (>3000kg)."
- **Re-ingestão mensal automatizada:** Agendar pipeline para recalcular e re-indexar planilhas no mesmo ciclo de atualização do Comercial.

---

## 2. Estimativa de Tokens da Base

### 2.1. Cálculo passo a passo

**Regra de conversão:** ~0,75 palavras por token → 1 palavra ≈ 1,33 tokens

#### PDFs do SharePoint
- Quantidade: 800 documentos
- Páginas por documento: ~10
- Palavras por página: ~500
- **Total de palavras:** 800 × 10 × 500 = **4.000.000 palavras**
- **Total de tokens:** 4.000.000 ÷ 0,75 = **~5.333.333 tokens**

#### Wiki Confluence
- Quantidade: 400 páginas
- Palavras por página: ~1.500
- **Total de palavras:** 400 × 1.500 = **600.000 palavras**
- **Total de tokens:** 600.000 ÷ 0,75 = **~800.000 tokens**

#### Planilhas XLSX
- Quantidade: 50 planilhas
- Estimativa conservadora: ~200 linhas × 10 colunas × 3 palavras por célula = 6.000 palavras/planilha
- Considerando múltiplas abas (~3 abas por planilha): 6.000 × 3 = 18.000 palavras/planilha
- **Total de palavras:** 50 × 18.000 = **900.000 palavras**
- **Total de tokens:** 900.000 ÷ 0,75 = **~1.200.000 tokens**

#### Resumo consolidado

| Fonte | Palavras | Tokens estimados |
|-------|----------|-----------------|
| PDFs SharePoint | 4.000.000 | ~5.333.000 |
| Wiki Confluence | 600.000 | ~800.000 |
| Planilhas XLSX | 900.000 | ~1.200.000 |
| **TOTAL** | **5.500.000** | **~7.333.000 tokens** |

### 2.2. Implicações

- A base total (~7,3M tokens) **não cabe** numa única janela de contexto de 128K tokens do GPT-4o.
- Fator de compressão necessário: 7.333.000 ÷ 128.000 ≈ **57×** — o pipeline precisa selecionar ~1,7% da base por query.
- Isso confirma que RAG é **obrigatório** (não é viável uma abordagem "jogue tudo no contexto").
- Com chunks de 500 tokens, a base terá **~14.666 chunks** no índice vetorial.

---

## 3. Análise de Orçamento de Contexto

### 3.1. Distribuição do orçamento (128K tokens GPT-4o)

| Componente | Tokens | % do total |
|-----------|--------|-----------|
| System prompt + instruções do assistente | ~2.000 | 1,6% |
| Histórico de conversa (sessão Teams) | ~1.000–5.000 | 0,8%–3,9% |
| Chunks recuperados (espaço disponível) | ~121.000–125.000 | 94,5%–97,6% |
| Margem para resposta gerada | ~2.000–4.000 | 1,6%–3,1% |

### 3.2. Quantos chunks cabem?

**Cenário conservador** (histórico longo de 5K tokens):
- Espaço disponível para chunks: 128.000 - 2.000 - 5.000 - 4.000 = **117.000 tokens**
- Chunks de 500 tokens: 117.000 ÷ 500 = **234 chunks cabem**

**Cenário típico** (histórico curto de 1K tokens):
- Espaço: 128.000 - 2.000 - 1.000 - 3.000 = **122.000 tokens**
- Chunks: 122.000 ÷ 500 = **244 chunks**

### 3.3. Mas "cabe" ≠ "deve usar"

O fato de 234 chunks caberem na janela **não significa que devemos usar todos**. Eis os trade-offs:

#### Efeito "Lost in the Middle"
Pesquisas (Liu et al., 2023) demonstram que LLMs têm desempenho degradado quando a informação relevante está posicionada no meio de um contexto longo. A performance segue um padrão em "U": informação no início e no final do contexto é melhor utilizada.

**Impacto para NovaTech:** Se enviarmos 234 chunks e o chunk relevante (ex: multiplicador regional da PROC-042-v2) estiver na posição 117/234, a probabilidade de o modelo ignorá-lo ou misturá-lo com informação de outros chunks aumenta significativamente.

#### Competição por atenção
Com muitos chunks, chunks parcialmente relevantes (ex: PROC-042 v1 quando a pergunta é sobre valores atuais) competem com chunks corretos (PROC-042 v2), aumentando risco de respostas que misturam versões.

#### Recomendação de quantidade

| Cenário | Chunks recomendados | Justificativa |
|---------|-------------------|---------------|
| Pergunta simples e direta | 3–5 chunks | "Qual o prazo de devolução?" → poucos chunks focados evitam ruído |
| Pergunta multi-domínio | 8–12 chunks | "Prazo + frete + SLA" → precisa cobrir múltiplos documentos |
| Máximo recomendado | 15–20 chunks | Além disso, o efeito "lost in the middle" degrada qualidade |

**Tokens efetivamente usados:** 5–20 chunks × 500 tokens = **2.500–10.000 tokens** de contexto documental por query. Isso é ~2–8% da janela — muito menos que o máximo teórico, mas com qualidade muito superior.

### 3.4. Estratégia de posicionamento

Para mitigar "lost in the middle":
1. **Chunks mais relevantes primeiro** (ranking por score de similaridade coseno)
2. **Chunk mais relevante duplicado no final** (técnica "bookend")
3. **Separadores explícitos** entre chunks com metadata: `[Fonte: PROC-042-v2, Seção 2.1, Vigência: a partir de 01/12/2023]`

---

## 4. Recomendação de Estratégia de Chunking

### 4.1. Estratégia proposta: Chunking Semântico Hierárquico

Dados os tipos de pergunta dos atendentes NovaTech, recomendo uma estratégia **híbrida** com 3 níveis:

#### Nível 1 — Chunks por seção lógica (padrão)
- Dividir documentos em chunks por seção/subseção (H2/H3 do documento).
- Tamanho-alvo: **300–600 tokens** por chunk.
- Overlap: **50 tokens** entre chunks adjacentes (para manter contexto de transição).
- Cada chunk inclui: título do documento + número da seção como prefixo.

**Justificativa:** As perguntas dos atendentes são tipicamente sobre um tópico específico ("prazo de devolução", "multiplicador do Nordeste", "SLA do Gold"). Chunks por seção alinham com a granularidade das perguntas.

#### Nível 2 — Chunks atômicos para tabelas e regras
- Tabelas de multiplicadores, SLAs, e regras numéricas: chunk único por tabela completa.
- Incluir cabeçalhos e contexto (título da seção + vigência).
- Tamanho: variável (pode exceder 600 tokens se necessário para manter integridade).

**Justificativa para NovaTech:** A tabela de multiplicadores da PROC-042-v2 tem 5 linhas × 2 colunas = ~100 tokens. Deve ser um chunk único e indivisível. Se a tabela de SLA (7 métricas × 3 tiers) for cortada no meio, o modelo pode confundir SLA de Gold com Silver.

#### Nível 3 — Parent-child com metadata de versão
- Para documentos com versões conflitantes (PROC-042 v1 vs v2), implementar:
  - **Parent chunk:** Resumo do documento com data de vigência e status.
  - **Child chunks:** Seções individuais com herança da metadata do parent.
  - **Metadata obrigatória:** `{versão, data_emissão, vigência_inicio, status}`

**Justificativa:** O caso concreto da NovaTech com PROC-042 v1 (multiplicador Sudeste = 1.0) e v2 (multiplicador Sudeste = 1.1) exige que o pipeline saiba **qual versão entregar**. A regra de negócio (seção 5 da v2): "chamados a partir de 01/12/2023 usam v2" deve ser encodada como filtro no retrieval, não deixada para o LLM decidir.

### 4.2. Tratamento específico para documentos contraditórios

**Problema concreto:** Se o retriever retorna chunks de ambas as versões da PROC-042 (v1: Sul=1.2 e v2: Sul=1.3), o LLM pode:
- Escolher arbitrariamente uma versão
- Misturar valores das duas (ex: usar fator de peso da v1 com multiplicador da v2)
- Apresentar ambos sem indicar qual é vigente

**Solução em 3 camadas:**

1. **Na ingestão:** Adicionar metadata de vigência a cada chunk:
   ```
   PROC-042 v1: vigencia_fim: 2023-11-30
   PROC-042 v2: vigencia_inicio: 2023-12-01
   ```

2. **No retrieval:** Implementar filtro temporal no Azure AI Search. Query padrão: `vigencia_fim >= data_atual OR vigencia_fim IS NULL`. Isso exclui chunks obsoletos do resultado.

3. **No prompt do LLM:** Instrução explícita no system prompt:
   ```
   Quando múltiplas versões do mesmo documento forem apresentadas, use SEMPRE a versão mais recente (maior número de versão ou data de emissão mais recente), a menos que o contexto indique explicitamente que a versão anterior se aplica (ex: chamados em transição).
   ```

### 4.3. Parâmetros finais recomendados

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Tamanho de chunk (padrão) | 400 tokens (~300 palavras) | Alinhado com seções típicas dos docs NovaTech |
| Overlap | 50 tokens | Mantém contexto sem duplicação excessiva |
| Top-K retrieval (padrão) | 5 | Cobertura suficiente para perguntas simples |
| Top-K retrieval (multi-domínio) | 10–12 | Detectado via classificação de intent |
| Modelo de embedding | `text-embedding-3-large` (Azure OpenAI) | Melhor performance em português para domínio técnico |
| Índice vetorial | Azure AI Search (HNSW) | Já disponível na stack Microsoft da NovaTech |
| Re-ranker | Semantic ranker do Azure AI Search | Reordena top-50 para top-K final, mitiga "lost in the middle" |
| Estratégia de busca | Híbrida (vetorial + keyword BM25) | Keywords críticas para números exatos: "PROC-042", "Gold", "7 dias úteis" |

### 4.4. Estimativa de chunks na base final

| Fonte | Tokens totais | Chunks (~400 tokens, 50 overlap) |
|-------|--------------|----------------------------------|
| PDFs SharePoint | 5.333.000 | ~15.237 |
| Wiki Confluence | 800.000 | ~2.285 |
| Planilhas XLSX | 1.200.000 | ~3.428 |
| **TOTAL** | **7.333.000** | **~20.950 chunks** |

---

## 5. Conclusão e Viabilidade

### Veredicto: **Viável, com ressalvas técnicas**

O projeto é tecnicamente viável com a stack Azure AI (Document Intelligence + Azure OpenAI + Azure AI Search), mas o sucesso depende criticamente de:

1. **Qualidade da ingestão** — PDFs com tabelas e OCR são o maior risco técnico. Requer investimento em pipeline de pré-processamento robusto com validação humana para os ~120 documentos OCR.

2. **Governança de versões** — A contradição PROC-042 v1/v2 é sintomática. Com 800+ documentos atualizados por 3 áreas sem processo unificado, este problema vai se repetir. O pipeline precisa de metadata de vigência obrigatória na ingestão.

3. **Calibração de retrieval** — O trade-off de chunks (cobertura vs foco) exige tuning iterativo com perguntas reais dos atendentes. Recomendo fase de piloto com 50 perguntas representativas antes do go-live.

### Riscos que escalam para o Tech Lead

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Tabelas corrompidas no chunking | Alta | Respostas com valores financeiros incorretos | Chunking atômico + validação pós-ingestão |
| OCR com erros numéricos | Média | Multiplicadores/prazos errados | Confidence threshold + revisão humana prioritária |
| Contradição entre versões | Alta (já confirmada) | Respostas misturando regras de versões diferentes | Filtro temporal no retrieval + metadata de vigência |
| "Lost in the middle" em perguntas complexas | Média | Respostas incompletas para multi-domínio | Limitar top-K + re-ranking + bookend positioning |
| Atualização mensal sem re-ingestão | Alta | Base desatualizada, respostas incorretas | Pipeline automatizado de re-ingestão com diff detection |

---

*Documento preparado para revisão do Tech Lead. Próximo passo: validar estratégia de chunking com PoC usando os 5 documentos-chave (POL-001, PROC-042 v1/v2, SLA-2024, FAQ-Atendimento) antes de escalar para a base completa.*
