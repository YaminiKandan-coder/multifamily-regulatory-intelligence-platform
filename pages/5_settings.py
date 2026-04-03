from __future__ import annotations
import streamlit as st
from config import settings
from db.client import get_db


def show_settings_page() -> None:
    st.title("Settings")

    # API key status
    st.subheader("API Key Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Anthropic", "✓ Set" if settings.has_anthropic_key else "✗ Missing")
    col2.metric("OpenAI", "✓ Set" if settings.has_openai_key else "✗ Missing")
    col3.metric("Google", "✓ Set" if settings.has_google_key else "✗ Missing")

    st.divider()

    # Provider selection info
    st.subheader("Active Providers")
    st.info(
        f"**Chat provider:** {settings.CHAT_PROVIDER}  \n"
        f"**Embed provider:** {settings.EMBED_PROVIDER}"
    )

    st.divider()

    # Load CSV
    st.subheader("Load Regulations from CSV")
    csv_path = st.text_input("CSV file path", value="data/seeds/sources.csv")
    if st.button("Load CSV"):
        try:
            from core.regulations.scraper import load_regulations_from_csv
            db = get_db()
            count = load_regulations_from_csv(db, csv_path)
            st.success(f"Loaded {count} new regulation(s).")
        except Exception as e:
            st.error(f"Failed: {e}")

    st.divider()

    # Initialize vector index
    st.subheader("Initialize Vector Index")
    if st.button("Run Indexing"):
        try:
            from core.llm.client import llm
            from core.regulations.scraper import ScraperService
            db = get_db()
            svc = ScraperService(db_client=db, llm_client=llm)
            count = svc.initialize_vector_index()
            st.success(f"Indexed {count} chunk(s).")
        except Exception as e:
            st.error(f"Indexing failed: {e}")

    st.divider()

    # Trigger scraper
    st.subheader("Run Scraper")
    if st.button("Scrape & Index"):
        try:
            from core.llm.client import llm
            from core.regulations.scraper import ScraperService
            db = get_db()
            svc = ScraperService(db_client=db, llm_client=llm)
            result = svc.scrape_and_index()
            st.success(f"Scraped: {result['scraped']} | Indexed: {result['indexed']}")
        except Exception as e:
            st.error(f"Scraper failed: {e}")

    st.divider()
    st.page_link("pages/6_source_registry.py", label="Go to Source Registry →")


show_settings_page()
