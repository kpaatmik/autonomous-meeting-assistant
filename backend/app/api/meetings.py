from fastapi import APIRouter
from datetime import datetime
from app.services.scheduler import scheduler
from app.services.meeting_manager import MeetingManager
from app.storage.meetings import MEETINGS

router = APIRouter()
manager = MeetingManager()
# this meeting dictionary is a simple in-memory store for demo purposes, later it can be replaced with a database

@router.post("/meetings")
async def schedule_meeting(payload: dict):
    meeting_id = payload["meeting_id"]

    MEETINGS[meeting_id] = payload

    scheduler.add_job(
        manager.start_meeting,
        trigger="date",
        run_date=datetime.fromisoformat(payload["start_time"]),
        args=[meeting_id],
        id=f"meeting_{meeting_id}"
    )

    return {"status": "scheduled", "meeting_id": meeting_id}
