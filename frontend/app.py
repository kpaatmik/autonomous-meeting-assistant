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
    pre_intents_input = st.text_area(
        "Pre-Meeting Topics",
        help="Enter one agenda item or context line per row. These will be used to guide the assistant during the meeting."
    )

    if st.button("Schedule"):
        pre_intents = [line.strip() for line in pre_intents_input.splitlines() if line.strip()]
        payload = {
            "meeting_id": meeting_id,
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "start_time": start_time.isoformat(),
            "pre_intents": pre_intents
        }

        res = requests.post(f"{API}/meetings/schedule", json=payload)

        if res.status_code == 200:
            st.success("Meeting scheduled successfully")
        else:
            st.error(f"Failed to schedule meeting: {res.text}")

    st.markdown("---")
    st.subheader("Upcoming Meetings")

    meetings_res = requests.get(f"{API}/meetings")
    meetings = meetings_res.json().get("meetings", []) if meetings_res.ok else []

    if not meetings:
        st.info("No upcoming meetings found.")
    else:
        for meeting in meetings:
            with st.expander(f"{meeting['meeting_id']} — {meeting.get('start_time', 'No time')}", expanded=False):
                st.write(f"**Meeting URL:** {meeting.get('meeting_url', 'N/A')}")
                st.write(f"**Bot Name:** {meeting.get('bot_name', 'AI Assistant')}")
                st.write(f"**Start Time:** {meeting.get('start_time', 'N/A')}")

                existing_pre_intents = meeting.get("pre_intents", [])
                pre_intents_text = st.text_area(
                    "Pre-Meeting Topics",
                    value="\n".join(existing_pre_intents),
                    key=f"preintents_{meeting['meeting_id']}"
                )

                if st.button("Save Pre-Intents", key=f"save_preintents_{meeting['meeting_id']}"):
                    updated_pre_intents = [line.strip() for line in pre_intents_text.splitlines() if line.strip()]
                    update_res = requests.put(
                        f"{API}/meetings/{meeting['meeting_id']}/preintents",
                        json={"pre_intents": updated_pre_intents}
                    )
                    if update_res.ok:
                        st.success("Pre-intents updated")
                    else:
                        st.error(f"Failed to update pre-intents: {update_res.text}")


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
