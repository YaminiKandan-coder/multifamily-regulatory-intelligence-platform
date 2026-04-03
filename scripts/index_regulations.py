"""Populates regulation_embeddings for all unindexed regulations."""
from __future__ import annotations
from core.regulations.scraper import ScraperService
from core.llm.client import llm
from db.client import get_db


def main() -> None:
    db = get_db()
    svc = ScraperService(db_client=db, llm_client=llm)
    count = svc.initialize_vector_index()
    print(f"Indexed {count} chunk(s).")


if __name__ == "__main__":
    main()
