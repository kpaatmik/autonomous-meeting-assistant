from fastapi import APIRouter
from datetime import datetime
from app.services.scheduler import scheduler
from app.services.meeting_manager import MeetingManager

router = APIRouter()
manager = MeetingManager()

MEETINGS = {}

@router.post("/meetings")
async def schedule_meeting(payload: dict):
    meeting_id = payload["meeting_id"]

    MEETINGS[meeting_id] = payload

    scheduler.add_job(
        manager.start_meeting,
        trigger="date",
        run_date=datetime.fromisoformat(payload["start_time"]),
        args=[payload],
        id=f"meeting_{meeting_id}"
    )

    return {"status": "scheduled", "meeting_id": meeting_id}
