"""Prompt builder: combines system prompt, retrieved chunks, and the user
query into a complete prompt ready for an LLM."""

SYSTEM_PROMPT = """\
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
⚠️ [Alertas ou ressalvas, se aplicável]\
"""


def build_prompt(query: str, chunks: list[dict]) -> str:
    """Assemble a full prompt from system prompt, retrieved chunks, and query.

    Parameters
    ----------
    query : str
        The attendant's question.
    chunks : list[dict]
        List of chunk dicts as returned by ``search.search()``.

    Returns
    -------
    str
        The assembled prompt string.
    """

    # Format chunks
    chunks_section_parts: list[str] = []
    for c in chunks:
        part = (
            f"--- Chunk {c['rank']} ---\n"
            f"Fonte: {c['source']} | Seção: {c['section']} | Documento: {c['doc_id']}\n"
            f"Score de similaridade: {c['distance']:.4f}\n\n"
            f"{c['text']}\n\n"
            f"---"
        )
        chunks_section_parts.append(part)

    chunks_block = "\n\n".join(chunks_section_parts)

    prompt = (
        f"<system_prompt>\n{SYSTEM_PROMPT}\n</system_prompt>\n\n"
        f"<contexto_recuperado>\n{chunks_block}\n</contexto_recuperado>\n\n"
        f"<pergunta_do_atendente>\n{query}\n</pergunta_do_atendente>"
    )

    # Print formatted prompt
    print("\n" + "=" * 70)
    print("PROMPT MONTADO")
    print("=" * 70)
    print(prompt)
    print("=" * 70 + "\n")

    return prompt
