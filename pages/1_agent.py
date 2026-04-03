from __future__ import annotations
import streamlit as st
from typing import Any, Optional
from config import LEGAL_DISCLAIMER
from core.regulations.explorer import get_state_jurisdiction_options
from db.client import get_db


def _get_jurisdiction_options() -> list[dict[str, Any]]:
    try:
        return get_state_jurisdiction_options(get_db())
    except Exception:
        return []


def _format_compliance_markdown(result: Any) -> str:
    lines = [f"**Overall Compliance Score:** {result.overall_score:.0%}\n"]
    if result.issues:
        lines.append(f"### Issues Found ({len(result.issues)})\n")
        for issue in result.issues:
            lines.append(
                f"**Clause {issue.clause_number}** — {issue.violation_type}\n\n"
                f"- **Regulation:** {issue.regulation_cited}\n"
                f"- **Problem:** {issue.description}\n"
                f"- **Fix:** {issue.fix}\n"
                f"- **Suggested revision:** _{issue.suggested_revision}_\n"
            )
    if result.compliant_clauses:
        lines.append(f"\n### Compliant Clauses\n" + ", ".join(result.compliant_clauses))
    lines.append(f"\n---\n_{LEGAL_DISCLAIMER}_")
    return "\n".join(lines)


def _handle_message(
    user_input: str,
    mode: str,
    jurisdiction_id: Optional[int],
    uploaded_file: Any,
) -> str:
    if mode == "Lease Compliance" and uploaded_file is not None:
        from core.compliance.parser import parse_document, extract_clauses
        from core.compliance.checker import ComplianceChecker
        from core.llm.client import llm
        content = parse_document(uploaded_file.read(), uploaded_file.name)
        doc = extract_clauses(content)
        checker = ComplianceChecker(db_client=get_db(), llm_client=llm)
        result = checker.check_compliance(doc.clauses, jurisdiction_id=jurisdiction_id)
        return _format_compliance_markdown(result)

    # Chat Q&A mode
    from core.rag.qa_system import get_qa
    qa = get_qa()
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.get("messages", [])
    ]
    grounded = qa.answer(
        query=user_input,
        jurisdiction_id=jurisdiction_id,
        history=history,
    )
    answer = grounded.uncertainty_prefix + grounded.answer
    return answer


def show_agent_page() -> None:
    st.title("Compliance Agent")

    jur_options = _get_jurisdiction_options()
    jur_map = {f"{j['name']} ({j['type']})": j["id"] for j in jur_options}

    col1, col2 = st.columns([2, 1])
    with col1:
        mode = st.radio("Mode", ["Chat Q&A", "Lease Compliance"], horizontal=True)
    with col2:
        jur_label = st.selectbox("Jurisdiction", options=["All"] + list(jur_map.keys()))
    jurisdiction_id = jur_map.get(jur_label) if jur_label != "All" else None

    uploaded_file = None
    if mode == "Lease Compliance":
        uploaded_file = st.file_uploader("Upload lease (PDF or DOCX)", type=["pdf", "docx"])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a housing regulation question…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                response = _handle_message(prompt, mode, jurisdiction_id, uploaded_file)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


show_agent_page()
