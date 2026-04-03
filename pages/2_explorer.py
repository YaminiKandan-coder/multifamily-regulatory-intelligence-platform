from __future__ import annotations
import streamlit as st
from db.client import get_db
from core.llm.client import llm
from core.regulations.explorer import (
    get_state_jurisdiction_options,
    get_distinct_categories,
    get_explorer_metrics,
    search_regulations,
    to_results_dataframe,
)


def show_explorer_page() -> None:
    st.title("Regulation Explorer")

    db = get_db()

    # Metrics
    try:
        metrics = get_explorer_metrics(db)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Regulations", metrics["total_regulations"])
        c2.metric("Jurisdictions", metrics["total_jurisdictions"])
        c3.metric("Indexed", metrics["indexed_regulations"])
    except Exception as e:
        st.warning(f"Could not load metrics: {e}")

    st.divider()

    # Search controls
    query = st.text_input("Search regulations", placeholder="e.g. ESA deposit rules")

    jur_options = get_state_jurisdiction_options(db)
    jur_map = {f"{j['name']} ({j['type']})": j["id"] for j in jur_options}
    col1, col2 = st.columns(2)
    with col1:
        jur_label = st.selectbox("Location", ["All"] + list(jur_map.keys()))
    with col2:
        categories = ["All"] + get_distinct_categories(db)
        category = st.selectbox("Category", categories)

    jurisdiction_id = jur_map.get(jur_label) if jur_label != "All" else None
    category_val = category if category != "All" else None

    if query:
        with st.spinner("Searching…"):
            results = search_regulations(
                db_client=db,
                llm_client=llm,
                query=query,
                jurisdiction_id=jurisdiction_id,
                category=category_val,
            )
        if not results:
            st.info("No results found.")
        else:
            df = to_results_dataframe(results)
            st.dataframe(df, use_container_width=True)
            for r in results:
                meta = r.get("metadata") or {}
                with st.expander(f"{meta.get('source_name', 'Source')} — {meta.get('category', '')}"):
                    st.write(r.get("chunk_text", ""))
                    if meta.get("url"):
                        st.markdown(f"[Source]({meta['url']})")


show_explorer_page()
