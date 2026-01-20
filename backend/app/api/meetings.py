from fastapi import APIRouter
from datetime import datetime
import pytz

from services.scheduler import get_scheduler
from services.meeting_manager import manager
from storage.meetings import MEETINGS

router = APIRouter(prefix="/meetings", tags=["Meetings"])

IST = pytz.timezone("Asia/Kolkata")

@router.post("/schedule")
async def schedule_meeting(payload: dict):
    meeting_id = payload["meeting_id"]

    MEETINGS[meeting_id] = payload

    # 🔑 FIX: parse + localize time
    start_time = datetime.fromisoformat(payload["start_time"])
    start_time = IST.localize(start_time)

    scheduler = get_scheduler()
    scheduler.add_job(
        manager.start_meeting_job,      # sync entry point (correct)
        trigger="date",
        run_date=start_time,            # timezone-aware
        args=[meeting_id],
        id=f"meeting_{meeting_id}",
        replace_existing=True
    )

    print(f"[SCHEDULED] {meeting_id} at {start_time}")

    return {"status": "scheduled", "meeting_id": meeting_id}
