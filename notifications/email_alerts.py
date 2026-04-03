from __future__ import annotations
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Optional
from config import settings


def _smtp_send(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        # Fallback: write to local emails/ folder
        os.makedirs("emails", exist_ok=True)
        safe = to.replace("@", "_at_").replace(".", "_")
        path = f"emails/{safe}_{subject[:30].replace(' ', '_')}.txt"
        with open(path, "w") as f:
            f.write(f"To: {to}\nSubject: {subject}\n\n{body}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_EMAIL, to, msg.as_string())


class EmailAlertsService:
    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    def subscribe(self, email: str, jurisdiction_id: int) -> bool:
        try:
            self._db.table("email_subscriptions").upsert({
                "email": email,
                "jurisdiction_id": jurisdiction_id,
                "is_active": True,
            }, on_conflict="email,jurisdiction_id").execute()
            self._send_welcome(email)
            return True
        except Exception:
            return False

    def unsubscribe(self, email: str, jurisdiction_id: int) -> bool:
        try:
            self._db.table("email_subscriptions").update(
                {"is_active": False}
            ).eq("email", email).eq("jurisdiction_id", jurisdiction_id).execute()
            return True
        except Exception:
            return False

    def _send_welcome(self, email: str) -> None:
        _smtp_send(
            to=email,
            subject="Subscribed to Housing Regulation Alerts",
            body=(
                "You have successfully subscribed to housing regulation update alerts.\n\n"
                "You will receive notifications when regulations in your selected jurisdictions change.\n\n"
                "This is for informational purposes only and is not legal advice."
            ),
        )

    def notify_subscribers(self, update: dict[str, Any]) -> int:
        jurisdiction_ids = update.get("affected_jurisdictions", [])
        if not jurisdiction_ids:
            return 0

        resp = self._db.table("email_subscriptions").select("email").eq(
            "is_active", True
        ).in_("jurisdiction_id", jurisdiction_ids).execute()

        emails = list({row["email"] for row in (resp.data or [])})
        summary = update.get("update_summary", "A regulation update was detected.")

        for email in emails:
            _smtp_send(
                to=email,
                subject="Housing Regulation Update Alert",
                body=(
                    f"A regulation update has been detected:\n\n{summary}\n\n"
                    "This is for informational purposes only and is not legal advice."
                ),
            )
        return len(emails)

    def send_daily_digest(self, updates: list[dict[str, Any]]) -> None:
        if not updates:
            return
        resp = self._db.table("email_subscriptions").select("email").eq(
            "is_active", True
        ).execute()
        emails = list({row["email"] for row in (resp.data or [])})
        body = "Daily Housing Regulation Digest\n\n"
        for u in updates:
            body += f"- {u.get('update_summary', '')}\n"
        body += "\nThis is for informational purposes only and is not legal advice."
        for email in emails:
            _smtp_send(to=email, subject="Daily Housing Regulation Digest", body=body)

    def get_subscriptions(self) -> list[dict[str, Any]]:
        resp = self._db.table("email_subscriptions").select("*").eq(
            "is_active", True
        ).execute()
        return resp.data or []


# Global singleton — lazy init
_instance: Optional[EmailAlertsService] = None


def get_email_alerts() -> EmailAlertsService:
    global _instance
    if _instance is None:
        from db.client import get_db
        _instance = EmailAlertsService(db_client=get_db())
    return _instance


email_alerts = get_email_alerts
