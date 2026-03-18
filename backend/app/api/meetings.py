from fastapi import APIRouter
from datetime import datetime
import pytz

from services.scheduler import get_scheduler
from services.meeting_manager import manager
from storage.meetings import MEETINGS
from services.summary_service import summarize_meeting
from services.rag_service import ask_meeting

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

from services.persistence import get_persistence

@router.get("/{meeting_id}/search")
async def search_meeting(meeting_id: str, q: str, top_k: int = 5):
    persistence = get_persistence()
    results = persistence.search(meeting_id, q, top_k=top_k)

    out = []
    for row, similarity in results:
        out.append({
            "id": row[0],
            "meeting_id": row[1],
            "speaker": row[2],
            "start": row[3],
            "end": row[4],
            "text": row[5],
            "similarity": similarity
        })

    #  Cosine similarity → higher is better
    out.sort(key=lambda x: x["similarity"], reverse=True)

    return {"results": out}








@router.get("/{meeting_id}/summary")
async def meeting_summary(meeting_id: str):

    summary = await summarize_meeting(meeting_id)

    return {
        "meeting_id": meeting_id,
        "summary": summary
    }

@router.post("/{meeting_id}/ask")
async def ask_bot(meeting_id: str, payload: dict):

    question = payload.get("question")

    if not question:
        return {"error": "question missing"}

    answer = await ask_meeting(meeting_id, question)

    return {
        "meeting_id": meeting_id,
        "question": question,
        "answer": answer
    }