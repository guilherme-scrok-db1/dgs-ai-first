# Análise Técnica de Viabilidade — Assistente RAG NovaTech (FINAL)

**Autor:** Desenvolvedor Sênior — Pipeline RAG  
**Data:** 01/06/2026  
**Projeto:** Assistente de IA para Atendimento NovaTech  
**Status:** Versão consolidada após revisão técnica — pronta para validação com Tech Lead  
**Revisão:** v2.0 — incorpora feedback de revisão crítica (12 pontos endereçados)

---

## Sumário Executivo

A NovaTech (logística, 1.200 funcionários) deseja um assistente de IA que permita a 45 atendentes obter respostas fundamentadas na documentação oficial via linguagem natural, integrado a Teams + SharePoint. A base documental inclui ~800 PDFs, ~400 páginas wiki e ~50 planilhas. O volume é de 192 queries documentais/dia (60% de 320 chamados). Meta: reduzir busca de 12min para <2min/chamado.

**Veredicto:** Viável com escopo faseado. O escopo completo proposto **não cabe em 3 meses**. Recomendamos go-live parcial (MVP) em 3 meses com a base principal (PDFs texto + wiki) e expansão em fase 2 (OCR + planilhas).

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

> ⚠️ **Nota de escopo:** A validação humana de ~120 documentos OCR pode levar 2–4 semanas se depender do time da NovaTech. Recomenda-se postergar para fase 2 (ver seção 7).

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

### 1.5. [REVISADO] Hierarquia de confiabilidade das fontes

> **Seção adicionada após revisão.** O FAQ-Atendimento é explicitamente marcado como "NÃO validado por Compliance ou Operações". Tratar todas as fontes igualmente no pipeline cria risco de respostas baseadas em informação informal.

**Problema concreto:** O FAQ-45 diz "para clientes com mais de 10 fretes especiais/mês, existe desconto automático". A PROC-042-v2 diz "a partir de 8 fretes/mês". O FAQ está desatualizado. Se ambos forem recuperados, qual prevalece?

**Estratégia:**
- Implementar **metadata de confiabilidade** em cada chunk:
  - `confiabilidade: normativo` → POL, PROC, SLA (documentos formais validados)
  - `confiabilidade: informal` → FAQ-Atendimento (conhecimento prático não validado)
- No system prompt do LLM: *"Priorize SEMPRE documentos normativos (POL, PROC, SLA) sobre documentos informais (FAQ). Quando citar o FAQ, indique explicitamente: 'Segundo orientação informal do time de atendimento (não validada oficialmente)...'"*
- No re-ranker: aplicar boost de relevância para chunks com `confiabilidade: normativo` quando houver conflito.
- **Alternativa para v2:** Excluir o FAQ da base de retrieval principal e usá-lo apenas como dado para entender a linguagem dos atendentes (reformulação de queries).

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

#### [REVISADO] Planilhas XLSX — Estimativa em faixa

> **Revisado:** A estimativa original usava premissas arbitrárias (200 linhas × 10 colunas). Dado que o cenário menciona planilhas com 15+ colunas e tabelas de frete com combinações região × peso × tipo × cliente, apresentamos cenário otimista e pessimista.

| Cenário | Premissa | Palavras | Tokens |
|---------|----------|----------|--------|
| **Otimista** | 50 × 200 linhas × 10 cols × 3 palavras × 3 abas | 900.000 | ~1.200.000 |
| **Pessimista** | 50 × 1.000 linhas × 15 cols × 4 palavras × 2 abas | 6.000.000 | ~8.000.000 |
| **Estimativa adotada** | Média ponderada (mais próxima do pessimista) | 3.000.000 | ~4.000.000 |

**Justificativa para adotar cenário mais próximo do pessimista:** Planilhas de frete tipicamente têm muitas linhas (combinações de rotas). Sem acesso real aos dados, é mais seguro superestimar.

#### Resumo consolidado

| Fonte | Palavras | Tokens (otimista) | Tokens (pessimista) |
|-------|----------|-------------------|---------------------|
| PDFs SharePoint | 4.000.000 | ~5.333.000 | ~5.333.000 |
| Wiki Confluence | 600.000 | ~800.000 | ~800.000 |
| Planilhas XLSX | 900.000–6.000.000 | ~1.200.000 | ~8.000.000 |
| **TOTAL** | — | **~7.333.000** | **~14.133.000** |

**Estimativa de trabalho adotada: ~10.000.000 tokens** (cenário médio-pessimista).

### 2.2. Implicações

- A base total (~10M tokens no cenário adotado) **não cabe** numa única janela de contexto de 128K tokens do GPT-4o.
- Fator de compressão necessário: 10.000.000 ÷ 128.000 ≈ **78×** — o pipeline precisa selecionar ~1,3% da base por query.
- Isso confirma que RAG é **obrigatório** (não é viável uma abordagem "jogue tudo no contexto").
- Com chunks de ~400 tokens (tamanho recomendado), a base terá **~28.500 chunks** no índice vetorial.

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

### 3.4. [REVISADO] Cenário de conversa multi-turno

> **Seção adicionada após revisão.** A análise original ignorava o crescimento do histórico ao longo de uma sessão no Teams.

Em atendimento real, o atendente frequentemente refina a pergunta:
- **Turno 1:** "Qual o prazo de devolução?" → histórico: ~1K tokens
- **Turno 3:** "E se for carga perigosa?" → histórico: ~5K tokens (inclui Q&A anteriores)
- **Turno 5:** "E qual seria o frete para coleta reversa no Norte?" → histórico: ~12K+ tokens

**Impacto no turno 5:**
- Espaço para chunks: 128.000 - 2.000 - 12.000 - 4.000 = **110.000 tokens**
- Ainda cabem muitos chunks, mas o **custo por request** sobe proporcionalmente ao histórico.

**Mitigação obrigatória:**
- Implementar **sumarização de histórico** após o turno 3: condensar turnos anteriores em um resumo de ~500 tokens, descartando Q&A completos.
- Alternativa: **sliding window** — manter apenas os últimos 2 turnos completos + resumo dos anteriores.
- Incluir no system prompt: instrução para que o modelo use o resumo de contexto ao invés de re-ler histórico completo.

### 3.5. Estratégia de posicionamento

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
  - **Metadata obrigatória:** `{versão, data_emissão, vigência_inicio, status, confiabilidade}`

**Justificativa:** O caso concreto da NovaTech com PROC-042 v1 (multiplicador Sudeste = 1.0) e v2 (multiplicador Sudeste = 1.1) exige que o pipeline saiba **qual versão entregar**. A regra de negócio (seção 5 da v2): "chamados a partir de 01/12/2023 usam v2" deve ser encodada como filtro no retrieval, não deixada para o LLM decidir.

### 4.2. [REVISADO] Tratamento de documentos contraditórios — com reconhecimento de limitações

> **Revisado:** A versão original propunha um filtro temporal (`vigencia_fim >= data_atual`) como se a metadata já existisse. Na realidade, o cenário explicita que os documentos "não possuem indicação formal de vigência ou obsolescência" e "coexistem no SharePoint sem hierarquia clara". A metadata de vigência **precisa ser criada** — não está disponível hoje.

**Problema concreto:** Se o retriever retorna chunks de ambas as versões da PROC-042 (v1: Sul=1.2 e v2: Sul=1.3), o LLM pode:
- Escolher arbitrariamente uma versão
- Misturar valores das duas (ex: usar fator de peso da v1 com multiplicador da v2)
- Apresentar ambos sem indicar qual é vigente

**Solução em 3 camadas (com viabilidade real):**

**Camada 1 — Curadoria de vigência na ingestão (requer esforço humano):**

A metadata de vigência não existe hoje. Criá-la exige:
1. Solicitar à NovaTech uma **lista de documentos com versões múltiplas** (~5–10% da base, estimativa: 40–80 pares).
2. Para cada par, definir manualmente: qual é vigente, qual é obsoleto, se há período de transição.
3. Encodar como metadata:
   ```
   PROC-042 v1: vigencia_fim: 2023-11-30, status: obsoleto_com_transição
   PROC-042 v2: vigencia_inicio: 2023-12-01, status: vigente
   ```

**Esforço estimado:** 2–3 dias de trabalho com um analista da NovaTech que conheça os documentos. Deve ser feito durante o discovery.

**Camada 2 — Heurísticas para documentos sem curadoria (fallback):**

Para os ~90% de documentos sem versões conflitantes mapeadas:
- **Heurística de data:** Quando dois chunks do mesmo código de documento forem recuperados, priorizar o de data de emissão mais recente.
- **Heurística de nome:** Sufixos como "v2", "revisado", "atualizado" indicam versão mais recente.
- Essas heurísticas são imperfeitas mas cobrem a maioria dos casos.

**Camada 3 — Instrução no system prompt (rede de segurança):**
```
REGRA DE VERSIONAMENTO: Quando múltiplas versões do mesmo documento forem apresentadas no contexto:
1. Use SEMPRE a versão mais recente (maior número de versão ou data de emissão mais recente).
2. Se o chunk contiver uma "seção de disposições transitórias", verifique se o caso do cliente se enquadra na transição antes de aplicar a versão mais recente.
3. Se não for possível determinar qual versão é vigente, DIGA EXPLICITAMENTE ao atendente: "Existem duas versões deste procedimento. Recomendo confirmar com [setor responsável] qual se aplica."
```

**Camada 4 — Filtro no retrieval (quando metadata existir):**
- Implementar filtro no Azure AI Search: `status != 'obsoleto' OR status IS NULL`.
- Chunks com `status: obsoleto_com_transição` devem aparecer apenas se a query mencionar termos como "chamado antigo", "aberto antes de", ou indicar contexto de transição.

---

### 4.3. [REVISADO] Estratégia para perguntas cross-document

> **Seção adicionada após revisão.** A análise original mencionava "perguntas multi-domínio" com 8–12 chunks, mas não definia como o pipeline garante cobertura de múltiplos documentos.

**Problema concreto:**

Pergunta: *"Qual o custo de devolver uma carga de 600kg para o Norte?"*

Esta pergunta cruza:
- **POL-001** (seção 3.5): "desistência do cliente: frete reverso calculado com mesmos multiplicadores do frete original"
- **PROC-042-v2** (seção 2.1): multiplicador Norte = 1.8, fator de peso 1.0 (500-1000kg)

Se o retrieval semântico buscar por similaridade com a pergunta completa, o termo "custo de devolver" tem mais proximidade semântica com POL-001, e o chunk de multiplicadores regionais pode ficar abaixo do threshold do top-5.

**Estratégia: Query Decomposition + Multi-Query Retrieval**

1. **Classificação de intent:** Antes do retrieval, passar a pergunta por um LLM leve (GPT-4o-mini) com prompt:
   ```
   Classifique esta pergunta em uma ou mais categorias:
   - DEVOLUÇÃO (prazos, custos, procedimento de devolução)
   - FRETE (cálculo, multiplicadores, peso, região)
   - SLA (prazos de atendimento, tiers de cliente)
   - GERAL (outras)
   
   Se a pergunta cruza múltiplas categorias, liste todas.
   Pergunta: "{query}"
   ```

2. **Decomposição (se multi-domínio):** Gerar sub-queries especializadas:
   - Query original: "Qual o custo de devolver uma carga de 600kg para o Norte?"
   - Sub-query 1: "custos de devolução por desistência do cliente frete reverso"
   - Sub-query 2: "multiplicador regional frete especial Norte 600kg"

3. **Retrieval paralelo:** Buscar top-5 para cada sub-query e fazer union dos resultados (deduplicated). Resultado final: top-8–12 chunks cobrindo ambos os domínios.

4. **Re-ranking unificado:** Aplicar semantic ranker no conjunto combinado para garantir que os chunks mais relevantes para a pergunta original fiquem nas primeiras posições.

**Impacto na latência:** +200–500ms (uma chamada adicional ao GPT-4o-mini para classificação). Aceitável dado o ganho de qualidade.

**Quando NÃO decompor:** Perguntas simples ("Qual o prazo de devolução?") não precisam de decomposição. O classificador de intent detecta domínio único e pula a etapa.

---

### 4.4. Parâmetros finais recomendados

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

### 4.5. [REVISADO] Estratégia de fallback quando o retrieval falha

> **Seção adicionada após revisão.** A análise original não definia o comportamento do assistente quando nenhum chunk é relevante.

**Cenários de falha:**
- Pergunta sobre algo não documentado: "Frete para 300kg para Salvador?" (frete padrão < 500kg não está na base)
- Score de relevância muito baixo em todos os chunks recuperados
- Pergunta fora do domínio do assistente: "Qual o telefone do RH?"

**Estratégia:**

1. **Threshold mínimo de relevância:** Se o top-1 chunk tem score coseno < 0.72 (a calibrar durante piloto), o assistente entra em modo "sem informação suficiente".

2. **Resposta de fallback estruturada:**
   ```
   Não encontrei informação sobre [tema] na documentação disponível. 
   Isso pode significar que:
   - O assunto não está coberto pelos documentos atuais
   - A pergunta precisa ser reformulada
   
   Sugestão: encaminhe ao [setor responsável] ou consulte [fonte alternativa].
   ```

3. **Mapeamento de escalação por domínio:**

   | Domínio não coberto | Encaminhar para |
   |---------------------|-----------------|
   | Frete padrão (< 500kg) | Comercial — ramal 3200 |
   | Sinistros / carga danificada | sinistros@novatech.com.br |
   | Carga perigosa (exceções) | Gestão de Riscos — ramal 4500 |
   | Contratos e descontos especiais | Gerente de conta (Gold) ou Comercial |
   | Fora do domínio do assistente | "Não posso ajudar com esse tema" |

4. **Logging para melhoria contínua:** Toda query que ativa o fallback deve ser logada para identificar gaps documentais recorrentes. Se >5% das queries caem no fallback sobre o mesmo tema, sinalizar como gap para a NovaTech documentar.

---

### 4.6. Estimativa de chunks na base final

| Fonte | Tokens totais | Chunks (~400 tokens, 50 overlap) |
|-------|--------------|----------------------------------|
| PDFs SharePoint | 5.333.000 | ~15.237 |
| Wiki Confluence | 800.000 | ~2.285 |
| Planilhas XLSX | 4.000.000 (estimativa média) | ~11.428 |
| **TOTAL** | **~10.133.000** | **~28.950 chunks** |

---

## 5. [REVISADO] Análise de Latência

> **Seção adicionada após revisão.** A análise original não estimava latência end-to-end.

### 5.1. Pipeline end-to-end por query

| Etapa | Latência estimada | Observação |
|-------|-------------------|------------|
| Teams → Azure Function | ~100ms | Rede interna Azure |
| Classificação de intent (GPT-4o-mini) | ~200–400ms | Apenas para queries multi-domínio |
| Geração de embedding da query | ~200–500ms | `text-embedding-3-large` |
| Busca no Azure AI Search + semantic ranker | ~200–500ms | HNSW + re-ranking |
| Geração de resposta (GPT-4o) | ~2.000–8.000ms | Depende do output; streaming mitiga percepção |
| Retorno ao Teams | ~100ms | — |
| **TOTAL (pergunta simples)** | **~2,5–5 segundos** | Sem decomposição |
| **TOTAL (pergunta multi-domínio)** | **~3–9 segundos** | Com decomposição + retrieval paralelo |

### 5.2. Validação contra a meta de <2min/chamado

**Cenário típico de atendimento:**
- Atendente recebe chamado → lê contexto do cliente: ~30s
- Faz 1ª pergunta ao assistente: espera ~4s + lê resposta ~15s = ~19s
- Faz pergunta de refinamento: espera ~4s + lê resposta ~10s = ~14s
- Aplica a informação / responde ao cliente: ~30s
- **Total estimado: ~1,5–2 minutos**

**Conclusão:** A meta de <2min é atingível para perguntas simples (1–2 turnos). Para perguntas complexas (3+ turnos), pode chegar a 2,5–3min. Ainda assim, é uma melhoria de 75–85% sobre os 12min atuais.

### 5.3. Mitigações de latência

- **Streaming:** Habilitar streaming de tokens no GPT-4o. O atendente começa a ler a resposta antes de ela estar completa. Percepção de latência cai de ~5s para ~1s (tempo até o primeiro token).
- **Cache semântico:** Para perguntas repetidas (ex: "qual o prazo de devolução?" — provavelmente feita múltiplas vezes/dia), implementar cache de resposta por similaridade da query. Azure AI Search suporta caching nativo.
- **Pré-computação de embeddings:** Embeddings das queries são stateless, mas se houver padrões (mesmas perguntas com variações), um cache de embeddings reduz chamadas ao Azure OpenAI.

### 5.4. Throughput no pico

- 192 queries/dia ÷ 8h = **24 queries/hora** (média)
- Pico estimado (2× média): ~48 queries/hora = **~0,8 queries/minuto**
- Cada query ocupa recursos por ~5s → no máximo 1 query simultânea na média, 2 no pico.
- **Conclusão:** Nenhum gargalo de concorrência com essa volumetria. Um único deployment de GPT-4o é suficiente.

---

## 6. [REVISADO] Estimativa de Custo Operacional

> **Seção adicionada após revisão.**

### 6.1. Custo mensal recorrente

| Componente | Cálculo | Custo/mês (USD) |
|-----------|---------|----------------|
| **GPT-4o — input tokens** | 4.224 queries × 9.000 tokens = 38M tokens × $2,50/M | ~$95 |
| **GPT-4o — output tokens** | 4.224 queries × 750 tokens = 3,2M tokens × $10/M | ~$32 |
| **GPT-4o-mini (classificação)** | ~2.000 queries multi-domínio × 500 tokens × $0,15/M | ~$1 |
| **Azure AI Search (Standard S1)** | Índice ~29K chunks, 1 réplica | ~$250 |
| **Azure OpenAI embeddings (queries)** | 4.224 × 100 tokens × $0,13/M | ~$1 |
| **Azure Function (compute)** | Consumption plan, ~4.200 execuções/mês | ~$5 |
| **Application Insights (logs)** | ~5GB/mês de telemetria | ~$15 |
| **TOTAL MENSAL** | — | **~$400–500** |

**Custo por atendente:** ~$400 ÷ 45 = **~$9/atendente/mês** (~R$ 50/mês por atendente ao câmbio atual).

### 6.2. Custo de ingestão inicial (one-time)

| Componente | Cálculo | Custo (USD) |
|-----------|---------|-------------|
| **Document Intelligence (OCR)** | 120 docs × 10 páginas × $0,01/página | ~$12 |
| **Document Intelligence (layout)** | 800 docs × 10 páginas × $0,01/página | ~$80 |
| **Embeddings (ingestão)** | ~10M tokens × $0,13/M | ~$1,3 |
| **GPT-4o (geração de resumos parent)** | ~1.000 docs × 500 tokens output × $10/M | ~$5 |
| **TOTAL INGESTÃO** | — | **~$100–150** |

### 6.3. Custo de re-ingestão mensal

- Documentos atualizados/mês: ~50–100 (estimativa: 5–10% da base)
- Custo: proporcional → **~$10–20/mês** adicional

### 6.4. Resumo de TCO (Total Cost of Ownership)

| Período | Custo |
|---------|-------|
| Mês 0 (setup + ingestão) | ~$100–150 (one-time) + infra |
| Mês 1–12 (operação) | ~$400–500/mês |
| **Ano 1 total** | **~$5.000–6.200** |

**Comparação:** 45 atendentes × 12min/chamado × 3,2 chamados documentais/dia × R$ 25/hora = **R$ 108.000/ano** em tempo de busca manual. ROI potencial: 15–20× o custo da solução.

---

## 7. [REVISADO] Viabilidade de Prazo e Escopo Faseado

> **Seção adicionada após revisão.** O escopo técnico completo não cabe em 3 meses.

### 7.1. Escopo total mapeado vs. esforço estimado

| Componente | Esforço estimado | Dependência |
|-----------|-----------------|-------------|
| Discovery + curadoria de vigência | 2 semanas | NovaTech (lista de docs com versões) |
| Pipeline de ingestão PDFs texto (~680 docs) | 3 semanas | Document Intelligence setup |
| Pipeline de ingestão Wiki Confluence | 2 semanas | Acesso à API Confluence |
| Pipeline de ingestão planilhas | 2 semanas | Acesso à pasta de rede |
| OCR + validação humana (~120 docs) | 3–4 semanas | NovaTech (revisão manual) |
| Implementação chunking hierárquico | 2 semanas | Pipeline de ingestão pronto |
| Query decomposition + multi-query | 1,5 semanas | — |
| Integração Teams (Bot Framework) | 3 semanas | Azure Bot Service + Teams admin |
| System prompt + guardrails + fallback | 1 semana | Chunking pronto |
| Eval set + testes de qualidade | 2 semanas | Base ingerida |
| Shadow mode + piloto com atendentes | 2 semanas | Integração pronta |
| **TOTAL SEQUENCIAL** | **~23–25 semanas** | — |
| **TOTAL COM PARALELISMO (2 devs + 1 data eng)** | **~14–16 semanas** | — |

**Conclusão:** 14–16 semanas (3,5–4 meses) para escopo completo, mesmo com 3 pessoas em paralelo. **3 meses é insuficiente para tudo.**

### 7.2. Proposta de escopo faseado

#### Fase 1 — MVP (3 meses) — Go-live parcial

| Inclui | Não inclui |
|--------|-----------|
| PDFs texto (~680 docs) via Document Intelligence | PDFs escaneados (OCR) |
| Wiki Confluence (400 páginas) | Planilhas XLSX |
| Chunking hierárquico (Nível 1 + 2) | Parent-child com metadata de versão (Nível 3 completo) |
| Busca híbrida + semantic ranker | Query decomposition automática |
| Integração Teams (bot básico) | Cards adaptativos avançados |
| Curadoria de vigência para top-20 documentos críticos | Curadoria completa de toda a base |
| Fallback + escalação | Cache semântico |
| Eval set + shadow mode (1 semana) | Observabilidade completa |

**Resultado da Fase 1:** Assistente funcional cobrindo ~85% das perguntas típicas (as que dependem de PDFs e wiki). Atendentes já ganham produtividade. Gaps (planilhas, OCR) cobertos por fallback + escalação.

#### Fase 2 — Expansão (meses 4–5)

- Ingestão de planilhas com estruturação semântica
- OCR dos 120 documentos + validação humana
- Query decomposition para perguntas cross-document
- Curadoria de vigência expandida
- Cache semântico para perguntas repetidas
- Dashboard de observabilidade

#### Fase 3 — Otimização (meses 6+)

- Fine-tuning de embeddings com dados de feedback
- Parent-child completo com filtros temporais
- Análise de gaps documentais → recomendações à NovaTech
- Expansão para outros times (não apenas atendimento)

### 7.3. O que comunicar ao Tech Lead

> "O escopo técnico completo que identificamos requer ~4 meses com 3 pessoas. Para caber em 3 meses, propomos go-live com MVP que cobre PDFs + wiki (~85% dos cenários). Planilhas e OCR entram como fase 2 no mês 4–5. O risco é aceitável porque os documentos mais consultados (POL-001, PROC-042, SLA-2024) estão em PDF texto e wiki."

---

## 8. [REVISADO] Cold Start e Estratégia de Validação

> **Seção adicionada após revisão.**

### 8.1. Eval set de ouro (pré-go-live)

Usar o Mapa de Cobertura (perguntas típicas → chunks esperados) como benchmark:

| Pergunta de teste | Chunks que DEVEM ser retornados | Critério de sucesso |
|-------------------|--------------------------------|---------------------|
| "Qual o prazo de devolução?" | POL-001-A, POL-001-B | Resposta cita 7 dias úteis + exceções |
| "Qual o SLA do cliente Gold?" | SLA-2024-B, SLA-2024-A | Resposta cita 2h resposta + 24h resolução |
| "Frete para 600kg para Manaus?" | PROC-042v2-B, PROC-042v2-A | Usa multiplicador 1.8 (v2), não 1.6 (v1) |
| "Qual o SLA do cliente Platinum?" | SLA-2024-A | Responde que Platinum NÃO existe |
| "Frete para 300kg para Salvador?" | Nenhum chunk relevante | Ativa fallback, não inventa valor |

**Métrica mínima para go-live:** ≥ 80% das perguntas do eval set respondidas corretamente e com fonte verificável.

### 8.2. Shadow mode (primeiras 2 semanas pós-go-live)

1. Assistente disponível no Teams, mas atendentes são instruídos: "Use o assistente como apoio, mas **confirme** a resposta antes de repassar ao cliente."
2. Cada resposta tem botões: 👍 (correto) / 👎 (incorreto/incompleto) / ⚠️ (parcialmente correto).
3. Feedback é logado com: query + chunks retornados + resposta + avaliação do atendente.
4. Após 2 semanas, analisar: taxa de 👍, padrões de 👎 (quais tipos de pergunta falham), e decidir se promove a "modo confiável" (atendentes podem copiar direto).

### 8.3. Critérios de promoção de shadow → produção plena

- Taxa de 👍 ≥ 75% (considerando que atendentes podem não avaliar respostas fáceis)
- Taxa de 👎 em perguntas críticas (frete, SLA) < 10%
- Zero alucinações detectadas em respostas sobre valores numéricos (multiplicadores, prazos)
- Nenhum caso de mistura de versões (PROC-042 v1/v2) nos últimos 5 dias

---

## 9. [REVISADO] Considerações de Integração Teams + SharePoint

> **Seção adicionada após revisão.**

### 9.1. Arquitetura de integração

```
[Atendente no Teams] 
    → Azure Bot Framework (Bot Service)
    → Azure Function (orquestração)
        → GPT-4o-mini (classificação de intent, se necessário)
        → Azure OpenAI Embeddings (embedding da query)
        → Azure AI Search (retrieval + re-ranking)
        → GPT-4o (geração de resposta com streaming)
    → Resposta renderizada no Teams (Adaptive Card)
```

### 9.2. Premissas a validar com a NovaTech

| Premissa | Status | Impacto se falsa |
|----------|--------|-----------------|
| Todos os 45 atendentes têm acesso a todos os documentos | **A validar** | Se houver restrições por departamento, o retrieval precisa de security trimming (filtra chunks por permissão do usuário) — adiciona complexidade significativa |
| Teams admin permite instalação de bots custom | **A validar** | Se não, opção alternativa: Copilot Studio (limitações de customização) |
| Atendentes usam Teams Desktop (não mobile) | **A validar** | Mobile tem limitações de formatação em Adaptive Cards |
| Sessão de conversa é por chamado (não contínua) | **A validar** | Afeta gestão de histórico e sumarização |

### 9.3. Limitações do Teams para respostas do assistente

- **Tamanho máximo de mensagem:** ~28KB (Adaptive Card). Respostas longas precisam ser truncadas com "Ver mais".
- **Formatação:** Markdown parcial. Tabelas complexas podem não renderizar bem → preferir formato lista para SLAs e multiplicadores.
- **Streaming:** Suportado via Activity Updates no Bot Framework v4. Requer implementação específica.

---

## 10. [REVISADO] Monitoramento e Observabilidade

> **Seção adicionada após revisão.**

### 10.1. Métricas mínimas para go-live (MVP)

| Métrica | Ferramenta | Threshold de alerta |
|---------|-----------|-------------------|
| Latência end-to-end (p95) | Application Insights | > 10 segundos |
| Score médio de relevância (top-1 chunk) | Custom logging | < 0.70 (média móvel 24h) |
| % de queries que ativam fallback | Custom logging | > 20% (indica gaps documentais) |
| Taxa de erro HTTP (Azure Function) | Application Insights | > 1% |
| Feedback 👎 / total avaliados | Custom logging | > 30% |

### 10.2. Métricas para fase 2 (otimização)

- Precision@5 e Recall@5 por categoria de pergunta
- Distribuição de domínios das queries (para identificar novos padrões)
- Drift de relevância após re-ingestão de documentos
- Tempo médio de resposta ao cliente (métrica de negócio, comparar com baseline de 12min)

### 10.3. Stack de observabilidade

- **Application Insights** (já no Azure): logs de latência, erros, throughput
- **Custom telemetry:** A cada query, logar: `{query, intent_classification, chunks_returned[], chunk_scores[], response_text, response_time_ms, feedback}`
- **Dashboard Power BI** (NovaTech já tem M365): painel gerencial com métricas semanais para a diretoria

---

## 11. Riscos Consolidados

| # | Risco | Probabilidade | Impacto | Mitigação | Fase |
|---|-------|--------------|---------|-----------|------|
| 1 | Tabelas corrompidas no chunking | Alta | Valores financeiros incorretos nas respostas | Chunking atômico + validação pós-ingestão com amostragem manual | MVP |
| 2 | OCR com erros numéricos | Média | Multiplicadores/prazos errados | Confidence threshold + revisão humana dos top-20% | Fase 2 |
| 3 | Contradição entre versões de documentos | Alta (confirmada) | Respostas misturando regras de versões diferentes | Curadoria de vigência (top-20 docs) + heurísticas + instrução no prompt | MVP |
| 4 | "Lost in the middle" em perguntas complexas | Média | Respostas incompletas para multi-domínio | Limitar top-K + re-ranking + bookend + query decomposition | MVP (parcial) |
| 5 | Atualização mensal sem re-ingestão | Alta | Base desatualizada, respostas incorretas | Pipeline automatizado de re-ingestão com diff detection | MVP |
| 6 | [REVISADO] Latência percebida > expectativa do atendente | Média | Abandono da ferramenta | Streaming + cache semântico | MVP + Fase 2 |
| 7 | [REVISADO] Perguntas cross-document sem cobertura | Média | Respostas incompletas que ignoram parte da regra | Query decomposition + multi-query retrieval | Fase 2 (MVP com top-K=10 como paliativo) |
| 8 | [REVISADO] FAQ citado como fonte oficial | Alta | Atendente segue procedimento não validado | Hierarquia de confiabilidade na metadata + instrução no prompt | MVP |
| 9 | [REVISADO] Cold start — abandono nas primeiras semanas | Média | Atendentes desistem antes de feedback calibrar o sistema | Shadow mode + eval set pré-go-live + métrica mínima | MVP |
| 10 | [REVISADO] Retrieval retorna nada relevante (gap documental) | Média | LLM alucina resposta ou dá resposta vaga inútil | Threshold de relevância + fallback com escalação | MVP |
| 11 | [REVISADO] Prazo de 3 meses insuficiente para escopo completo | Alta (confirmada) | Go-live atrasado ou com qualidade comprometida | Escopo faseado: MVP em 3 meses, expansão em mês 4–5 | — |
| 12 | [REVISADO] Security trimming necessário mas não mapeado | Baixa-Média | Atendente vê info de doc restrito ou busca não retorna doc permitido | Validar com NovaTech se há restrições de acesso por perfil | Discovery |
| 13 | [REVISADO] Custo operacional não previsto em orçamento | Baixa | Projeto aprovado sem budget recorrente | Estimar ~$400–500/mês (~R$ 50/atendente) e aprovar com diretoria | Discovery |

---

## 12. Conclusão e Próximos Passos

### Veredicto: **Viável com escopo faseado**

O projeto é tecnicamente viável com a stack Azure AI (Document Intelligence + Azure OpenAI + Azure AI Search). A meta de <2min/chamado é atingível (latência estimada de 3–9s + tempo de leitura). O custo operacional é baixo (~$9/atendente/mês) com ROI potencial de 15–20×.

**Porém:** O escopo técnico completo requer ~4 meses com equipe de 3 pessoas. A recomendação é **go-live com MVP em 3 meses** (PDFs texto + wiki = ~85% dos cenários) e expansão posterior.

### Decisões que dependem do Tech Lead

1. **Confirmar equipe:** 2 devs + 1 data engineer é suficiente? Ou precisa de mais suporte para cumprir 3 meses?
2. **Aceitar escopo faseado:** MVP sem OCR e sem planilhas é aceitável para a diretoria da NovaTech?
3. **Security trimming:** Validar com NovaTech se há restrições de acesso. Se sim, adicionar 2–3 semanas ao cronograma.
4. **Curadoria de vigência:** Quem faz? NovaTech precisa dedicar 2–3 dias de um analista durante discovery.

### Próximos passos imediatos

1. PoC com os 5 documentos-chave (POL-001, PROC-042 v1/v2, SLA-2024, FAQ-Atendimento): validar chunking + retrieval + resposta em ambiente controlado.
2. Definir eval set de ouro com 20–30 perguntas representativas + respostas esperadas.
3. Validar premissas de integração Teams com IT da NovaTech.
4. Apresentar escopo faseado para aprovação da diretoria.

---

*Documento consolidado após revisão crítica. Todos os trechos marcados com [REVISADO] indicam alterações ou adições em relação à versão original da análise.*
