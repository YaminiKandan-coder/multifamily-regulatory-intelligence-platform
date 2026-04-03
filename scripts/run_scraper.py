"""Orchestrates: scrape_and_index → check_for_updates → notify_subscribers."""
from __future__ import annotations
from core.regulations.scraper import ScraperService
from core.regulations.update_checker import get_update_checker
from notifications.email_alerts import get_email_alerts
from core.llm.client import llm
from db.client import get_db


def main() -> None:
    db = get_db()

    print("Starting scrape and index…")
    svc = ScraperService(db_client=db, llm_client=llm)
    result = svc.scrape_and_index()
    print(f"Scraped: {result['scraped']} | Indexed: {result['indexed']}")

    print("Checking for regulation updates…")
    checker = get_update_checker()
    updates = checker.check_for_updates()
    print(f"Updates detected: {len(updates)}")

    if updates:
        print("Notifying subscribers…")
        alerts = get_email_alerts()
        total_notified = 0
        for update in updates:
            n = alerts.notify_subscribers({
                "update_summary": update.summary,
                "affected_jurisdictions": update.affected_jurisdictions,
            })
            total_notified += n
        print(f"Notified {total_notified} subscriber(s).")

    print("Done.")


if __name__ == "__main__":
    main()
