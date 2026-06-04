"""Search module: receives a query, generates its embedding, and retrieves
the top-K most similar chunks from ChromaDB."""

import chromadb
from sentence_transformers import SentenceTransformer

import config


def search(query: str, top_k: int | None = None) -> list[dict]:
    """Search for the most similar chunks to the given query.

    Returns a list of dicts with keys: text, source, section, doc_id,
    distance, rank.
    """
    top_k = top_k or config.DEFAULT_TOP_K

    # Load ChromaDB
    client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
    try:
        collection = client.get_collection(name=config.COLLECTION_NAME)
    except Exception:
        print("[ERRO] Collection não encontrada. Execute a ingestão primeiro (python ingest.py).")
        return []

    if collection.count() == 0:
        print("[ERRO] Collection está vazia. Execute a ingestão primeiro.")
        return []

    # Generate query embedding
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    query_embedding = model.encode([query]).tolist()

    # Query ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Build result list
    ranked: list[dict] = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        ranked.append({
            "text": results["documents"][0][i],
            "source": meta.get("source", ""),
            "section": meta.get("section", ""),
            "doc_id": meta.get("doc_id", ""),
            "distance": results["distances"][0][i],
            "rank": i + 1,
        })

    # Pretty-print results
    print(f"\n{'=' * 60}")
    print(f"Top {top_k} chunks para: \"{query}\"")
    print(f"{'=' * 60}")
    for r in ranked:
        preview = r["text"][:120].replace("\n", " ")
        print(f"\n  [{r['rank']}] Score: {r['distance']:.4f}")
        print(f"      Fonte: {r['source']} | Seção: {r['section']} | Doc: {r['doc_id']}")
        print(f"      Preview: {preview}...")
    print(f"{'=' * 60}\n")

    return ranked


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Qual o prazo de devolução?"
    search(query)
