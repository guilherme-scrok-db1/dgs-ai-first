"""Ingestion script: reads markdown documents, chunks by section, generates
embeddings, and stores everything in ChromaDB."""

import os
import re
import glob

import chromadb
from sentence_transformers import SentenceTransformer

import config


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def _extract_header_metadata(content: str, filename: str) -> dict:
    """Extract version, date, and doc_id from the YAML-like header block."""
    meta: dict = {}

    # doc_id: first token before the first dash in the filename (e.g. POL-001)
    name_no_ext = os.path.splitext(filename)[0]
    # Try to get a meaningful doc_id (e.g. POL-001, PROC-042, SLA-2024, FAQ)
    match = re.match(r"((?:POL|PROC|SLA|FAQ)[\w-]*?)(?:-[a-záàâãéèêíïóôõúç])", name_no_ext, re.IGNORECASE)
    if match:
        meta["doc_id"] = match.group(1)
    else:
        meta["doc_id"] = name_no_ext

    # version
    ver_match = re.search(r"\*\*Vers[ãa]o:\*\*\s*(.+)", content)
    if ver_match:
        meta["version"] = ver_match.group(1).strip()

    # date
    date_match = re.search(r"\*\*(?:Última atualização|Data de emissão):\*\*\s*(.+)", content)
    if date_match:
        meta["date"] = date_match.group(1).strip()

    # doc_type
    prefix = meta["doc_id"].split("-")[0].upper()
    meta["doc_type"] = config.DOC_TYPE_MAP.get(prefix, "outro")

    return meta


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _contains_table(text: str) -> bool:
    """Return True if the text block contains a markdown table."""
    lines = text.strip().split("\n")
    pipe_lines = [l for l in lines if "|" in l]
    return len(pipe_lines) >= 2


def _split_large_section(text: str, max_size: int, overlap: int) -> list[str]:
    """Split a large section into sub-chunks on paragraph boundaries,
    keeping any markdown table intact in one chunk."""

    # If the section is mostly a table, keep it whole regardless of size.
    if _contains_table(text):
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para.strip()
        if len(candidate) > max_size and current:
            chunks.append(current.strip())
            # Add overlap from the end of the previous chunk
            overlap_text = current.strip()[-overlap:] if len(current.strip()) > overlap else current.strip()
            current = overlap_text + "\n\n" + para.strip()
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


def _chunk_markdown(content: str, filename: str) -> list[dict]:
    """Split markdown content into semantic chunks based on headers."""

    meta = _extract_header_metadata(content, filename)

    # Split by headers (## or ###)
    header_pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(content))

    sections: list[tuple[str, str]] = []  # (header_text, body)

    if not matches:
        # No headers found — treat the whole document as one section
        sections.append(("Documento completo", content.strip()))
    else:
        # Content before the first header (preamble)
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append(("Cabeçalho", preamble))

        for i, m in enumerate(matches):
            header_text = m.group(2).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            if body:
                sections.append((header_text, body))

    chunks: list[dict] = []
    for section_title, section_body in sections:
        full_text = f"## {section_title}\n\n{section_body}" if section_title != "Cabeçalho" else section_body

        if len(full_text) > config.MAX_CHUNK_SIZE:
            sub_chunks = _split_large_section(full_text, config.MAX_CHUNK_SIZE, config.CHUNK_OVERLAP)
        else:
            sub_chunks = [full_text]

        for sc in sub_chunks:
            chunks.append({
                "text": sc,
                "metadata": {
                    "source": filename,
                    "doc_id": meta["doc_id"],
                    "section": section_title,
                    "version": meta.get("version", "N/A"),
                    "date": meta.get("date", "N/A"),
                    "doc_type": meta["doc_type"],
                },
            })

    return chunks


# ---------------------------------------------------------------------------
# Main ingestion flow
# ---------------------------------------------------------------------------

def ingest(documents_dir: str | None = None, force: bool = False) -> None:
    """Read all .md files, chunk them, generate embeddings, store in ChromaDB."""

    docs_dir = documents_dir or config.DOCUMENTS_DIR
    docs_dir = os.path.abspath(docs_dir)

    # Only ingest the 5 target NovaTech documents
    target_files = [
        "POL-001-politica-devolucao.md",
        "PROC-042-frete-especial-v1.md",
        "PROC-042-v2-frete-especial-revisado.md",
        "SLA-2024-tabela-sla-clientes.md",
        "FAQ-atendimento.md",
    ]
    md_files = sorted(
        os.path.join(docs_dir, f) for f in target_files
        if os.path.isfile(os.path.join(docs_dir, f))
    )
    if not md_files:
        print(f"[ERRO] Nenhum arquivo .md encontrado em {docs_dir}")
        return

    print(f"[INGESTÃO] Encontrados {len(md_files)} documentos em {docs_dir}")

    # Initialise ChromaDB
    client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)

    if force:
        # Delete existing collection if forcing re-ingestion
        try:
            client.delete_collection(config.COLLECTION_NAME)
            print("[INGESTÃO] Collection existente removida (force=True).")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Check if already populated
    if collection.count() > 0 and not force:
        print(f"[INGESTÃO] Collection '{config.COLLECTION_NAME}' já possui {collection.count()} chunks. "
              "Use force=True para re-ingerir.")
        return

    # Load embedding model
    print(f"[INGESTÃO] Carregando modelo de embeddings: {config.EMBEDDING_MODEL} ...")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    all_chunks: list[dict] = []
    stats: dict[str, int] = {}

    for filepath in md_files:
        filename = os.path.basename(filepath)
        print(f"  Processando: {filename} ...", end=" ")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = _chunk_markdown(content, filename)
        stats[filename] = len(chunks)
        all_chunks.extend(chunks)
        print(f"{len(chunks)} chunks gerados.")

    if not all_chunks:
        print("[ERRO] Nenhum chunk gerado.")
        return

    # Generate embeddings
    print(f"[INGESTÃO] Gerando embeddings para {len(all_chunks)} chunks ...")
    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Store in ChromaDB
    ids = [f"chunk_{i:04d}" for i in range(len(all_chunks))]
    metadatas = [c["metadata"] for c in all_chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    # Report
    print("\n" + "=" * 60)
    print("RELATÓRIO DE INGESTÃO")
    print("=" * 60)
    print(f"Total de documentos processados: {len(stats)}")
    print(f"Total de chunks gerados:         {len(all_chunks)}")
    print("-" * 60)
    for doc, count in stats.items():
        print(f"  {doc:50s} → {count} chunks")
    print("=" * 60)


if __name__ == "__main__":
    ingest(force=True)
