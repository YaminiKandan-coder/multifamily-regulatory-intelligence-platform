from __future__ import annotations
import re
from dataclasses import dataclass, field
from config import CHUNK_SIZE, CHUNK_OVERLAP

# Patterns for legal structure detection
_SECTION_PATTERNS = [
    re.compile(r"^(ARTICLE\s+[IVXLCDM\d]+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^(§\s*\d+[\.\d]*)", re.MULTILINE),
    re.compile(r"^(Section\s+\d+[\.\d]*)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^(\d+\.\s+[A-Z])", re.MULTILINE),
]
_DEFINITIONS_RE = re.compile(r"\b(means|defined as|\"[A-Z][a-z]+\"\s+means)\b", re.IGNORECASE)
_EFFECTIVE_DATE_RE = re.compile(r"\beffective\s+(date|january|february|march|april|may|june|july|august|september|october|november|december)\b", re.IGNORECASE)


@dataclass
class ChunkMeta:
    section_title: str = ""
    chunk_index: int = 0
    total_chunks: int = 0
    has_definitions: bool = False
    has_effective_date: bool = False


def chunk_legal_text(text: str) -> list[tuple[str, ChunkMeta]]:
    boundaries = _find_section_boundaries(text)
    if len(boundaries) < 2:
        return _sliding_window_chunks(text)

    chunks: list[tuple[str, ChunkMeta]] = []
    for i, (start, title) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        section_text = text[start:end].strip()
        if not section_text:
            continue
        if len(section_text) <= CHUNK_SIZE:
            meta = ChunkMeta(
                section_title=title,
                chunk_index=0,
                total_chunks=1,
                has_definitions=bool(_DEFINITIONS_RE.search(section_text)),
                has_effective_date=bool(_EFFECTIVE_DATE_RE.search(section_text)),
            )
            chunks.append((section_text, meta))
        else:
            sub = _sliding_window_chunks(section_text, title_prefix=title)
            chunks.extend(sub)

    # Update total_chunks per section group
    total = len(chunks)
    for idx, (text_chunk, meta) in enumerate(chunks):
        chunks[idx] = (text_chunk, ChunkMeta(
            section_title=meta.section_title,
            chunk_index=idx,
            total_chunks=total,
            has_definitions=meta.has_definitions,
            has_effective_date=meta.has_effective_date,
        ))
    return chunks


def _find_section_boundaries(text: str) -> list[tuple[int, str]]:
    boundaries: list[tuple[int, str]] = []
    for pattern in _SECTION_PATTERNS:
        for m in pattern.finditer(text):
            boundaries.append((m.start(), m.group(1).strip()))
    boundaries.sort(key=lambda x: x[0])
    # Deduplicate overlapping positions
    seen: set[int] = set()
    deduped = []
    for pos, title in boundaries:
        if pos not in seen:
            seen.add(pos)
            deduped.append((pos, title))
    return deduped


def _sliding_window_chunks(
    text: str, title_prefix: str = ""
) -> list[tuple[str, ChunkMeta]]:
    chunks: list[tuple[str, ChunkMeta]] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if not chunk.strip():
            break
        meta = ChunkMeta(
            section_title=title_prefix,
            chunk_index=idx,
            total_chunks=0,  # updated below
            has_definitions=bool(_DEFINITIONS_RE.search(chunk)),
            has_effective_date=bool(_EFFECTIVE_DATE_RE.search(chunk)),
        )
        chunks.append((chunk, meta))
        start += CHUNK_SIZE - CHUNK_OVERLAP
        idx += 1

    total = len(chunks)
    return [
        (c, ChunkMeta(
            section_title=m.section_title,
            chunk_index=m.chunk_index,
            total_chunks=total,
            has_definitions=m.has_definitions,
            has_effective_date=m.has_effective_date,
        ))
        for c, m in chunks
    ]
