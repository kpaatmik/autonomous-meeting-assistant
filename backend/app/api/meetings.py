from fastapi import APIRouter
from datetime import datetime
import pytz
from services.flan_qa_service import get_flan_qa_bot
from services.flan_summarizer import get_flan_summarizer
from services.persistence import get_persistence

from services.scheduler import get_scheduler
from services.meeting_manager import manager
from storage.meetings import MEETINGS
#from services.summary_service import get_summarizer
# from app.services.rag_service import ask_meeting

router = APIRouter(prefix="/meetings", tags=["Meetings"])

IST = pytz.timezone("Asia/Kolkata")


@router.get("/")
async def list_meetings(status: str = None):
    persistence = get_persistence()
    meetings = persistence.list_meeting_metadata(status=status)
    return {"meetings": meetings}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str):
    persistence = get_persistence()
    meeting = persistence.get_meeting_metadata(meeting_id)
    if not meeting:
        return {"error": "Meeting not found"}
    return meeting


@router.post("/schedule")
async def schedule_meeting(payload: dict):
    meeting_id = payload["meeting_id"]

    meeting_payload = {
        "meeting_id": meeting_id,
        "meeting_url": payload.get("meeting_url"),
        "bot_name": payload.get("bot_name", "AI Bot"),
        "start_time": payload.get("start_time"),
        "pre_intents": payload.get("pre_intents", []),
    }

    MEETINGS[meeting_id] = meeting_payload
    persistence = get_persistence()
    persistence.save_meeting_metadata(
        meeting_id,
        meeting_payload["meeting_url"],
        meeting_payload["bot_name"],
        meeting_payload["start_time"],
        status="scheduled",
        pre_intents=meeting_payload["pre_intents"]
    )

    # 🔑 FIX: parse + localize time
    start_time = datetime.fromisoformat(meeting_payload["start_time"])
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


@router.put("/{meeting_id}/preintents")
async def update_preintents(meeting_id: str, payload: dict):
    meeting = MEETINGS.get(meeting_id)
    if not meeting:
        return {"error": "Meeting not found"}

    pre_intents = payload.get("pre_intents", [])
    if not isinstance(pre_intents, list):
        return {"error": "pre_intents must be a list"}

    pre_intents_clean = [str(item).strip() for item in pre_intents if str(item).strip()]
    meeting["pre_intents"] = pre_intents_clean

    persistence = get_persistence()
    persistence.update_meeting_metadata(meeting_id, pre_intents=pre_intents_clean)

    return {"status": "updated", "meeting_id": meeting_id, "pre_intents": pre_intents_clean}

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

    persistence = get_persistence()
    summarizer = get_flan_summarizer()

    rows = persistence.get_all_segments(meeting_id)

    output = summarizer.summarize_meeting(rows)

    return output

"""

@router.get("/{meeting_id}/summary")
async def meeting_summary(meeting_id: str):
    persistence = get_persistence()
    summarizer = get_flan_summarizer()

    # fetch all segments
    results = persistence.search(meeting_id, "", top_k=1000)

    rows = [r[0] for r in results]

    output = summarizer.summarize_meeting(rows)

    return output


@router.get("/{meeting_id}/summary")
async def get_summary(meeting_id: str):
    summarizer = get_summarizer()
    result = summarizer.summarize_meeting(meeting_id)
    return result




@router.get("/{meeting_id}/summary")
async def meeting_summary(meeting_id: str):

    persistence = get_persistence()
    summarizer = get_flan_summarizer()

    rows = persistence.get_all_segments(meeting_id)

    output = summarizer.summarize_meeting(rows)

    return output


@router.post("/{meeting_id}/ask")
async def ask_meeting_question(meeting_id: str, payload: dict):

    question = payload.get("question")

    if not question:
        return {"error": "question required"}

    qa_bot = get_flan_qa_bot()

    result = qa_bot.answer_question(meeting_id, question)

    return result

"""
@router.post("/{meeting_id}/ask")
async def ask_meeting_question(meeting_id: str, payload: dict):

    question = payload.get("question")

    if not question:
        return {"error": "question required"}

    qa_bot = get_flan_qa_bot()

    result = qa_bot.answer_question(meeting_id, question)

    return result
