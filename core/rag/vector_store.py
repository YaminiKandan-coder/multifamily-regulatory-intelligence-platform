from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel
from config import settings
from core.rag.chunking import chunk_legal_text, _sliding_window_chunks


class SearchResult(BaseModel):
    id: int
    chunk_text: str
    similarity: float
    metadata: dict[str, Any] = {}


def _chunk_text(text: str) -> list[str]:
    if settings.RAG_USE_LEGAL_CHUNKING:
        chunks = chunk_legal_text(text)
        return [c for c, _ in chunks]
    chunks = _sliding_window_chunks(text)
    return [c for c, _ in chunks]


class RegulationVectorStore:
    def __init__(self, db_client: Any, llm_client: Any) -> None:
        self._db = db_client
        self._llm = llm_client

    def add_documents(self, regulations: list[dict[str, Any]]) -> int:
        count = 0
        for reg in regulations:
            content = reg.get("content", "")
            reg_id = reg.get("id")
            if not content or reg_id is None:
                continue
            chunks = _chunk_text(content)
            for chunk in chunks:
                embedding = self._llm.embed(chunk)
                self._db.table("regulation_embeddings").insert({
                    "regulation_id": reg_id,
                    "embedding": embedding,
                    "chunk_text": chunk,
                }).execute()
                count += 1
        return count

    def search(
        self,
        query: str,
        top_k: int = 5,
        jurisdiction_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> list[SearchResult]:
        embedding = self._llm.embed(query)
        try:
            params: dict[str, Any] = {
                "query_embedding": embedding,
                "match_count": top_k,
                "filter_jurisdiction": jurisdiction_id,
            }
            if category:
                params["category_filter"] = category
            resp = self._db.rpc("match_regulations_v2", params).execute()
        except Exception:
            resp = self._db.rpc(
                "match_regulations",
                {
                    "query_embedding": embedding,
                    "match_count": top_k,
                    "filter_jurisdiction": jurisdiction_id,
                },
            ).execute()
        return [SearchResult(**row) for row in (resp.data or [])]

    def search_v3(
        self,
        query: str,
        top_k: int = 5,
        jurisdiction_ids: Optional[list[int]] = None,
        category: Optional[str] = None,
    ) -> list[SearchResult]:
        embedding = self._llm.embed(query)
        resp = self._db.rpc(
            "match_regulations_v3",
            {
                "query_embedding": embedding,
                "match_count": top_k,
                "jurisdiction_ids": jurisdiction_ids,
                "category_filter": category,
            },
        ).execute()
        return [SearchResult(**row) for row in (resp.data or [])]

    def delete_by_regulation_id(self, regulation_id: int) -> None:
        self._db.table("regulation_embeddings").delete().eq(
            "regulation_id", regulation_id
        ).execute()
