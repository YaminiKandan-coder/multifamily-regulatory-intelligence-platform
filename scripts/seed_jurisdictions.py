"""Seeds federal jurisdiction, all 50 US states, and 5 TX cities."""
from __future__ import annotations
from db.client import get_db

STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"),
]

TX_CITIES = ["Dallas", "Houston", "Austin", "San Antonio", "Fort Worth"]


def seed() -> None:
    db = get_db()

    # Federal
    db.table("jurisdictions").upsert(
        {"type": "federal", "name": "Federal"},
        on_conflict="type,name",
    ).execute()

    # States
    for code, name in STATES:
        db.table("jurisdictions").upsert(
            {"type": "state", "name": name, "state_code": code},
            on_conflict="type,name",
        ).execute()

    # TX cities
    tx_resp = db.table("jurisdictions").select("id").eq("type", "state").eq("name", "Texas").single().execute()
    tx_id = tx_resp.data["id"]
    for city in TX_CITIES:
        db.table("jurisdictions").upsert(
            {"type": "city", "name": city, "state_code": "TX", "parent_id": tx_id},
            on_conflict="type,name",
        ).execute()

    print("Jurisdictions seeded.")


if __name__ == "__main__":
    seed()
