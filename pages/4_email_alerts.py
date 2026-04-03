from __future__ import annotations
import streamlit as st
from db.client import get_db
from notifications.email_alerts import get_email_alerts
from core.regulations.explorer import get_state_jurisdiction_options


def show_email_alerts_page() -> None:
    st.title("Email Alerts")

    db = get_db()
    alerts = get_email_alerts()

    jur_options = get_state_jurisdiction_options(db)
    jur_map = {f"{j['name']} ({j['type']})": j["id"] for j in jur_options}

    st.subheader("Subscribe")
    with st.form("subscribe_form"):
        email = st.text_input("Email address")
        jur_label = st.selectbox("Jurisdiction", list(jur_map.keys()))
        submitted = st.form_submit_button("Subscribe")
        if submitted and email and jur_label:
            success = alerts.subscribe(email, jur_map[jur_label])
            if success:
                st.success(f"Subscribed {email} to {jur_label} alerts.")
            else:
                st.error("Subscription failed. Please try again.")

    st.divider()
    st.subheader("Unsubscribe")
    with st.form("unsubscribe_form"):
        unsub_email = st.text_input("Email address", key="unsub_email")
        unsub_jur = st.selectbox("Jurisdiction", list(jur_map.keys()), key="unsub_jur")
        unsub_submitted = st.form_submit_button("Unsubscribe")
        if unsub_submitted and unsub_email:
            success = alerts.unsubscribe(unsub_email, jur_map[unsub_jur])
            if success:
                st.success(f"Unsubscribed {unsub_email}.")
            else:
                st.error("Unsubscribe failed.")

    st.divider()
    st.subheader("Active Subscriptions")
    try:
        subs = alerts.get_subscriptions()
        if subs:
            for s in subs:
                st.text(f"{s.get('email')} — jurisdiction {s.get('jurisdiction_id')}")
        else:
            st.info("No active subscriptions.")
    except Exception as e:
        st.error(f"Could not load subscriptions: {e}")


show_email_alerts_page()
