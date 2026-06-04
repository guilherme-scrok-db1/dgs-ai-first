"""Centralized configuration for the RAG pipeline."""

import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "..", "..")
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chroma_db")
RESULTS_DIR = os.path.join(BASE_DIR, "resultados")

# --- ChromaDB ---
COLLECTION_NAME = "novatech_docs"

# --- Embeddings ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Chunking ---
MAX_CHUNK_SIZE = 1000       # Max characters per chunk before splitting
CHUNK_OVERLAP = 100         # Character overlap when splitting large sections

# --- Search ---
DEFAULT_TOP_K = 5

# --- Document type inference mapping ---
DOC_TYPE_MAP = {
    "POL": "normativo",
    "PROC": "procedimento",
    "SLA": "sla",
    "FAQ": "faq",
}
