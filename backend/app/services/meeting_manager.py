from services.meeting_session import MeetingSession


class MeetingManager:
    def __init__(self):
        self.sessions = {}

    async def start_meeting(self, meeting_id: str):
        if meeting_id in self.sessions:
            print(f"[INFO] Meeting {meeting_id} already running")
            return

        session = MeetingSession(meeting_id)
        await session.start()

        self.sessions[meeting_id] = session
        print(f"[INFO] Meeting {meeting_id} started")

    async def stop_meeting(self, meeting_id: str):
        session = self.sessions.pop(meeting_id, None)
        if session:
            await session.stop()
            print(f"[INFO] Meeting {meeting_id} stopped")
            
    async def stop_all(self):
        """
        Gracefully stop ALL active meetings.
        Called during backend shutdown.
        """
        for meeting_id, session in list(self.sessions.items()):
            try:
               await session.stop()
            except Exception as e:
                print(f"[WARN] Failed to stop meeting {meeting_id}: {e}")

        self.sessions.clear()
