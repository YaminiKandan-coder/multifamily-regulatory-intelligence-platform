from __future__ import annotations
from typing import Any, Optional
import pandas as pd


def get_state_jurisdiction_options(db_client: Any) -> list[dict[str, Any]]:
    resp = db_client.table("jurisdictions").select("id,name,type,state_code").execute()
    return resp.data or []


def get_distinct_categories(db_client: Any) -> list[str]:
    resp = db_client.table("regulations").select("category").execute()
    return sorted({r["category"] for r in (resp.data or []) if r.get("category")})


def get_explorer_metrics(db_client: Any) -> dict[str, int]:
    total_resp = db_client.table("regulations").select("id", count="exact").eq("is_current", True).execute()
    jur_resp = db_client.table("jurisdictions").select("id", count="exact").execute()
    embed_resp = db_client.table("regulation_embeddings").select("regulation_id").execute()
    indexed = len({r["regulation_id"] for r in (embed_resp.data or [])})
    return {
        "total_regulations": total_resp.count or 0,
        "total_jurisdictions": jur_resp.count or 0,
        "indexed_regulations": indexed,
    }


def search_regulations(
    db_client: Any,
    llm_client: Any,
    query: str,
    jurisdiction_id: Optional[int] = None,
    category: Optional[str] = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    try:
        embedding = llm_client.embed(query)
        params: dict[str, Any] = {
            "query_embedding": embedding,
            "match_count": top_k,
            "filter_jurisdiction": jurisdiction_id,
        }
        if category:
            params["category_filter"] = category
        try:
            resp = db_client.rpc("match_regulations_v2", params).execute()
        except Exception:
            resp = db_client.rpc("match_regulations", {
                "query_embedding": embedding,
                "match_count": top_k,
                "filter_jurisdiction": jurisdiction_id,
            }).execute()
        return resp.data or []
    except Exception:
        return []


def to_results_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame()
    rows = []
    for r in results:
        meta = r.get("metadata") or {}
        rows.append({
            "Source": meta.get("source_name", ""),
            "Category": meta.get("category", ""),
            "URL": meta.get("url", ""),
            "Similarity": round(r.get("similarity", 0.0), 3),
            "Excerpt": (r.get("chunk_text") or "")[:200],
        })
    return pd.DataFrame(rows)
