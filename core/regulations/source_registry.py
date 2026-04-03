from __future__ import annotations
import csv
import io
from datetime import datetime
from typing import Any, Optional
import requests
from config import settings


class AppSettingsRepo:
    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    def get(self, key: str) -> Optional[str]:
        try:
            resp = self._db.table("app_settings").select("value").eq("key", key).single().execute()
            return (resp.data or {}).get("value")
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        self._db.table("app_settings").upsert(
            {"key": key, "value": value, "updated_at": datetime.utcnow().isoformat()},
            on_conflict="key",
        ).execute()

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key)
        if val is None:
            return default
        return val.lower() == "true"

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, "true" if value else "false")

    def delete(self, key: str) -> None:
        self._db.table("app_settings").delete().eq("key", key).execute()

    def list_all(self) -> list[dict[str, Any]]:
        resp = self._db.table("app_settings").select("*").execute()
        return resp.data or []


class SourceRepository:
    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    def table_exists(self) -> bool:
        try:
            self._db.table("regulation_sources").select("id").limit(1).execute()
            return True
        except Exception:
            return False

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        state_code: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query = self._db.table("regulation_sources").select("*", count="exact")
        if state_code:
            query = query.eq("state_code", state_code)
        if is_active is not None:
            query = query.eq("is_active", is_active)
        offset = (page - 1) * page_size
        resp = query.range(offset, offset + page_size - 1).execute()
        data = resp.data or []
        if search:
            search_lower = search.lower()
            data = [
                r for r in data
                if search_lower in (r.get("source_name") or "").lower()
                or search_lower in (r.get("url") or "").lower()
            ]
        return data, resp.count or 0

    def get_by_url(self, url: str) -> Optional[dict[str, Any]]:
        try:
            resp = self._db.table("regulation_sources").select("*").eq("url", url).single().execute()
            return resp.data
        except Exception:
            return None

    def upsert_by_url(self, source: dict[str, Any]) -> dict[str, Any]:
        resp = self._db.table("regulation_sources").upsert(
            source, on_conflict="url"
        ).execute()
        return (resp.data or [{}])[0]

    def update_scrape_status(
        self, source_id: int, success: bool, error: Optional[str] = None
    ) -> None:
        self._db.table("regulation_sources").update({
            "last_scraped_at": datetime.utcnow().isoformat(),
            "last_error": None if success else error,
        }).eq("id", source_id).execute()

    def delete(self, source_id: int) -> None:
        self._db.table("regulation_sources").delete().eq("id", source_id).execute()

    def bulk_set_active(self, source_ids: list[int], is_active: bool) -> None:
        self._db.table("regulation_sources").update(
            {"is_active": is_active}
        ).in_("id", source_ids).execute()


class SourceRegistryService:
    def __init__(self, db_client: Any) -> None:
        self._db = db_client
        self._settings = AppSettingsRepo(db_client)
        self._repo = SourceRepository(db_client)

    def is_enabled(self) -> bool:
        return self._settings.get_bool("use_db_source_registry", default=False)

    def toggle(self, enabled: bool) -> None:
        self._settings.set_bool("use_db_source_registry", enabled)

    def backfill_from_csv(self, csv_path: str) -> int:
        count = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url", "").strip()
                if not url:
                    continue
                if self._repo.get_by_url(url):
                    continue  # idempotent
                self._repo.upsert_by_url({
                    "jurisdiction_id": int(row.get("jurisdiction_id", 1)),
                    "source_name": row.get("source_name", ""),
                    "url": url,
                    "domain": row.get("domain", "housing"),
                    "category": row.get("category", "General"),
                    "state_code": row.get("state_code") or None,
                    "is_active": True,
                })
                count += 1
        return count

    def test_source(self, url: str, timeout: int = 10) -> dict[str, Any]:
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            return {"reachable": resp.status_code < 400, "status_code": resp.status_code}
        except Exception as e:
            return {"reachable": False, "error": str(e)}

    def export_csv(self) -> str:
        data, _ = self._repo.list_all(page=1, page_size=10000)
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @property
    def repo(self) -> SourceRepository:
        return self._repo

    @property
    def app_settings(self) -> AppSettingsRepo:
        return self._settings


# Global singleton — lazy init
_instance: Optional[SourceRegistryService] = None


def get_source_registry() -> SourceRegistryService:
    global _instance
    if _instance is None:
        from db.client import get_db
        _instance = SourceRegistryService(db_client=get_db())
    return _instance


source_registry = get_source_registry
