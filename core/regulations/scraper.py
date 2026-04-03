from __future__ import annotations
import csv
import hashlib
import io
import re
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None  # type: ignore

from config import settings

# State name ↔ code lookups
STATE_NAME_TO_CODE: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

STATE_CODE_TO_NAME: dict[str, str] = {v: k.title() for k, v in STATE_NAME_TO_CODE.items()}

CITY_TO_STATE: dict[str, str] = {
    "dallas": "TX", "houston": "TX", "austin": "TX",
    "san antonio": "TX", "fort worth": "TX",
    "los angeles": "CA", "san francisco": "CA", "san diego": "CA",
    "new york city": "NY", "new york": "NY", "brooklyn": "NY",
    "chicago": "IL", "miami": "FL", "seattle": "WA",
    "denver": "CO", "phoenix": "AZ", "portland": "OR",
}

_BOILERPLATE_RE = re.compile(
    r"(cookie policy|privacy policy|terms of use|skip to content|navigation|"
    r"sign in|log in|subscribe|newsletter|advertisement)",
    re.IGNORECASE,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _scrape_html(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "ComplianceBot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip() and not _BOILERPLATE_RE.search(l)]
    return "\n".join(lines)


def _scrape_pdf(url: str, timeout: int = 30) -> str:
    if PyPDF2 is None:
        return ""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _use_db_registry(db_client: Any) -> bool:
    try:
        resp = db_client.table("app_settings").select("value").eq(
            "key", "use_db_source_registry"
        ).single().execute()
        return (resp.data or {}).get("value", "false").lower() == "true"
    except Exception:
        return False


def load_regulations_from_csv(db_client: Any, csv_path: str) -> int:
    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            content_hash = _sha256(row.get("content", ""))
            existing = db_client.table("regulations").select("id").eq(
                "content_hash", content_hash
            ).execute()
            if existing.data:
                continue
            db_client.table("regulations").insert({
                "jurisdiction_id": int(row["jurisdiction_id"]),
                "domain": row.get("domain", "housing"),
                "category": row.get("category", "General"),
                "source_name": row.get("source_name", ""),
                "url": row.get("url", ""),
                "content": row.get("content", ""),
                "content_hash": content_hash,
                "version": 1,
                "is_current": True,
            }).execute()
            count += 1
    return count


def get_unindexed_regulations(db_client: Any) -> list[dict[str, Any]]:
    indexed_ids_resp = db_client.table("regulation_embeddings").select(
        "regulation_id"
    ).execute()
    indexed_ids = {r["regulation_id"] for r in (indexed_ids_resp.data or [])}

    all_resp = db_client.table("regulations").select("id,content,jurisdiction_id,source_name,url").eq(
        "is_current", True
    ).execute()
    return [r for r in (all_resp.data or []) if r["id"] not in indexed_ids]


def get_indexing_status(db_client: Any) -> dict[str, int]:
    total_resp = db_client.table("regulations").select("id", count="exact").eq(
        "is_current", True
    ).execute()
    indexed_resp = db_client.table("regulation_embeddings").select(
        "regulation_id"
    ).execute()
    indexed_ids = len({r["regulation_id"] for r in (indexed_resp.data or [])})
    return {
        "total": total_resp.count or 0,
        "indexed": indexed_ids,
        "unindexed": max(0, (total_resp.count or 0) - indexed_ids),
    }


class RegulationScraper:
    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    def scrape_url(self, url: str) -> str:
        if url.lower().endswith(".pdf"):
            return _scrape_pdf(url)
        return _scrape_html(url)

    def scrape_and_store(self, source: dict[str, Any]) -> Optional[dict[str, Any]]:
        url = source.get("url", "")
        try:
            content = self.scrape_url(url)
            if not content.strip():
                return None
            content_hash = _sha256(content)
            existing = self._db.table("regulations").select("id,content_hash").eq(
                "url", url
            ).eq("is_current", True).execute()
            if existing.data and existing.data[0]["content_hash"] == content_hash:
                return None  # No change
            # Deactivate old version
            if existing.data:
                self._db.table("regulations").update({"is_current": False}).eq(
                    "url", url
                ).execute()
            resp = self._db.table("regulations").insert({
                "jurisdiction_id": source.get("jurisdiction_id", 1),
                "domain": source.get("domain", "housing"),
                "category": source.get("category", "General"),
                "source_name": source.get("source_name", ""),
                "url": url,
                "content": content,
                "content_hash": content_hash,
                "version": 1,
                "is_current": True,
            }).execute()
            return resp.data[0] if resp.data else None
        except Exception as e:
            return None


class ScraperService:
    def __init__(self, db_client: Any, llm_client: Any) -> None:
        self._db = db_client
        self._llm = llm_client
        self._scraper = RegulationScraper(db_client)

    def load_from_csv(self, csv_path: str) -> int:
        return load_regulations_from_csv(self._db, csv_path)

    def initialize_vector_index(self) -> int:
        from core.rag.vector_store import RegulationVectorStore
        store = RegulationVectorStore(self._db, self._llm)
        unindexed = get_unindexed_regulations(self._db)
        return store.add_documents(unindexed)

    def scrape_and_index(self) -> dict[str, int]:
        sources = self._get_sources()
        scraped = 0
        for source in sources:
            result = self._scraper.scrape_and_store(source)
            if result:
                scraped += 1
                # Update last_scraped_at if using DB registry
                if _use_db_registry(self._db):
                    try:
                        self._db.table("regulation_sources").update({
                            "last_scraped_at": "now()",
                            "last_error": None,
                        }).eq("id", source.get("id")).execute()
                    except Exception:
                        pass
        indexed = self.initialize_vector_index()
        return {"scraped": scraped, "indexed": indexed}

    def _get_sources(self) -> list[dict[str, Any]]:
        if _use_db_registry(self._db):
            resp = self._db.table("regulation_sources").select("*").eq(
                "is_active", True
            ).execute()
            return resp.data or []
        # Legacy: load from regulations table
        resp = self._db.table("regulations").select(
            "id,jurisdiction_id,source_name,url,domain,category"
        ).eq("is_current", True).execute()
        return resp.data or []
