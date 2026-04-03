from __future__ import annotations
import streamlit as st
from db.client import get_db
from core.regulations.update_checker import get_update_checker
from core.regulations.explorer import get_state_jurisdiction_options


def show_update_log_page() -> None:
    st.title("Regulation Update Log")

    db = get_db()

    # State filter
    jur_options = get_state_jurisdiction_options(db)
    state_options = sorted({
        j["state_code"] for j in jur_options if j.get("state_code")
    })
    selected_state = st.selectbox("Filter by state", ["All"] + state_options)

    if st.button("Check for Updates Now"):
        with st.spinner("Checking all sources for changes…"):
            checker = get_update_checker()
            results = checker.check_for_updates()
        if results:
            st.success(f"{len(results)} update(s) detected.")
        else:
            st.info("No changes detected.")

    st.divider()

    # Load update log
    try:
        query = db.table("regulation_updates").select(
            "id,regulation_id,update_summary,affected_jurisdictions,detected_at"
        ).order("detected_at", desc=True)
        resp = query.execute()
        updates = resp.data or []
    except Exception as e:
        st.error(f"Could not load update log: {e}")
        return

    if not updates:
        st.info("No updates recorded yet.")
        return

    # Deduplicate by source URL via regulation_id lookup
    seen_reg_ids: set[int] = set()
    for update in updates:
        reg_id = update.get("regulation_id")
        if reg_id in seen_reg_ids:
            continue
        seen_reg_ids.add(reg_id)

        detected = update.get("detected_at", "")[:10]
        summary = update.get("update_summary", "No summary available.")
        with st.expander(f"Update {update['id']} — {detected}"):
            st.write(summary)
            st.caption(f"Regulation ID: {reg_id} | Jurisdictions: {update.get('affected_jurisdictions', [])}")


show_update_log_page()
