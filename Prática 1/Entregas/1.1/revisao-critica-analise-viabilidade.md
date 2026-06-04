# Revisão Crítica — Análise de Viabilidade RAG NovaTech

**Revisor:** Revisor Técnico Sênior — Arquiteturas RAG em Produção  
**Data:** 01/06/2026  
**Documento revisado:** `analise-viabilidade-tecnica-rag.md`  
**Veredicto geral:** ⚠️ Requer correções antes de apresentar ao Tech Lead

---

## Problemas Identificados

### 1. Estimativa de tokens para planilhas é arbitrária e provavelmente subestimada

**Severidade: Média**

**O que está errado:**  
A estimativa de planilhas assume "200 linhas × 10 colunas × 3 palavras por célula × 3 abas = 18.000 palavras/planilha". Essa premissa é inventada — não há dados do cliente para sustentá-la. Planilhas de frete com 15+ colunas (mencionadas no próprio cenário) contradizem a suposição de "10 colunas". Além disso, planilhas frequentemente contêm nomes de cidades, endereços de CDs, e descrições que excedem "3 palavras por célula".

Mais importante: se forem tabelas de frete com combinações região × peso × tipo × cliente, o número de linhas pode facilmente ser 2.000+ por aba, não 200.

**Como corrigir:**  
- Apresentar a estimativa como **faixa** (cenário otimista/pessimista), não como valor único.
- Cenário pessimista: 50 planilhas × 1.000 linhas × 15 colunas × 4 palavras = 3.000.000 palavras → ~4.000.000 tokens.
- Isso elevaria o total da base para ~10M tokens, não 7,3M. A diferença não muda a conclusão (RAG continua obrigatório), mas muda a estimativa de chunks no índice (~28.500 vs ~20.950).

---

### 2. O cálculo de "quantos chunks cabem" é enganoso e pode induzir erro de decisão

**Severidade: Alta**

**O que está errado:**  
A análise calcula que 234 chunks "cabem" na janela e depois argumenta que não se deve usar todos. Correto — mas a forma como está escrito sugere que o orçamento de contexto é generoso. O problema real não é espaço, é **custo e latência**. Enviar 10.000 tokens de chunks em cada request para GPT-4o com 192 chamados/dia (60% de 320) tem impacto financeiro direto que não foi calculado.

Além disso, a seção ignora completamente o **output token budget**. A análise aloca "2.000–4.000 tokens para resposta gerada", mas respostas de atendimento com citação de fonte, explicação e procedimento facilmente excedem 1.000 palavras (~1.333 tokens). Se o atendente faz follow-up, o histórico cresce e consome do orçamento de chunks — este cenário iterativo não foi modelado.

**Como corrigir:**  
- Modelar o cenário de conversa multi-turno: turno 1 (1K histórico) → turno 3 (5K histórico) → turno 5 (12K+ histórico). No turno 5, o espaço para chunks cai significativamente se não houver sumarização do histórico.
- Adicionar recomendação explícita: **sumarização de histórico** ou **sliding window** para conversas longas no Teams.
- Calcular o custo por query e o custo mensal (ver problema #7).

---

### 3. Perguntas cross-document não têm estratégia de retrieval definida

**Severidade: Alta**

**O que está errado:**  
A análise menciona "perguntas multi-domínio" e sugere 8–12 chunks, mas não explica **como** o pipeline decide que uma pergunta é multi-domínio, nem como garante que chunks de todos os documentos relevantes sejam recuperados.

Exemplo concreto não coberto: *"Qual o custo de devolver uma carga de 600kg para o Norte?"*

Essa pergunta cruza:
- **POL-001** (seção 3.5): custos de devolução — "desistência do cliente: frete reverso com mesmos multiplicadores do frete original"
- **PROC-042-v2** (seção 2.1): multiplicador Norte = 1.8, fator de peso 1.0 (500-1000kg)

Se o retrieval semântico buscar por similaridade com a pergunta completa, pode retornar chunks sobre "devolução" OU sobre "frete especial", mas não necessariamente ambos com relevância suficiente para aparecer no top-5. O termo "custo de devolver" tem mais similaridade semântica com POL-001, e o chunk de multiplicadores pode ficar na posição 8–10 do ranking.

**Como corrigir:**  
- Definir estratégia de **query decomposition**: antes de buscar, um LLM (ou regras) decompõe a pergunta em sub-queries. Ex: "custo de devolução" + "frete 600kg Norte".
- Alternativa: implementar **multi-query retrieval** — gerar 2–3 reformulações da pergunta e fazer union dos resultados.
- Incluir esta estratégia na seção 4 com exemplo concreto da NovaTech.

---

### 4. A estratégia para documentos contraditórios tem uma falha lógica no filtro temporal

**Severidade: Alta**

**O que está errado:**  
A solução proposta (filtro `vigencia_fim >= data_atual OR vigencia_fim IS NULL`) assume que alguém preencheu o campo `vigencia_fim` da PROC-042 v1. Mas o cenário diz explicitamente: *"Este documento não possui indicação formal de vigência ou obsolescência no sistema da NovaTech. Ambos coexistem no SharePoint sem hierarquia clara."*

Ou seja: **não há metadata de vigência para popular**. Quem define que a v1 tem `vigencia_fim: 2023-11-30`? A seção 5 da v2 define regra transicional, mas isso é uma informação dentro do texto, não metadata estruturada. O pipeline teria que:
1. Ler a seção 5 da v2
2. Interpretar que isso implica obsolescência da v1 para chamados pós-01/12/2023
3. Inferir `vigencia_fim` para a v1

Isso requer **interpretação humana ou NLP** no momento da ingestão — não é um filtro simples. E com 800 documentos, quantos outros pares contraditórios existem que não foram mapeados?

**Como corrigir:**  
- Reconhecer explicitamente que a metadata de vigência **não existe hoje** e que criá-la é um **esforço de curadoria manual** para os documentos-chave.
- Propor um processo pragmático: durante o discovery, pedir à NovaTech uma lista de documentos com versões múltiplas. Para esses (~5–10% da base?), fazer curadoria manual de vigência.
- Para o restante: usar heurísticas (data de emissão mais recente = vigente) + instrução no prompt como fallback.
- Estimar o esforço dessa curadoria e verificar se cabe nos 3 meses.

---

### 5. Latência em produção não foi analisada

**Severidade: Alta**

**O que está errado:**  
Nenhuma análise de latência end-to-end. O SLA do cliente Gold é 2h para primeira resposta. Se o atendente precisa esperar 15–30 segundos pela resposta do assistente em cada interação, isso impacta a produtividade prometida (reduzir de 12min para <2min). O pipeline completo é:

1. Receber pergunta no Teams → chamar API (~100ms)
2. Gerar embedding da pergunta → Azure OpenAI (~200–500ms)
3. Buscar no Azure AI Search (~100–300ms com re-ranker semântico)
4. Enviar chunks + pergunta ao GPT-4o → geração (~2–8 segundos dependendo do output)
5. Retornar ao Teams (~100ms)

**Latência estimada total: 3–10 segundos por query.**

Com 192 queries/dia (~24/hora no pico, assumindo distribuição 8h), isso é gerenciável. Mas a análise deveria ter feito essa conta para confirmar.

**Cenário preocupante:** Se o atendente faz 3–4 perguntas por chamado (refinamento), são 30–40 segundos de espera por chamado. Somado ao tempo de leitura/ação, os "2 minutos" são viáveis, mas apertados.

**Como corrigir:**  
- Adicionar seção "Análise de Latência" com estimativa end-to-end.
- Considerar **streaming** (GPT-4o retorna tokens progressivamente no Teams) para melhorar percepção de velocidade.
- Avaliar se o Azure AI Search com semantic ranker adiciona latência aceitável vs busca vetorial pura.

---

### 6. Custo operacional mensal não foi estimado

**Severidade: Média**

**O que está errado:**  
A análise não menciona custo de operação. Para validação com Tech Lead e para o Delivery Manager dimensionar orçamento, é essencial.

**Estimativa que deveria constar:**

- **Queries/mês:** 192/dia × 22 dias úteis = ~4.224 queries/mês
- **Tokens de input por query** (system prompt + histórico + chunks): ~2.000 + 2.000 + 5.000 = ~9.000 tokens
- **Tokens de output por query:** ~500–1.000 tokens
- **Total input/mês:** 4.224 × 9.000 = ~38M tokens input
- **Total output/mês:** 4.224 × 750 = ~3,2M tokens output

Com pricing GPT-4o (referência Azure): ~$2.50/1M input tokens, ~$10/1M output tokens:
- Input: 38M × $2.50/M = ~$95/mês
- Output: 3,2M × $10/M = ~$32/mês
- **Total LLM: ~$127/mês**

Adicionar:
- Azure AI Search (Standard tier): ~$250/mês
- Azure OpenAI embeddings (ingestão + queries): ~$20/mês
- Document Intelligence (OCR): ~$50/mês (ingestão inicial)
- **Total estimado: ~$450–600/mês em regime**

Isso é barato para 45 atendentes (R$ 15–20/atendente/mês). Mas a ingestão inicial dos 800 PDFs com Document Intelligence pode custar $500–1.000 one-time.

**Como corrigir:**  
- Adicionar seção "Estimativa de Custo Operacional" com breakdown por serviço.
- Incluir custo de ingestão inicial (one-time) vs custo mensal recorrente.

---

### 7. Cold start e feedback loop não têm estratégia

**Severidade: Média**

**O que está errado:**  
A análise menciona "tuning iterativo com perguntas reais dos atendentes" e "fase piloto com 50 perguntas", mas não define:
- Como as 50 perguntas serão selecionadas (quem escolhe? com que critério?)
- O que acontece entre o go-live e o momento em que se tem feedback suficiente para calibrar
- Como medir se o assistente está errando (quem valida as respostas?)

**Cenário de cold start:** No dia 1 com atendentes reais, o sistema não tem métricas de retrieval (precision/recall) calibradas. Se o top-K é 5 mas o chunk certo ficou na posição 6, ninguém vai saber até um atendente reclamar. E atendentes sob pressão de SLA podem parar de usar o assistente se as primeiras experiências forem ruins — criando um loop de abandono.

**Como corrigir:**  
- Definir **eval set** de ouro: usar as perguntas do Mapa de Cobertura (Anexo B) como benchmark pré-go-live. Validar precision@5 e recall@5 antes de liberar para atendentes.
- Propor **shadow mode** nas primeiras 2 semanas: o assistente roda em paralelo, atendentes validam respostas com thumbs up/down, sem dependência operacional.
- Definir métrica mínima para go-live: ex: "80% das respostas do eval set corretas e com fonte válida".

---

### 8. A FAQ como fonte de verdade é um risco não ponderado adequadamente

**Severidade: Média**

**O que está errado:**  
A análise trata todas as fontes igualmente na estratégia de chunking. Mas o FAQ-Atendimento é explicitamente marcado como "NÃO validado por Compliance ou Operações" e "pode conter informações desatualizadas ou imprecisas".

Se o pipeline ingere o FAQ com o mesmo peso que a POL-001, o assistente pode citar o FAQ-38 ("encaminhe para sinistros@novatech.com.br") como se fosse procedimento oficial — quando na verdade é conhecimento informal de atendentes. O atendente novato não vai distinguir "resposta baseada no FAQ informal" de "resposta baseada na política oficial".

**Cenário concreto:** Pergunta sobre desconto — o FAQ-45 diz "para clientes com mais de 10 fretes especiais/mês, existe desconto automático". A PROC-042-v2 diz "a partir de 8 fretes/mês". O FAQ está **desatualizado** em relação à v2. Se ambos forem recuperados, qual prevalece?

**Como corrigir:**  
- Implementar **hierarquia de confiabilidade** na metadata: `confiabilidade: normativo` (POL, PROC, SLA) vs `confiabilidade: informal` (FAQ).
- No system prompt: "Priorize SEMPRE documentos normativos (POL, PROC, SLA) sobre documentos informais (FAQ). Quando citar o FAQ, indique explicitamente que a fonte é informal."
- Alternativa mais drástica: **excluir o FAQ da base de retrieval** e usá-lo apenas como dado de treinamento para reformulação de perguntas (entender a linguagem dos atendentes).

---

### 9. Integração Teams + SharePoint tem complexidades não mencionadas

**Severidade: Média**

**O que está errado:**  
A análise foca no pipeline de dados e na geração, mas ignora a integração com Teams — que é onde os atendentes vão interagir. Aspectos não cobertos:

- **Autenticação e permissões:** Todos os atendentes podem ver todos os documentos? Ou há restrições por departamento/tier? Se houver, o retrieval precisa de security trimming.
- **Experiência conversacional no Teams:** O Teams tem limitações de formatação (cards adaptativos, markdown limitado, tamanho de mensagem). Respostas longas com tabelas podem renderizar mal.
- **Rate limiting:** O Azure Bot Framework tem limites de mensagens por segundo. Com 24 queries/hora no pico, não é problema — mas se múltiplos atendentes perguntarem simultaneamente, o queuing importa.
- **Persistência de sessão:** O histórico de conversa no Teams é gerenciado como? Cada mensagem é uma nova invocação ou há estado de sessão?

**Como corrigir:**  
- Adicionar seção "Considerações de Integração" mapeando: Teams Bot Framework → Azure Function → Azure AI Search + Azure OpenAI.
- Listar premissa: "assumimos que todos os atendentes têm acesso a todos os documentos" ou flag como ponto a validar com a NovaTech.

---

### 10. Prazo de 3 meses não foi validado contra o escopo técnico

**Severidade: Alta**

**O que está errado:**  
A análise lista um escopo técnico considerável e não cruza com o prazo disponível:

- Ingestão de 800 PDFs com Document Intelligence (incluindo 120 OCR com validação humana)
- Ingestão de 400 páginas Confluence via API com resolução de links
- Processamento de 50 planilhas com estruturação semântica
- Implementação de chunking hierárquico em 3 níveis
- Filtro temporal com curadoria de vigência
- Busca híbrida (vetorial + BM25) com re-ranker
- Query decomposition para perguntas multi-domínio
- Integração Teams com Bot Framework
- Fase piloto com eval set e shadow mode

Isso é discovery + engenharia de dados + backend + integração + testes + piloto em 3 meses (assumindo ~2 devs + 1 data engineer). É extremamente apertado. A validação humana de ~120 documentos OCR sozinha pode levar 2–4 semanas se depender do time da NovaTech.

**Como corrigir:**  
- Incluir seção "Viabilidade de prazo" com estimativa de esforço por componente.
- Propor **escopo mínimo viável** para 3 meses: apenas PDFs texto (680 docs) + wiki, sem OCR na v1. Planilhas e OCR como fase 2.
- Ou propor explicitamente que 3 meses é insuficiente para o escopo completo e recomendar go-live parcial.

---

### 11. Não há estratégia de fallback quando o retrieval falha

**Severidade: Média**

**O que está errado:**  
O Mapa de Cobertura (Anexo B) mostra que a pergunta "Frete para 300kg para Salvador?" não tem chunk relevante (frete padrão < 500kg não está documentado). A análise não define o que o assistente faz quando:
- Nenhum chunk tem score acima do threshold de relevância
- Os chunks recuperados não respondem à pergunta
- A pergunta é sobre algo não documentado

Sem essa definição, o LLM vai alucinar uma resposta (ex: inventar um valor de frete para 300kg) ou dar uma resposta vaga e inútil.

**Como corrigir:**  
- Definir **threshold mínimo de relevância** (ex: score coseno > 0.75) abaixo do qual o assistente responde: "Não encontrei informação sobre isso na documentação. Encaminhe ao [setor X]."
- Definir **comportamento de escalação**: se o assistente não sabe, para quem o atendente deve perguntar?
- Mapear os gaps documentais conhecidos (frete < 500kg, carga danificada fora de sinistro) e definir respostas padrão de redirecionamento.

---

### 12. Não menciona observabilidade e monitoramento em produção

**Severidade: Baixa**

**O que está errado:**  
Em produção com 192 queries/dia, é crítico ter:
- Log de queries + chunks retornados + resposta gerada (para debug e melhoria)
- Métricas de retrieval (score médio dos top-K, % de queries sem chunks relevantes)
- Métricas de satisfação (feedback dos atendentes)
- Alertas de degradação (ex: score médio caiu 20% após atualização de docs)

A análise não menciona nada disso. Sem observabilidade, problemas como "o assistente começou a misturar versões da PROC-042" podem persistir semanas até alguém reclamar.

**Como corrigir:**  
- Adicionar seção "Monitoramento e Observabilidade" com métricas mínimas para go-live.
- Propor stack: Application Insights (já no Azure) para logs + dashboard com métricas de RAG.

---

## Pontos positivos da análise (para não ser apenas negativo)

- A análise de "lost in the middle" é tecnicamente sólida e demonstra conhecimento real de limitações de LLMs.
- O tratamento de tabelas como chunks atômicos é a decisão correta.
- A busca híbrida (vetorial + BM25) é acertada para o domínio (códigos como "PROC-042", "POL-001" são melhor capturados por keyword match).
- A referência concreta aos documentos da NovaTech (multiplicadores, SLAs) demonstra que o desenvolvedor leu o material de referência.
- A seção 4.2 sobre documentos contraditórios identifica o problema correto, mesmo que a solução proposta tenha falhas.

---

## Veredicto

### ⚠️ A análise NÃO está pronta para apresentar ao Tech Lead sem correções.

**DEVE ser corrigido antes de apresentar (bloqueadores):**

| # | Problema | Por quê é bloqueador |
|---|----------|---------------------|
| 3 | Falta estratégia para perguntas cross-document | O Tech Lead vai perguntar "e se a pergunta cruza dois docs?" e a análise não tem resposta |
| 4 | Filtro temporal assume metadata que não existe | A solução proposta é inviável sem esforço de curadoria que não foi estimado |
| 5 | Sem análise de latência | Impossível validar se a meta de <2min/chamado é atingível sem estimar tempo de resposta do assistente |
| 10 | Prazo não foi cruzado com escopo | O Tech Lead precisa saber se 3 meses é viável — a análise propõe escopo de 6+ meses sem perceber |

**DEVERIA ser adicionado (importantes mas não bloqueadores):**

| # | Problema | Impacto |
|---|----------|---------|
| 6 | Custo operacional | Delivery Manager precisa para orçamento |
| 7 | Cold start | Risco de abandono pelos atendentes |
| 8 | Hierarquia FAQ vs docs normativos | Risco de respostas baseadas em fonte não confiável |
| 11 | Fallback para retrieval sem resultado | Risco de alucinação |

**PODE ser adicionado em versão posterior (nice to have):**

| # | Problema | Impacto |
|---|----------|---------|
| 1 | Refinar estimativa de planilhas | Não muda conclusão, melhora credibilidade |
| 9 | Detalhes de integração Teams | Pode ser documento separado |
| 12 | Observabilidade | Necessário para produção, não para validação de viabilidade |

---

**Recomendação ao desenvolvedor:** Corrija os 4 bloqueadores, adicione estimativa de custo (5 minutos de cálculo), e proponha um escopo mínimo viável para 3 meses separando o que é v1 do que é v2. Depois disso, o documento estará apto para revisão do Tech Lead.
