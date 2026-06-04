"""End-to-end test script: runs ingestion (if needed), executes 5 test
queries, saves prompts and generates an analysis report."""

import os
import textwrap

import chromadb

import config
from ingest import ingest
from search import search
from prompt_builder import build_prompt


# ---------------------------------------------------------------------------
# Test cases (from the coverage map in Anexo B)
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "id": 1,
        "query": "Qual o prazo de devolução?",
        "expected": ["POL-001 (Seção 3.1 — Prazo geral)", "POL-001 (Seção 3.2 — Exceções ao prazo geral)"],
        "possible": ["POL-001 (Seção 3.3 — Procedimento de devolução)"],
    },
    {
        "id": 2,
        "query": "Posso devolver carga perigosa?",
        "expected": ["POL-001 (Seção 3.2 — Exceções ao prazo geral)"],
        "possible": ["FAQ Item 3", "POL-001 (Seção 3.1 — Prazo geral)"],
    },
    {
        "id": 3,
        "query": "Qual o SLA do cliente Gold?",
        "expected": ["SLA-2024 (Seção 2 — Tabela de SLAs)"],
        "possible": ["SLA-2024 (Seção 1 — Classificação de clientes)",
                      "SLA-2024 (Seção 3 — Definição de incidente crítico)"],
    },
    {
        "id": 4,
        "query": "Quanto custa o frete para 600kg para Manaus?",
        "expected": ["PROC-042-v2 (Seção 2.1 — Multiplicadores atualizados)",
                      "PROC-042-v2 (Seção 2 — Fórmula de cálculo)"],
        "possible": ["PROC-042 v1 (Seção 2.1 — Multiplicadores — risco de contradição)"],
    },
    {
        "id": 5,
        "query": "Qual o multiplicador para o Sudeste?",
        "expected": ["PROC-042-v2 (Seção 2.1 — Multiplicadores atualizados)"],
        "possible": ["PROC-042 v1 (Seção 2.1 — Multiplicadores — contradição: 1.0 vs 1.1)"],
    },
]


def _ensure_ingestion() -> None:
    """Run ingestion if the ChromaDB collection is empty or missing."""
    client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
    try:
        col = client.get_collection(config.COLLECTION_NAME)
        if col.count() > 0:
            print(f"[MAIN] Collection '{config.COLLECTION_NAME}' já populada ({col.count()} chunks). "
                  "Pulando ingestão.\n")
            return
    except Exception:
        pass

    print("[MAIN] Collection vazia ou inexistente. Executando ingestão...\n")
    ingest(force=True)
    print()


def _save_prompt(test_id: int, query: str, prompt: str) -> str:
    """Save the assembled prompt to a text file and return the path."""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    filename = f"prompt_teste_{test_id}.txt"
    filepath = os.path.join(config.RESULTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Pergunta: {query}\n\n")
        f.write(prompt)
    return filepath


def _build_report(results: list[dict]) -> str:
    """Build a markdown report analysing chunk retrieval quality."""

    lines: list[str] = [
        "# Relatório de Teste — Pipeline RAG NovaTech\n",
        f"Total de perguntas testadas: {len(results)}\n",
    ]

    for r in results:
        lines.append(f"\n---\n\n## Pergunta {r['id']}: \"{r['query']}\"\n")

        lines.append("### Chunks recuperados\n")
        lines.append("| Rank | Score | Fonte | Seção | Preview |")
        lines.append("|------|-------|-------|-------|---------|")
        for c in r["chunks"]:
            preview = c["text"][:80].replace("\n", " ").replace("|", "\\|")
            lines.append(
                f"| {c['rank']} | {c['distance']:.4f} | {c['source']} | {c['section']} | {preview}… |"
            )

        lines.append("\n### Chunks esperados (gabarito)\n")
        for e in r["expected"]:
            lines.append(f"- {e}")

        lines.append("\n### Chunks possíveis (relevância menor)\n")
        for p in r["possible"]:
            lines.append(f"- {p}")

        lines.append("\n### Análise\n")

        # Simple heuristic analysis
        retrieved_sources = [(c["doc_id"], c["section"]) for c in r["chunks"]]
        retrieved_summary = [f"{c['doc_id']}/{c['section']}" for c in r["chunks"]]

        lines.append(f"Chunks retornados (doc_id/seção): {', '.join(retrieved_summary)}\n")

        # Check coverage
        expected_ids = [e.split("(")[0].strip() for e in r["expected"]]
        found_expected = []
        for exp_id in expected_ids:
            exp_id_clean = exp_id.replace(" ", "").replace("-", "").upper()
            for c in r["chunks"]:
                c_id_clean = c["doc_id"].replace(" ", "").replace("-", "").upper()
                if exp_id_clean.startswith(c_id_clean) or c_id_clean.startswith(exp_id_clean):
                    found_expected.append(exp_id)
                    break

        if len(found_expected) == len(expected_ids):
            lines.append("✅ **Todos os chunks esperados foram recuperados.**\n")
        else:
            missing = set(expected_ids) - set(found_expected)
            lines.append(f"⚠️ **Chunks esperados não encontrados no top-{config.DEFAULT_TOP_K}:** {', '.join(missing)}\n")

    return "\n".join(lines)


def main() -> None:
    """Run the end-to-end test pipeline."""
    print("=" * 70)
    print("  PIPELINE RAG — NovaTech — Teste End-to-End")
    print("=" * 70 + "\n")

    _ensure_ingestion()

    results: list[dict] = []

    for tc in TEST_CASES:
        print(f"\n{'─' * 70}")
        print(f"  TESTE {tc['id']}: {tc['query']}")
        print(f"{'─' * 70}")

        chunks = search(tc["query"], top_k=config.DEFAULT_TOP_K)
        prompt = build_prompt(tc["query"], chunks)
        filepath = _save_prompt(tc["id"], tc["query"], prompt)
        print(f"  Prompt salvo em: {filepath}")

        results.append({
            "id": tc["id"],
            "query": tc["query"],
            "chunks": chunks,
            "expected": tc["expected"],
            "possible": tc["possible"],
        })

    # Generate consolidated report
    report = _build_report(results)
    report_path = os.path.join(config.RESULTS_DIR, "relatorio-teste.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n{'=' * 70}")
    print(f"  Relatório consolidado salvo em: {report_path}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
