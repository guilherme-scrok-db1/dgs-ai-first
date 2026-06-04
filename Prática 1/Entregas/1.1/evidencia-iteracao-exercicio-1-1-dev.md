# Histórico de Iteração — Exercício 1.1 (Desenvolvedor)

## Informações
- **Data:** 01/06/2026
- **Exercício:** Análise de viabilidade técnica com fundamentos de LLM e engenharia de contexto
- **Ferramenta utilizada:** GitHub Copilot (Claude Opus 4.6)
- **Papel:** Desenvolvedor Sênior — Pipeline RAG
- **Contexto:** Projeto NovaTech — assistente de IA baseado em RAG para atendimento ao cliente

---

## Iteração 1 — Produção da Análise Técnica

### Meu prompt (input):

> Você é um desenvolvedor sênior especialista em IA generativa e pipelines de RAG. O Tech Lead do projeto pediu que você avalie a viabilidade técnica de um assistente de IA baseado em RAG para a empresa NovaTech (logística, 1.200 funcionários).
>
> ## CENÁRIO
>
> A NovaTech quer um assistente que permita a 45 atendentes fazer perguntas em linguagem natural e receber respostas fundamentadas na documentação oficial, com indicação da fonte. O assistente será integrado ao ambiente Microsoft (Teams + SharePoint).
>
> Fontes de dados:
> - SharePoint: ~800 documentos PDF/DOCX (média 10 páginas cada), atualizados mensalmente por Operações e Compliance
> - Wiki Confluence: ~400 páginas HTML (média 1.500 palavras cada), atualizadas semanalmente por TI e Comercial
> - Pasta de rede: ~50 planilhas XLSX, atualizadas mensalmente pelo Comercial
>
> Volume: 320 chamados/dia, dos quais ~60% envolvem consulta a documentação. Meta: reduzir tempo de busca de 12min para <2min por chamado.
>
> ## INFORMAÇÕES TÉCNICAS ADICIONAIS
>
> - Os PDFs do SharePoint incluem tabelas complexas (tabelas de frete com 15+ colunas), fluxogramas embutidos como imagens, e alguns documentos escaneados (~15% da base, OCR necessário).
> - A wiki do Confluence tem links internos entre páginas e usa macros customizadas.
> - As planilhas têm fórmulas interdependentes.
> - Documentos contraditórios foram identificados: duas versões do mesmo procedimento (PROC-042 v1 e v2) coexistem no SharePoint sem hierarquia clara, com multiplicadores regionais diferentes.
> - A NovaTech já tem licenças Microsoft 365 E3 e Azure AI Services disponível.
>
> ## CONCEITO DE CONTEXT ENGINEERING APLICADO A RAG
>
> O contexto que o LLM recebe a cada pergunta é limitado pela janela de contexto do modelo. A qualidade da resposta depende de:
> - Quais chunks são selecionados (relevância)
> - Quantos chunks cabem no contexto (orçamento de atenção)
> - Onde ficam posicionados no prompt (informação no meio de contextos longos é "esquecida" — efeito "lost in the middle")
> - O que mais está no contexto competindo por atenção (system prompt, histórico de conversa, instruções)
>
> ## TAREFA
>
> Produza uma análise técnica de viabilidade cobrindo obrigatoriamente:
>
> ### 1. Desafios por tipo de fonte
> Para CADA tipo abaixo, descreva: (a) o desafio específico para o pipeline de RAG, (b) como isso afeta a qualidade das respostas, (c) uma estratégia concreta de tratamento:
> - PDFs com tabelas complexas (15+ colunas)
> - PDFs escaneados (OCR necessário)
> - Wiki Confluence com links internos e macros
> - Planilhas com fórmulas interdependentes
>
> ### 2. Estimativa de tokens da base
> Calcule o tamanho aproximado total da base usando a regra ~0.75 palavras por token:
> - ~800 PDFs × 10 páginas × ~500 palavras/página
> - ~400 páginas wiki × 1.500 palavras cada
> - ~50 planilhas (estime um tamanho razoável)
> Mostre o cálculo passo a passo.
>
> ### 3. Análise de orçamento de contexto
> Considerando:
> - GPT-4o: janela de 128K tokens
> - System prompt + instruções: ~2K tokens
> - Histórico de conversa (sessão Teams): variável (~1K-5K tokens)
> - Chunks de ~500 tokens cada
>
> Calcule: quantos chunks cabem em cada query? Como isso afeta a estratégia de chunking e retrieval? Qual o trade-off entre mais chunks (mais cobertura) vs menos chunks (mais foco, menos "lost in the middle")?
>
> ### 4. Recomendação de estratégia de chunking
> Justifique a estratégia considerando:
> - O tipo de pergunta que os atendentes farão (prazos, valores de frete, regras de devolução, SLAs)
> - O efeito "lost in the middle"
> - A existência de documentos contraditórios (PROC-042 v1 vs v2)
> - A necessidade de manter tabelas e estruturas intactas
>
> ## FORMATO
>
> Estruture como um documento técnico com seções numeradas, cálculos explícitos e recomendações acionáveis. Seja específico ao domínio da NovaTech — não use recomendações genéricas.

### Resposta da IA (output):

**Arquivo gerado:** `analise-viabilidade-tecnica-rag.md`

Estrutura da resposta:

```
## 1. Desafios por Tipo de Fonte
### 1.1. PDFs com tabelas complexas (15+ colunas)
- Desafio: linearização destrói relação coluna-valor
- Impacto: modelo pode associar multiplicador à região errada
- Estratégia: Azure AI Document Intelligence + chunking atômico para tabelas

### 1.2. PDFs escaneados (~15% da base, OCR necessário)
- Desafio: erros de OCR em números e acentos
- Impacto: embeddings incorretos, valores financeiros errados
- Estratégia: Document Intelligence prebuilt-read + validação pós-OCR

### 1.3. Wiki Confluence com links internos e macros
- Desafio: semântica distribuída entre páginas linkadas
- Impacto: respostas incompletas por falta de contexto referenciado
- Estratégia: Ingestão via API REST + dereference de links + processamento de macros

### 1.4. Planilhas com fórmulas interdependentes
- Desafio: fórmulas são ininteligíveis; valores são estáticos/temporais
- Impacto: dados congelados no tempo podem estar desatualizados
- Estratégia: openpyxl data_only + contextualização temporal + re-ingestão mensal

## 2. Estimativa de Tokens da Base
- PDFs: 800 × 10 × 500 = 4M palavras → ~5,333K tokens
- Wiki: 400 × 1.500 = 600K palavras → ~800K tokens
- Planilhas: 50 × 18.000 = 900K palavras → ~1,200K tokens
- TOTAL: ~7,333,000 tokens
- Conclusão: RAG obrigatório (fator de compressão 57×)

## 3. Análise de Orçamento de Contexto
- 234 chunks cabem na janela (cenário conservador)
- Mas recomendação é usar 5–20 chunks (trade-off lost-in-the-middle)
- Estratégia de posicionamento: ranking + bookend + separadores

## 4. Recomendação de Estratégia de Chunking
- 3 níveis: seção lógica + atômico para tabelas + parent-child com versão
- Tratamento de contradições: metadata de vigência + filtro temporal + prompt
- Busca híbrida (vetorial + BM25) com semantic ranker

## 5. Conclusão: Viável, com ressalvas técnicas
- Matriz de riscos com 5 itens
```

---

## Iteração 2 — Revisão Crítica (Devil's Advocate)

### Meu prompt (input):

> Você é um revisor técnico sênior especializado em arquiteturas de RAG em produção. Abaixo está uma análise técnica de viabilidade produzida por um desenvolvedor para o projeto NovaTech (assistente de IA para atendimento ao cliente baseado em RAG, empresa de logística).
>
> ## ANÁLISE A REVISAR
> [referência ao arquivo analise-viabilidade-tecnica-rag.md]
>
> ## CONTEXTO DO PROJETO (para sua referência)
> - 800 PDFs (alguns escaneados, tabelas complexas), 400 páginas wiki, 50 planilhas
> - 320 chamados/dia, 60% com consulta a docs
> - Documentos contraditórios existentes (PROC-042 v1 vs v2 com multiplicadores diferentes)
> - Stack: Azure (GPT-4o, Azure AI Search), integração Teams + SharePoint
> - Prazo: 3 meses discovery + desenvolvimento + go-live
>
> ## SUA TAREFA
>
> Atue como devil's advocate e revisor crítico. Identifique:
>
> 1. **Estimativas otimistas demais**: A estimativa de tokens está realista? O cálculo do orçamento de contexto considera cenários pessimistas (conversas longas, perguntas multi-domínio)? Os prazos de tratamento das fontes são viáveis em 3 meses?
>
> 2. **Pontos fracos da análise**: Há algum tipo de conteúdo ou cenário que não foi considerado? A estratégia de chunking funciona para TODOS os tipos de pergunta ou há edge cases? O que acontece com perguntas que cruzam múltiplos documentos (ex: "qual o custo de devolver uma carga de 600kg para o Norte?" — cruza POL-001 + PROC-042)?
>
> 3. **Riscos não mencionados**: 
>    - E a latência? 320 chamados/dia × embedding + busca + geração.
>    - E o custo operacional mensal (tokens consumidos)?
>    - E a atualização incremental da base quando docs mudam mensalmente?
>    - E a questão de documentos que se contradizem (o pipeline sabe qual é o vigente)?
>    - E o "cold start" — o que acontece nos primeiros dias antes de ter feedback dos atendentes?
>
> 4. **Recomendações de melhoria**: Para cada ponto fraco ou risco encontrado, sugira como a análise deveria ser corrigida ou complementada.
>
> ## FORMATO
> Estruture sua revisão em:
> - Lista numerada de problemas encontrados (com severidade: alta/média/baixa)
> - Para cada problema: o que está errado/faltando e como corrigir
> - Uma seção final "Veredicto": a análise está aprovada para apresentar ao Tech Lead? O que DEVE ser corrigido antes?

### Resposta da IA (output):

**Arquivo gerado:** `revisao-critica-analise-viabilidade.md`

**12 problemas identificados:**

| # | Problema | Severidade |
|---|----------|-----------|
| 1 | Estimativa de planilhas arbitrária e provavelmente subestimada | Média |
| 2 | Cálculo de "quantos chunks cabem" é enganoso — ignora custo e multi-turno | Alta |
| 3 | Perguntas cross-document sem estratégia de retrieval | Alta |
| 4 | Filtro temporal assume metadata que não existe na NovaTech | Alta |
| 5 | Latência em produção não analisada | Alta |
| 6 | Custo operacional mensal não estimado | Média |
| 7 | Cold start e feedback loop sem estratégia | Média |
| 8 | FAQ tratado com mesmo peso que docs normativos | Média |
| 9 | Integração Teams tem complexidades ignoradas | Média |
| 10 | Prazo de 3 meses não validado contra escopo | Alta |
| 11 | Sem fallback quando retrieval não encontra nada | Média |
| 12 | Sem observabilidade/monitoramento em produção | Baixa |

**Veredicto:** ⚠️ NÃO aprovada para Tech Lead sem corrigir 4 bloqueadores (#3, #4, #5, #10).

---

## Iteração 3 — Consolidação Final

### Meu prompt (input):

> 1. **Análise original** (produzida na primeira etapa):
> [referência ao arquivo analise-viabilidade-tecnica-rag.md]
>
> 2. **Revisão crítica** (feedback recebido):
> [referência ao arquivo revisao-critica-analise-viabilidade.md]
>
> Gere um arquivo markdown com a ANÁLISE TÉCNICA FINAL consolidada que:
> - Incorpore todas as correções e melhorias apontadas na revisão crítica
> - Corrija estimativas otimistas com valores mais realistas
> - Adicione os riscos que estavam faltando
> - Mantenha a estrutura de seções numeradas da análise original
> - Marque com [REVISADO] os trechos que foram alterados em relação à versão original, para que fique evidente o que mudou
>
> O documento final deve ser autossuficiente — alguém que leia apenas ele deve entender a análise completa sem precisar consultar os dois documentos de origem.
>
> Formato: markdown estruturado, pronto para salvar como arquivo .md

### Resposta da IA (output):

**Arquivo gerado:** `analise-viabilidade-tecnica-rag-final.md`

Documento de 12 seções com todas as correções incorporadas. Seções marcadas com [REVISADO]:
- §1.5 — Hierarquia de confiabilidade das fontes (nova)
- §2.1 — Estimativa de planilhas em faixa otimista/pessimista (corrigida)
- §3.4 — Cenário de conversa multi-turno (nova)
- §4.2 — Documentos contraditórios com reconhecimento de limitações (reescrita)
- §4.3 — Estratégia para perguntas cross-document com query decomposition (nova)
- §4.5 — Fallback quando retrieval falha (nova)
- §5 — Análise de latência end-to-end (nova)
- §6 — Estimativa de custo operacional ~$400–500/mês (nova)
- §7 — Viabilidade de prazo com escopo faseado (nova)
- §8 — Cold start com shadow mode e eval set (nova)
- §9 — Considerações de integração Teams (nova)
- §10 — Monitoramento e observabilidade (nova)

---

## Resumo das Melhorias (v1 → versão final)

### Correções de estimativas

- **Tokens da base:** De valor único (~7,3M) para faixa com cenário pessimista (~10M adotado). Estimativa de planilhas corrigida de premissa arbitrária para cenário realista.
- **Chunks no índice:** De ~20.950 para ~28.950 (consequência da estimativa corrigida).

### Riscos que não existiam na v1

- ✅ **Latência end-to-end** — estimada em 3–9s/query, validada contra meta de <2min
- ✅ **Custo operacional** — calculado: ~$400–500/mês, ~$9/atendente/mês, ROI 15–20×
- ✅ **Cold start** — estratégia de shadow mode + eval set + critérios de promoção
- ✅ **Fallback para retrieval sem resultado** — threshold de relevância + escalação por domínio
- ✅ **Hierarquia de fontes** — FAQ (informal) vs POL/PROC/SLA (normativo)
- ✅ **Observabilidade** — métricas mínimas com thresholds de alerta
- ✅ **Integração Teams** — arquitetura + premissas a validar + limitações

### Problemas arquiteturais corrigidos

- ❌ **v1:** Filtro temporal assumia metadata que não existe → ✅ **Final:** Reconhece que curadoria manual é necessária, propõe processo pragmático com estimativa de esforço (2–3 dias)
- ❌ **v1:** Sem estratégia para perguntas cross-document → ✅ **Final:** Query decomposition com classificação de intent via GPT-4o-mini + multi-query retrieval
- ❌ **v1:** Conversa multi-turno ignorada → ✅ **Final:** Modelagem de crescimento de histórico + sumarização obrigatória após turno 3
- ❌ **v1:** Prazo não validado → ✅ **Final:** Escopo faseado explícito (MVP 3 meses com ~85% cobertura, expansão mês 4–5)

### Valor agregado pela iteração

1. **Credibilidade aumentada:** Estimativas em faixa (não valor único), premissas explícitas, limitações reconhecidas.
2. **Acionabilidade:** Escopo faseado permite que Tech Lead/Delivery Manager tomem decisão informada sobre prazo.
3. **Completude operacional:** Custo, latência, monitoramento — aspectos que a diretoria e o DM vão perguntar.
4. **Honestidade técnica:** Reconhecer que a metadata de vigência não existe (e não fingir que um filtro resolve) aumenta confiança do Tech Lead na análise.
5. **Proteção contra falhas:** Fallback, shadow mode e eval set reduzem risco de abandono no go-live.

---

## Conclusão sobre o processo de iteração

A primeira versão da análise cobria bem os fundamentos técnicos de RAG (chunking, embeddings, lost-in-the-middle), mas era **otimista demais** e **incompleta em aspectos operacionais**. A revisão crítica identificou 4 bloqueadores e 8 melhorias. A versão final é um documento **pronto para decisão** — não apenas uma análise técnica, mas um insumo para planejamento de projeto com prazo, custo e escopo realistas.

O exercício demonstra que:
- Aceitar o primeiro output da IA sem revisão teria resultado em um documento com falhas significativas (filtro temporal inviável, prazo irrealista, sem análise de custo/latência).
- A iteração com papel de "devil's advocate" forçou a identificação de pressupostos implícitos e cenários não cobertos.
- A consolidação final produziu um documento superior a qualquer uma das duas versões intermediárias isoladamente.
