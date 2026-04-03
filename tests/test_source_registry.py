from __future__ import annotations
import pytest
import tempfile
import os
import csv
from unittest.mock import MagicMock
from core.regulations.source_registry import AppSettingsRepo, SourceRepository, SourceRegistryService


class FakeSettingsTable:
    def __init__(self):
        self._store: dict[str, str] = {}

    def table(self, name):
        return self

    def select(self, *args, **kwargs):
        return self

    def upsert(self, data, **kwargs):
        self._store[data["key"]] = data["value"]
        return self

    def delete(self):
        return self

    def eq(self, col, val):
        self._val = val
        return self

    def single(self):
        return self

    def execute(self):
        result = MagicMock()
        result.data = {"value": self._store.get(getattr(self, "_val", ""), None)}
        return result


class FakeSourceTable:
    def __init__(self):
        self._store: list[dict] = []
        self._next_id = 1

    def table(self, name):
        return self

    def select(self, *args, **kwargs):
        self._count = len(self._store)
        return self

    def upsert(self, data, **kwargs):
        url = data.get("url")
        for i, r in enumerate(self._store):
            if r.get("url") == url:
                self._store[i] = {**r, **data}
                return self
        data["id"] = self._next_id
        self._next_id += 1
        self._store.append(data)
        return self

    def delete(self):
        return self

    def eq(self, col, val):
        self._eq_col = col
        self._eq_val = val
        return self

    def single(self):
        return self

    def in_(self, col, vals):
        return self

    def limit(self, n):
        return self

    def range(self, start, end):
        return self

    def execute(self):
        result = MagicMock()
        col = getattr(self, "_eq_col", None)
        val = getattr(self, "_eq_val", None)
        if col and val is not None:
            data = [r for r in self._store if r.get(col) == val]
        else:
            data = self._store[:]
        result.data = data
        result.count = len(data)
        return result


def _make_fake_db():
    db = MagicMock()
    fake_settings = FakeSettingsTable()
    fake_sources = FakeSourceTable()

    def table_router(name):
        if name == "app_settings":
            return fake_settings
        return fake_sources

    db.table.side_effect = table_router
    return db, fake_settings, fake_sources


def test_app_settings_crud():
    db, fake_settings, _ = _make_fake_db()
    repo = AppSettingsRepo(db)
    repo.set("use_db_source_registry", "true")
    assert fake_settings._store.get("use_db_source_registry") == "true"


def test_app_settings_get_bool():
    db, fake_settings, _ = _make_fake_db()
    fake_settings._store["use_db_source_registry"] = "true"
    repo = AppSettingsRepo(db)
    assert repo.get_bool("use_db_source_registry") is True


def test_source_repository_upsert_idempotent():
    db, _, fake_sources = _make_fake_db()
    repo = SourceRepository(db)
    data = {"url": "https://example.gov/reg", "source_name": "Test", "jurisdiction_id": 1, "domain": "housing", "category": "General", "is_active": True}
    repo.upsert_by_url(data)
    repo.upsert_by_url(data)  # second call should update, not duplicate
    assert len(fake_sources._store) == 1


def test_source_registry_toggle():
    db, fake_settings, _ = _make_fake_db()
    svc = SourceRegistryService(db)
    svc.toggle(True)
    assert fake_settings._store.get("use_db_source_registry") == "true"
    svc.toggle(False)
    assert fake_settings._store.get("use_db_source_registry") == "false"


def test_backfill_from_csv_idempotent():
    db, _, fake_sources = _make_fake_db()
    svc = SourceRegistryService(db)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "source_name", "jurisdiction_id", "domain", "category", "state_code"])
        writer.writeheader()
        writer.writerow({"url": "https://example.gov/1", "source_name": "Test", "jurisdiction_id": "1", "domain": "housing", "category": "General", "state_code": "TX"})
        tmp_path = f.name

    try:
        count1 = svc.backfill_from_csv(tmp_path)
        count2 = svc.backfill_from_csv(tmp_path)  # second run — no new inserts
        assert count1 == 1
        assert count2 == 0
    finally:
        os.unlink(tmp_path)


def test_test_source_unreachable():
    db, _, _ = _make_fake_db()
    svc = SourceRegistryService(db)
    result = svc.test_source("http://localhost:1")  # port nothing listens on
    assert result["reachable"] is False
