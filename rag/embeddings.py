"""Lightweight text embeddings for the Fintel RAG demo.

Default: deterministic TF-IDF vectors fitted on the loaded filing chunks
(no internet, no keys). Query vectors use the same vocabulary.

Optional: OpenAI embeddings when OPENAI_API_KEY is set. If the API call
fails, this module falls back to the local vectors automatically.

No API keys are hardcoded.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.request

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "had", "has", "have", "how", "in", "is", "it", "of", "on", "or",
    "that", "the", "this", "to", "was", "were", "what", "when", "where",
    "which", "who", "with",
}

_OPENAI_URL = "https://api.openai.com/v1/embeddings"
_OPENAI_MODEL = "text-embedding-3-small"

# Fitted from the document corpus so query and chunks share one vector space.
_VOCAB: dict[str, int] | None = None
_IDF: list[float] | None = None


def embed_text(text: str) -> list[float]:
    """Turn one string into a numeric vector."""
    vectors = embed_texts([text if text is not None else ""], fit=False)
    return vectors[0]


def embed_texts(texts: list[str], fit: bool = True) -> list[list[float]]:
    """Embed many strings. Always returns one vector per input text.

    When fit=True (used for the document index), rebuilds the local TF-IDF
    vocabulary from these texts. Queries should use fit=False / embed_text().
    """
    cleaned = [item if isinstance(item, str) else "" for item in texts]

    if os.getenv("OPENAI_API_KEY"):
        try:
            return _openai_embed_texts(cleaned)
        except Exception as exc:
            print(f"Warning: embedding API unavailable ({exc}). Using local fallback.")

    if fit or _VOCAB is None:
        _fit_tfidf(cleaned)
    return [_tfidf_vector(item) for item in cleaned]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Cosine similarity. Returns 0.0 if either vector is empty or mismatched."""
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b

    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def _tokenize(text: str) -> list[str]:
    unigrams = [
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if token not in _STOPWORDS
    ]
    bigrams = [f"{left}_{right}" for left, right in zip(unigrams, unigrams[1:])]
    return unigrams + bigrams


def _fit_tfidf(texts: list[str]) -> None:
    global _VOCAB, _IDF
    doc_tokens = [_tokenize(text) for text in texts]
    vocab: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in tokens:
            if token not in vocab:
                vocab[token] = len(vocab)

    n_docs = max(len(texts), 1)
    df = [0] * len(vocab)
    for tokens in doc_tokens:
        seen = set(tokens)
        for token in seen:
            df[vocab[token]] += 1

    idf = [math.log((1.0 + n_docs) / (1.0 + count)) + 1.0 for count in df]
    _VOCAB = vocab
    _IDF = idf


def _tfidf_vector(text: str) -> list[float]:
    if not _VOCAB or not _IDF:
        return []

    vector = [0.0] * len(_VOCAB)
    tokens = _tokenize(text)
    if not tokens:
        return vector

    tf: dict[str, float] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0.0) + 1.0

    length = float(len(tokens))
    for token, count in tf.items():
        index = _VOCAB.get(token)
        if index is None:
            continue
        vector[index] = (count / length) * _IDF[index]

    return _l2_normalize(vector)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0.0:
        return vector
    return [value / norm for value in vector]


def _openai_embed_texts(texts: list[str]) -> list[list[float]]:
    """Optional remote embeddings. Isolated here; unused unless a key is set."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = json.dumps({"model": _OPENAI_MODEL, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        _OPENAI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))

    items = sorted(body.get("data", []), key=lambda row: row.get("index", 0))
    vectors = [row.get("embedding") for row in items]
    if len(vectors) != len(texts) or any(not vec for vec in vectors):
        raise RuntimeError("embedding API returned an unexpected payload")
    return vectors
