from app.services.meeting_session import MeetingSession
from app.services.bot_launcher import launch_bot

class MeetingManager:
    def __init__(self):
        self.sessions = {}

    def start_meeting(self, meeting):
        meeting_id = meeting["meeting_id"]

        if meeting_id in self.sessions:
            return

        # 1️⃣ Launch bot
        launch_bot(meeting)

        # 2️⃣ Start isolated pipeline
        session = MeetingSession(meeting_id)
        session.start()

        self.sessions[meeting_id] = session

    def stop_meeting(self, meeting_id):
        session = self.sessions.pop(meeting_id, None)
        if session:
            session.stop()
