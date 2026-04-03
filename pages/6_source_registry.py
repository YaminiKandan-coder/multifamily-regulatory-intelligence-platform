from __future__ import annotations
import streamlit as st
from db.client import get_db
from core.regulations.source_registry import get_source_registry


def show_source_registry_page() -> None:
    st.title("Source Registry")

    registry = get_source_registry()

    if not registry.repo.table_exists():
        st.error("regulation_sources table not found. Run migration 007 first.")
        return

    # Toggle DB vs CSV
    enabled = registry.is_enabled()
    new_enabled = st.toggle("Use DB source registry (instead of CSV)", value=enabled)
    if new_enabled != enabled:
        registry.toggle(new_enabled)
        st.success(f"Source registry {'enabled' if new_enabled else 'disabled'}.")

    st.divider()

    # Metrics
    _, total = registry.repo.list_all(page=1, page_size=1)
    _, active_total = registry.repo.list_all(page=1, page_size=1, is_active=True)
    col1, col2 = st.columns(2)
    col1.metric("Total Sources", total)
    col2.metric("Active Sources", active_total)

    st.divider()

    # Search & filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Search", placeholder="name or URL")
    with col2:
        state_filter = st.text_input("State code", placeholder="e.g. TX")
    with col3:
        active_filter = st.selectbox("Status", ["All", "Active", "Inactive"])

    is_active_val = None if active_filter == "All" else (active_filter == "Active")
    page = st.number_input("Page", min_value=1, value=1, step=1)

    data, count = registry.repo.list_all(
        page=page,
        page_size=20,
        state_code=state_filter or None,
        is_active=is_active_val,
        search=search or None,
    )

    st.caption(f"{count} total sources")

    if data:
        for src in data:
            with st.expander(f"{src.get('source_name', src.get('url', ''))} — {src.get('state_code', '')}"):
                st.json(src)
                col_a, col_b, col_c = st.columns(3)
                if col_a.button("Test URL", key=f"test_{src['id']}"):
                    result = registry.test_source(src.get("url", ""))
                    if result.get("reachable"):
                        st.success(f"Reachable (HTTP {result.get('status_code')})")
                    else:
                        st.error(f"Unreachable: {result.get('error', '')}")
                if col_b.button("Deactivate" if src.get("is_active") else "Activate", key=f"toggle_{src['id']}"):
                    registry.repo.bulk_set_active([src["id"]], not src.get("is_active"))
                    st.rerun()
                if col_c.button("Delete", key=f"del_{src['id']}"):
                    registry.repo.delete(src["id"])
                    st.rerun()

    st.divider()

    # Add new source
    st.subheader("Add Source")
    with st.form("add_source_form"):
        new_name = st.text_input("Source name")
        new_url = st.text_input("URL")
        new_jur = st.number_input("Jurisdiction ID", min_value=1, step=1)
        new_state = st.text_input("State code (optional)")
        new_cat = st.text_input("Category", value="General")
        add_submitted = st.form_submit_button("Add")
        if add_submitted and new_url:
            registry.repo.upsert_by_url({
                "jurisdiction_id": int(new_jur),
                "source_name": new_name,
                "url": new_url,
                "domain": "housing",
                "category": new_cat,
                "state_code": new_state or None,
                "is_active": True,
            })
            st.success("Source added.")
            st.rerun()

    st.divider()

    # CSV import / export
    st.subheader("CSV Import / Export")
    uploaded = st.file_uploader("Import CSV", type=["csv"])
    if uploaded and st.button("Import"):
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        count = registry.backfill_from_csv(tmp_path)
        os.unlink(tmp_path)
        st.success(f"Imported {count} new source(s).")

    if st.button("Export CSV"):
        csv_data = registry.export_csv()
        st.download_button("Download", data=csv_data, file_name="regulation_sources.csv", mime="text/csv")


show_source_registry_page()
