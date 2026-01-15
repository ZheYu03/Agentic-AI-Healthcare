"""
Offline ingestion script to upsert the Hugging Face MedQuAD dataset into Pinecone
using Google text-embedding-004 embeddings.

Prereqs (env vars must be set):
- PINECONE_API_KEY
- PINECONE_INDEX_HOST  (new host-based API)
- GOOGLE_API_KEY
"""

import hashlib
import os
import sys
from typing import Iterable, List, Tuple

from datasets import load_dataset
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone

# Ingestion configuration
DATASET_NAME = "lavita/MedQuAD"
SPLIT = "train"  # MedQuAD is a single split
CHUNK_SIZE = 1000  # larger chunks per request
CHUNK_OVERLAP = 120
# Keep batch payloads under Pinecone's ~4MB JSON limit.
# With 768-dim embeddings + metadata, 10 vectors per upsert is a safe cap.
BATCH_SIZE = 10


def log(msg: str) -> None:
    print(msg, flush=True)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple deterministic chunking to make each chunk retrievable."""
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap
    return chunks


def make_doc_id(question: str, synonyms: str, source: str, chunk_idx: int) -> str:
    """Stable deterministic ID to support idempotent upserts."""
    base = f"{question.strip().lower()}::{synonyms.strip().lower()}::{source.strip().lower()}::{chunk_idx}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def format_record(question: str, answer: str, context: str, synonyms: str) -> str:
    """Combine fields into a single retrievable block; text = question + answer + synonyms."""
    return (
        f"Question: {question.strip()}\n"
        f"Synonyms: {synonyms.strip()}\n"
        f"Answer: {answer.strip()}"
    )


def batch_iter(iterable: Iterable, batch_size: int) -> Iterable[List]:
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def main() -> None:
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")
    pinecone_host = os.environ.get("PINECONE_INDEX_HOST")
    google_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    start_batch = int(os.environ.get("START_BATCH", "0"))
    max_batches = int(os.environ.get("MAX_BATCHES", "0"))  # 0 = no cap

    if not pinecone_api_key or not pinecone_host or not google_api_key:
        log("ERROR: Missing required environment variables (PINECONE_API_KEY, PINECONE_INDEX_HOST, GOOGLE_API_KEY).")
        sys.exit(1)

    log(f"Loading dataset {DATASET_NAME}...")
    ds = load_dataset(DATASET_NAME, split=SPLIT)
    log(f"Loaded {len(ds)} records.")

    # Initialize embeddings (Gemini)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=google_api_key,
    )

    # Initialize Pinecone client and index (host-based)
    pc = Pinecone(api_key=pinecone_api_key)
    index = pc.Index(host=pinecone_host)

    total_vectors = 0
    processed_batches = 0
    for batch_num, batch in enumerate(batch_iter(ds, batch_size=BATCH_SIZE), start=1):
        if batch_num <= start_batch:
            continue
        vectors = []
        for rec in batch:
            question = rec.get("question") or ""
            answer = rec.get("answer") or ""
            context = rec.get("context") or ""
            source_url = rec.get("document_url") or rec.get("url") or "MedQuAD"
            synonyms_field = rec.get("synonyms") or rec.get("synonym") or ""
            if isinstance(synonyms_field, list):
                synonyms = "; ".join([str(s) for s in synonyms_field])
            else:
                synonyms = str(synonyms_field)

            combined = format_record(question, answer, context, synonyms)
            for idx, chunk in enumerate(chunk_text(combined, CHUNK_SIZE, CHUNK_OVERLAP)):
                vec_id = make_doc_id(question, synonyms, source_url, idx)
                vectors.append(
                    {
                        "id": vec_id,
                        "values": embeddings.embed_query(chunk),
                        "metadata": {
                            "question": question,
                            "source": source_url,
                            "chunk_index": idx,
                            "synonyms": synonyms,
                            "answer": answer,
                            "text": chunk,  # ensure page_content is populated on retrieval
                        },
                    }
                )

        if not vectors:
            continue

        try:
            index.upsert(vectors=vectors)
            total_vectors += len(vectors)
            log(f"Batch {batch_num}: upserted {len(vectors)} vectors (total {total_vectors}).")
        except Exception as exc:  # pragma: no cover
            log(f"ERROR in batch {batch_num}: {exc}")
        processed_batches += 1
        if max_batches and processed_batches >= max_batches:
            log(f"Reached MAX_BATCHES={max_batches}. Stopping early.")
            break

    log(f"Done. Total vectors upserted: {total_vectors}")


if __name__ == "__main__":
    main()
