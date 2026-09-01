"""Load synthetic filing text files from data/filings/.

Public function used by teammates:
    load_documents()
"""

from __future__ import annotations

from pathlib import Path

# Filings live at <project_root>/data/filings/, next to this rag/ package.
_FILINGS_DIR = Path(__file__).resolve().parent.parent / "data" / "filings"


def load_documents() -> list[dict]:
    """Load every .txt file in data/filings/.

    Returns:
        A list of {"source": filename, "text": file contents}.
        Returns [] if the folder is missing or no readable files exist.
        Never invents documents or source names.
    """
    if not _FILINGS_DIR.is_dir():
        print(f"Warning: filings folder not found: {_FILINGS_DIR}")
        return []

    documents: list[dict] = []
    for path in sorted(_FILINGS_DIR.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Warning: could not read {path.name}: {exc}")
            continue
        documents.append({"source": path.name, "text": text})

    return documents


def chunk_document(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    source: str = "",
) -> list[dict]:
    """Split text into overlapping character chunks.

    Tries to break on a newline or period near the chunk end so passages
    stay readable. Each chunk keeps its source filename.

    Args:
        text: Full document text.
        chunk_size: Target chunk length in characters.
        overlap: Characters reused between neighbouring chunks.
        source: Original filename, copied onto every chunk.

    Returns:
        A list of {"source": source, "text": chunk_text}.
    """
    if not text or not str(text).strip():
        return []

    cleaned = str(text).strip()
    size = max(int(chunk_size), 1)
    step_overlap = max(int(overlap), 0)

    chunks: list[dict] = []
    # Prefer one chunk per numbered section (1. Overview, 2. Revenue, ...).
    sections = _split_sections(cleaned)
    for section in sections:
        chunks.extend(_window_chunks(section, size, step_overlap, source))

    return chunks


def _split_sections(text: str) -> list[str]:
    """Split on headings like '1. Company Overview' so topics stay together."""
    parts: list[str] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        is_heading = (
            len(stripped) > 2
            and stripped[0].isdigit()
            and ". " in stripped[:4]
        )
        if is_heading and current:
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = [line]
        else:
            current.append(line)
    piece = "".join(current).strip()
    if piece:
        parts.append(piece)
    return parts or [text]


def _window_chunks(text: str, size: int, overlap: int, source: str) -> list[dict]:
    heading = text.splitlines()[0].strip() if text else ""
    if len(text) <= size:
        return [{"source": source, "text": text}]

    step = max(size - overlap, 1)
    chunks: list[dict] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        if end < length:
            break_at = _best_break(text[start:end])
            if break_at >= size // 2:
                end = start + break_at
        piece = text[start:end].strip()
        if piece:
            # Keep the section title on overflow pieces so retrieval still
            # sees "Revenue / Growth" or "Key Risks" in every sub-chunk.
            if start > 0 and heading and heading not in piece[: len(heading) + 5]:
                piece = heading + "\n" + piece
            chunks.append({"source": source, "text": piece})
        if end >= length:
            break
        start += step
    return chunks


def _best_break(window: str) -> int:
    """Prefer splitting at a paragraph or sentence boundary."""
    newline = window.rfind("\n")
    if newline != -1:
        return newline + 1
    period = window.rfind(". ")
    if period != -1:
        return period + 1
    return len(window)


if __name__ == "__main__":
    loaded = load_documents()
    print(f"Loaded {len(loaded)} document(s).")
    for doc in loaded:
        print(f"- {doc['source']}: {len(doc['text'])} characters")
