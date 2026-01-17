from services.meeting_session import MeetingSession
import asyncio
from services.scheduler import get_event_loop



class MeetingManager:
    def __init__(self):
        self.sessions = {}

    def start_meeting_job(self, meeting_id: str):
        """
        APScheduler SAFE ENTRY POINT (SYNC)
        """
        print(f"[SCHEDULER] Triggered meeting {meeting_id}")
        print(f"[SCHEDULER] Triggered meeting {meeting_id}")

        loop = get_event_loop()
        if loop is None:
            print("[ERROR] No event loop available")
            return

        asyncio.run_coroutine_threadsafe(
            self.start_meeting(meeting_id),
            loop
        )

    async def start_meeting(self, meeting_id: str):
        if meeting_id in self.sessions:
            print(f"[INFO] Meeting {meeting_id} already running")
            return

        session = MeetingSession(meeting_id)
        self.sessions[meeting_id] = session

        await session.start()
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


manager = MeetingManager()