# Prompt para Geração do Pipeline de RAG — Exercício 1.3

> **Instrução:** Copie o prompt abaixo (seção "PROMPT") e cole no GitHub Copilot (chat) ou Claude para gerar o código do pipeline. O prompt já contém todos os requisitos, a stack técnica, a estrutura dos documentos-fonte e as perguntas de teste.

---

## PROMPT

Preciso que você implemente um pipeline de RAG (Retrieval-Augmented Generation) mínimo e funcional em Python. O objetivo é uma prova de conceito que ingira documentos de uma empresa de logística (NovaTech), crie embeddings, armazene em um vector store local e permita buscar chunks relevantes para montar prompts completos para um LLM.

### Stack técnica obrigatória (todas gratuitas/open-source)

- **Python 3.10+**
- **ChromaDB** como vector store local (`pip install chromadb`)
- **sentence-transformers** para embeddings (`pip install sentence-transformers` — modelo: `all-MiniLM-L6-v2`)
- **Orquestração manual** (sem LangChain — código direto para manter controle e transparência)

### Estrutura do projeto

Crie os seguintes arquivos:

```
rag_pipeline/
├── ingest.py          # Script de ingestão: lê documentos, chunka, gera embeddings, armazena no ChromaDB
├── search.py          # Função de busca: recebe pergunta, busca N chunks mais similares
├── prompt_builder.py  # Função de montagem de prompt: combina system prompt + chunks + pergunta
├── main.py            # Script principal para rodar testes end-to-end
├── requirements.txt   # Dependências
└── config.py          # Configurações centralizadas (caminhos, parâmetros de chunking, etc.)
```

### Documentos a ingerir

Os documentos-fonte são 5 arquivos markdown (`.md`) localizados no diretório pai do projeto (`../`). Os arquivos são:

1. **`POL-001-politica-devolucao.md`** — Política de devolução de mercadorias. Documento normativo. Contém seções numeradas (3.1 a 3.5), regras com exceções, procedimento passo-a-passo, tabela de custos.
2. **`PROC-042-frete-especial-v1.md`** — Procedimento de cálculo de frete especial (versão 1.0, março/2023). Contém fórmula, tabela de multiplicadores regionais, fatores de peso.
3. **`PROC-042-v2-frete-especial-revisado.md`** — Procedimento de cálculo de frete especial (versão 2.0, novembro/2023). Versão atualizada com multiplicadores diferentes. ⚠️ Coexiste com a v1 sem hierarquia formal — é um caso proposital de contradição documental.
4. **`SLA-2024-tabela-sla-clientes.md`** — Tabela de SLA por tipo de cliente. Contém classificação de tiers (Gold/Silver/Standard), tabelas de SLA, definição de incidente crítico, penalidades.
5. **`FAQ-atendimento.md`** — Perguntas frequentes do time de suporte. Documento informal, não validado por Compliance. Contém respostas práticas dos atendentes.

### Requisitos detalhados por módulo

#### 1. `config.py` — Configurações

- Caminho do diretório de documentos (default: `../`)
- Nome da collection do ChromaDB
- Caminho do diretório persistente do ChromaDB (default: `./chroma_db`)
- Modelo de embeddings: `all-MiniLM-L6-v2`
- Parâmetros de chunking (tamanho, overlap) — configuráveis
- Número de resultados padrão para busca (top_k)

#### 2. `ingest.py` — Ingestão de documentos

**Estratégia de chunking — IMPORTANTE:**

Não usar chunking fixo cego (ex: 512 tokens). Implementar **chunking semântico por seção do markdown**, com a seguinte lógica:

1. **Detectar headers markdown** (`##`, `###`) como delimitadores de seção.
2. **Cada seção (header + conteúdo até o próximo header de mesmo nível ou superior) vira um chunk.**
3. **Se uma seção exceder 1000 caracteres**, subdividir em sub-chunks com overlap de ~100 caracteres, quebrando em parágrafos (linhas em branco).
4. **Se uma seção contiver uma tabela markdown** (detectar linhas com `|`), manter a tabela inteira no mesmo chunk — nunca cortar uma tabela no meio.
5. **Preservar metadados** em cada chunk:
   - `source`: nome do arquivo de origem (ex: `POL-001-politica-devolucao.md`)
   - `doc_id`: identificador do documento (ex: `POL-001`)
   - `section`: header da seção (ex: `3.2. Exceções ao prazo geral`)
   - `version`: versão do documento, se disponível no cabeçalho (ex: `3.1`, `2.0`)
   - `date`: data de emissão/atualização, se disponível
   - `doc_type`: tipo inferido (`normativo`, `procedimento`, `sla`, `faq`)

**Justificativa do chunking por seção:** Os documentos da NovaTech são estruturados com seções temáticas claras (prazo, exceções, procedimento, custos). Chunking por seção preserva a unidade semântica de cada regra/procedimento, evitando que uma regra seja cortada ao meio. A preservação de tabelas inteiras é essencial porque tabelas de multiplicadores ou SLAs perdem sentido se fragmentadas.

**Fluxo do script:**
1. Listar todos os `.md` no diretório de documentos
2. Para cada arquivo: ler conteúdo, extrair metadados do cabeçalho, aplicar chunking
3. Gerar embeddings para cada chunk usando sentence-transformers
4. Armazenar no ChromaDB com embeddings + metadados + texto do chunk
5. Imprimir relatório: total de documentos processados, total de chunks gerados, chunks por documento

#### 3. `search.py` — Busca por similaridade

Implementar uma função `search(query: str, top_k: int = 5) -> list[dict]` que:

1. Carrega o modelo de embeddings (mesmo usado na ingestão)
2. Gera o embedding da query
3. Busca os `top_k` chunks mais similares no ChromaDB
4. Retorna uma lista de dicionários, cada um contendo:
   - `text`: conteúdo do chunk
   - `source`: arquivo de origem
   - `section`: seção do documento
   - `doc_id`: identificador do documento
   - `distance`: distância/score de similaridade retornado pelo ChromaDB
   - `rank`: posição no ranking (1 = mais similar)

A função deve imprimir os resultados de forma legível para análise humana (rank, score, source, preview do texto).

#### 4. `prompt_builder.py` — Montagem do prompt

Implementar uma função `build_prompt(query: str, chunks: list[dict]) -> str` que:

1. Monta um prompt completo com a seguinte estrutura:

```
<system_prompt>
[System prompt do assistente NovaTech — usar o conteúdo abaixo]
</system_prompt>

<contexto_recuperado>
[Para cada chunk recuperado, formatado como:]
--- Chunk {rank} ---
Fonte: {source} | Seção: {section} | Documento: {doc_id}
Score de similaridade: {distance}

{texto do chunk}

---
</contexto_recuperado>

<pergunta_do_atendente>
{query}
</pergunta_do_atendente>
```

2. O system prompt a incluir é (versão resumida para o pipeline):

```
Você é o Assistente NovaTech, uma ferramenta de apoio ao time de atendimento ao cliente da NovaTech, empresa de logística.

REGRAS INVIOLÁVEIS:
1. Toda informação na resposta DEVE citar a fonte no formato [CÓDIGO-DOC, Seção X.X].
2. NUNCA invente prazos, valores, percentuais ou regras que não estejam nos chunks fornecidos.
3. Quando não encontrar informação suficiente, diga explicitamente e sugira escalar para o supervisor.
4. Responda em português formal mas acessível. Seja direto — o atendente está em chamado.

HIERARQUIA DE FONTES (da mais alta para a mais baixa):
1. Documentos normativos vigentes (POL-001, SLA-2024)
2. Procedimentos operacionais — versão mais recente (PROC-042-v2)
3. Procedimentos operacionais — versões anteriores (PROC-042 v1) — apenas quando aplicável por disposição transitória
4. FAQ de atendimento — fonte informal, NÃO validada. Usar apenas como complemento.

CONFLITO PROC-042 v1 vs v2:
- Para chamados novos (a partir de 01/12/2023): usar PROC-042-v2.
- Para chamados abertos antes de 01/12/2023: usar PROC-042 v1.
- Quando ambas aparecerem: informar que existem duas versões e indicar qual se aplica.

FORMATO DE RESPOSTA:
[Resposta direta — máximo 2-3 frases]
**Detalhes:** [Informações complementares em tópicos, se necessário]
**Fonte(s):** [CÓDIGO-DOC, Seção X.X]
⚠️ [Alertas ou ressalvas, se aplicável]
```

3. Retornar o prompt completo como string e também imprimi-lo formatado no console.

#### 5. `main.py` — Testes end-to-end

Implementar um script que:

1. Verifica se o ChromaDB já foi populado; se não, roda a ingestão.
2. Executa as 5 perguntas de teste abaixo sequencialmente.
3. Para cada pergunta: executa busca, monta prompt, salva o prompt em um arquivo `.txt` na pasta `resultados/`.
4. Gera um relatório consolidado em `resultados/relatorio-teste.md` com:
   - Pergunta
   - Chunks recuperados (rank, score, source, preview)
   - Chunks esperados (do gabarito)
   - Análise: os chunks corretos foram recuperados? Qual a posição? Houve chunks irrelevantes?

**As 5 perguntas de teste (do mapa de cobertura do Anexo B):**

| # | Pergunta | Chunks esperados (gabarito) | Chunks possíveis (relevância menor) |
|---|----------|---------------------------|--------------------------------------|
| 1 | "Qual o prazo de devolução?" | POL-001-A (Seção 3.1), POL-001-B (Seção 3.2 exceções) | POL-001-C (procedimento) |
| 2 | "Posso devolver carga perigosa?" | POL-001-B (Seção 3.2 exceções) | FAQ-03, POL-001-A |
| 3 | "Qual o SLA do cliente Gold?" | SLA-2024-B (tabela SLA chamados gerais) | SLA-2024-A (classificação), SLA-2024-C (incidentes críticos) |
| 4 | "Quanto custa o frete para 600kg para Manaus?" | PROC-042v2-B (multiplicadores atualizados), PROC-042v2-A (fórmula) | PROC-042-B (versão antiga — risco de contradição) |
| 5 | "Qual o multiplicador para o Sudeste?" | PROC-042v2-B (multiplicadores atualizados) | PROC-042-B (versão antiga — contradição: 1.0 vs 1.1) |

#### 6. `requirements.txt`

```
chromadb
sentence-transformers
```

### Requisitos de qualidade

- **Código limpo e legível**: nomes de variáveis e funções descritivos, em inglês.
- **Prints informativos**: o pipeline deve imprimir progresso (ingestão: "Processando documento X... Y chunks gerados"; busca: "Top 5 chunks para query X").
- **Tratamento de erros básico**: arquivo não encontrado, ChromaDB não inicializado.
- **Encoding**: Tratar encoding UTF-8 para caracteres em português (acentos, cedilha).

### O que NÃO precisa ter

- Não precisa de API de LLM (a geração será feita manualmente no Claude).
- Não precisa de interface web ou API REST.
- Não precisa de LangChain — código manual é preferível para controle total.
- Não precisa de testes unitários formais (os 5 testes do main.py são suficientes).

---

*Gere o código completo de todos os arquivos, pronto para executar.*
