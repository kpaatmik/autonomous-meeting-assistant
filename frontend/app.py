import streamlit as st
import requests
from datetime import datetime

API = "http://localhost:8000"

st.title("🧠 Autonomous Meeting Assistant")

tab1, tab2 = st.tabs(["Schedule Meeting", "Post Meeting Intelligence"])

# ======================
# SCHEDULE TAB
# ======================

with tab1:

    st.header("Schedule Meeting")

    meeting_id = st.text_input("Meeting ID")
    meeting_url = st.text_input("Meeting URL")
    bot_name = st.text_input("Bot Name", "AI Assistant")
    start_time = st.datetime_input("Start Time")

    if st.button("Schedule"):

        payload = {
            "meeting_id": meeting_id,
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "start_time": start_time.isoformat()
        }

        res = requests.post(f"{API}/meetings/schedule", json=payload)

        st.success(res.json())


# ======================
# POST MEETING TAB
# ======================

with tab2:

    st.header("Meeting Intelligence")

    meeting_id2 = st.text_input("Meeting ID for Analysis")

    if st.button("Summarize Meeting"):

        res = requests.get(f"{API}/meetings/{meeting_id2}/summary")
        st.subheader("Summary")
        st.write(res.json()["summary"])

    st.subheader("Ask Bot")

    question = st.text_input("Ask about meeting")

    if st.button("Ask"):

        res = requests.post(
            f"{API}/meetings/{meeting_id2}/ask",
            json={"question": question}
        )

        st.write(res.json()["answer"])