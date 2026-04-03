"""Loads data/seeds/sources.csv into the regulations table with SHA-256 deduplication."""
from __future__ import annotations
from core.regulations.scraper import load_regulations_from_csv
from db.client import get_db


def main() -> None:
    db = get_db()
    count = load_regulations_from_csv(db, "data/seeds/sources.csv")
    print(f"Seeded {count} regulation(s).")


if __name__ == "__main__":
    main()
