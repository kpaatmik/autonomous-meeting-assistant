from services.persistence import get_persistence
from services.llm_client import generate

persistence = get_persistence()

async def summarize_meeting(meeting_id: str):

    rows = persistence.conn.execute(
        "SELECT text FROM segments WHERE meeting_id=?",
        (meeting_id,)
    ).fetchall()

    if not rows:
        return "No transcript available."

    full_text = " ".join([r[0] for r in rows])

    prompt = f"""
    Summarize this meeting clearly with:
    - key decisions
    - action items
    - important discussion points

    Transcript:
    {full_text}
    """

    summary = await generate(prompt)

    return summary