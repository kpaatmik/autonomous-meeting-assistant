from app.services.meeting_session import MeetingSession
from app.services.bot_launcher import launch_bot

class MeetingManager:
    def __init__(self):
        self.sessions = {}

    def start_meeting(self, meeting_id: str):
        if meeting_id in self.sessions:
            print(f"[INFO] Meeting {meeting_id} already running")
            return

        session = MeetingSession(meeting_id)
        session.start()

        self.sessions[meeting_id] = session
        print(f"[INFO] Meeting {meeting_id} started")

    def stop_meeting(self, meeting_id: str):
        session = self.sessions.pop(meeting_id, None)
        if session:
            session.stop()
            print(f"[INFO] Meeting {meeting_id} stopped")
            
    def stop_all(self):
        """
        Gracefully stop ALL active meetings.
        Called during backend shutdown.
        """
        for meeting_id, session in list(self.sessions.items()):
            try:
                session.stop()
            except Exception as e:
                print(f"[WARN] Failed to stop meeting {meeting_id}: {e}")

        self.sessions.clear()
