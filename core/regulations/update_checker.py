from __future__ import annotations
import hashlib
from datetime import datetime
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field
from core.llm.prompts import UPDATE_SUMMARY_PROMPT


class UpdateResult(BaseModel):
    regulation_id: int
    changed: bool
    old_hash: str = ""
    new_hash: str = ""
    summary: str = ""
    affected_jurisdictions: list[int] = Field(default_factory=list)


def _default_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class UpdateChecker:
    def __init__(
        self,
        db_client: Any,
        llm_client: Any,
        http_get: Optional[Callable[[str], str]] = None,
        hash_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._db = db_client
        self._llm = llm_client
        self._http_get = http_get or self._default_http_get
        self._hash = hash_fn or _default_sha256

    @staticmethod
    def _default_http_get(url: str) -> str:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=15, headers={"User-Agent": "ComplianceBot/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator="\n")

    def check_single(self, regulation_id: int) -> UpdateResult:
        resp = self._db.table("regulations").select(
            "id,url,content,content_hash,jurisdiction_id"
        ).eq("id", regulation_id).single().execute()
        reg = resp.data
        if not reg:
            return UpdateResult(regulation_id=regulation_id, changed=False)

        try:
            new_content = self._http_get(reg["url"])
        except Exception:
            return UpdateResult(regulation_id=regulation_id, changed=False)

        new_hash = self._hash(new_content)
        old_hash = reg.get("content_hash", "")

        if new_hash == old_hash:
            return UpdateResult(regulation_id=regulation_id, changed=False, old_hash=old_hash, new_hash=new_hash)

        # Generate summary
        summary = ""
        try:
            user_prompt = f"Old text:\n{reg['content'][:2000]}\n\nNew text:\n{new_content[:2000]}"
            summary = self._llm.ask(UPDATE_SUMMARY_PROMPT, user_prompt)
        except Exception:
            summary = "Regulation content has changed."

        # Store update record
        try:
            self._db.table("regulation_updates").insert({
                "regulation_id": regulation_id,
                "update_summary": summary,
                "affected_jurisdictions": [reg["jurisdiction_id"]],
                "detected_at": datetime.utcnow().isoformat(),
            }).execute()
            # Deactivate old, insert new version
            self._db.table("regulations").update({"is_current": False}).eq("id", regulation_id).execute()
            self._db.table("regulations").insert({
                "jurisdiction_id": reg["jurisdiction_id"],
                "domain": "housing",
                "category": "General",
                "source_name": "",
                "url": reg["url"],
                "content": new_content,
                "content_hash": new_hash,
                "version": 2,
                "is_current": True,
            }).execute()
        except Exception:
            pass

        return UpdateResult(
            regulation_id=regulation_id,
            changed=True,
            old_hash=old_hash,
            new_hash=new_hash,
            summary=summary,
            affected_jurisdictions=[reg["jurisdiction_id"]],
        )

    def check_for_updates(self) -> list[UpdateResult]:
        resp = self._db.table("regulations").select("id").eq("is_current", True).execute()
        ids = [r["id"] for r in (resp.data or [])]
        results = []
        for reg_id in ids:
            result = self.check_single(reg_id)
            if result.changed:
                results.append(result)
        return results


# Global singleton — lazy init
_instance: Optional[UpdateChecker] = None


def get_update_checker() -> UpdateChecker:
    global _instance
    if _instance is None:
        from db.client import get_db
        from core.llm.client import llm
        _instance = UpdateChecker(db_client=get_db(), llm_client=llm)
    return _instance


update_checker = get_update_checker
