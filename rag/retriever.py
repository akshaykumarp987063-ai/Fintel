"""Rank filing chunks by similarity to a user query.

Public function used by teammates:
    retrieve_documents(query, top_k=3)
"""

from __future__ import annotations

try:
    from rag.document_loader import chunk_document, load_documents
    from rag.embeddings import cosine_similarity, embed_text, embed_texts
except ImportError:
    from document_loader import chunk_document, load_documents
    from embeddings import cosine_similarity, embed_text, embed_texts

# Reused across calls so we do not re-read and re-embed on every query.
_CHUNK_CACHE: list[dict] | None = None
_VECTOR_CACHE: list[list[float]] | None = None


def retrieve_documents(query: str, top_k: int = 3) -> list[dict]:
    """Return the most relevant filing chunks for a query.

    Each result looks like:
        {"source": "tcs_q2.txt", "text": "...", "score": 0.91}

    Returns [] if the query is empty, no documents exist, or embedding fails.
    Does not invent documents or source filenames.
    """
    if query is None or not str(query).strip():
        return []

    try:
        k = max(int(top_k), 0)
    except (TypeError, ValueError):
        k = 3
    if k == 0:
        return []

    chunks, vectors = _get_index()
    if not chunks or not vectors:
        return []

    try:
        query_vector = embed_text(str(query))
    except Exception as exc:
        print(f"Warning: could not embed query: {exc}")
        return []

    scored: list[tuple[float, dict]] = []
    for chunk, vector in zip(chunks, vectors):
        score = cosine_similarity(query_vector, vector)
        score += _source_boost(query, chunk.get("source", ""))
        score += _heading_boost(query, chunk.get("text", ""))
        score = min(max(score, 0.0), 1.0)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    results: list[dict] = []
    for score, chunk in scored[:k]:
        results.append(
            {
                "source": chunk["source"],
                "text": chunk["text"],
                "score": round(float(score), 4),
            }
        )
    return results


def _source_boost(query: str, source: str) -> float:
    """Raise the score when the query names the company in the filename."""
    query_l = str(query).lower()
    source_l = str(source).lower()
    aliases = {
        "tcs": ("tcs",),
        "infosys": ("infosys", "infy"),
        "reliance": ("reliance",),
    }
    for company, names in aliases.items():
        file_match = company in source_l or any(name in source_l for name in names)
        query_match = any(name in query_l for name in names)
        if file_match and query_match:
            return 0.35
    return 0.0


def _heading_boost(query: str, text: str) -> float:
    """Raise the score when the chunk heading matches the question topic."""
    heading = str(text).splitlines()[0].lower() if text else ""
    query_l = str(query).lower()
    topics = (
        (("revenue", "growth"), ("revenue", "growth")),
        (("operating", "margin"), ("margin",)),
        (("risk",), ("risk",)),
        (("outlook",), ("outlook",)),
        (("demand", "business demand"), ("demand",)),
        (("management",), ("management", "demand")),
    )
    boost = 0.0
    for heading_words, query_words in topics:
        if any(word in heading for word in heading_words) and any(
            word in query_l for word in query_words
        ):
            boost += 0.25
    return boost


def _get_index() -> tuple[list[dict], list[list[float]]]:
    """Build an in-memory chunk index once, then reuse it."""
    global _CHUNK_CACHE, _VECTOR_CACHE
    if _CHUNK_CACHE is not None and _VECTOR_CACHE is not None:
        return _CHUNK_CACHE, _VECTOR_CACHE

    documents = load_documents()
    chunks: list[dict] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document.get("text", ""),
                source=document.get("source", ""),
            )
        )

    if not chunks:
        _CHUNK_CACHE = []
        _VECTOR_CACHE = []
        return _CHUNK_CACHE, _VECTOR_CACHE

    # Include the filename in the embedding text so "TCS" matches tcs_q2.txt.
    try:
        embed_inputs = [
            f"{chunk.get('source', '')} {chunk.get('text', '')}"
            for chunk in chunks
        ]
        vectors = embed_texts(embed_inputs)
    except Exception as exc:
        print(f"Warning: could not embed documents: {exc}")
        return [], []

    if len(vectors) != len(chunks):
        print("Warning: embedding count did not match chunk count.")
        return [], []

    _CHUNK_CACHE = chunks
    _VECTOR_CACHE = vectors
    return _CHUNK_CACHE, _VECTOR_CACHE


if __name__ == "__main__":
    sample_queries = [
        "What happened to TCS revenue growth?",
        "What happened to operating margins?",
        "What are the key business risks?",
        "What is the company outlook?",
        "What is management saying about demand?",
    ]
    for sample in sample_queries:
        print("=" * 60)
        print(sample)
        for row in retrieve_documents(sample, top_k=3):
            preview = row["text"][:120].replace("\n", " ")
            print(f"  {row['source']}  score={row['score']}  {preview}...")
