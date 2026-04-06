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

    meetings_res = requests.get(f"{API}/meetings", params={"status": "scheduled"})
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

    st.header("Post Meeting Intelligence")

    completed_res = requests.get(f"{API}/meetings", params={"status": "completed"})
    completed_meetings = completed_res.json().get("meetings", []) if completed_res.ok else []

    if not completed_meetings:
        st.info("No completed meetings found. Once a meeting is finished, it will appear here.")
    else:
        meeting_ids = [meeting["meeting_id"] for meeting in completed_meetings]
        selected_meeting_id = st.selectbox("Select completed meeting", meeting_ids)

        if selected_meeting_id:
            selected_meeting = next((m for m in completed_meetings if m["meeting_id"] == selected_meeting_id), None)
            if selected_meeting:
                st.subheader(f"Meeting: {selected_meeting_id}")
                st.write(f"**Meeting URL:** {selected_meeting.get('meeting_url', 'N/A')}")
                st.write(f"**Bot Name:** {selected_meeting.get('bot_name', 'AI Assistant')}")
                st.write(f"**Start Time:** {selected_meeting.get('start_time', 'N/A')}")
                st.write(f"**Status:** {selected_meeting.get('status', 'completed')}")
                st.write("**Pre-Meeting Topics:**")
                for topic in selected_meeting.get("pre_intents", []):
                    st.write(f"- {topic}")

                st.markdown("---")
                st.subheader("Summary")
                if st.button("Summarize This Meeting", key=f"summarize_{selected_meeting_id}"):
                    res = requests.get(f"{API}/meetings/{selected_meeting_id}/summary")
                    if res.ok:
                        st.success("Summary loaded")
                        st.write(res.json().get("summary", "No summary available."))
                    else:
                        st.error(f"Failed to load summary: {res.text}")

                st.markdown("---")
                st.subheader("Chat About This Meeting")
                question = st.text_input("Ask a question", key=f"question_{selected_meeting_id}")

                if st.button("Ask", key=f"ask_{selected_meeting_id}"):
                    if not question:
                        st.warning("Please enter a question before asking.")
                    else:
                        res = requests.post(
                            f"{API}/meetings/{selected_meeting_id}/ask",
                            json={"question": question}
                        )
                        if res.ok:
                            st.write(res.json().get("answer", "No answer returned."))
                        else:
                            st.error(f"Failed to ask question: {res.text}")
