import asyncio
import subprocess
import json
from pathlib import Path
from storage.meetings import MEETINGS

BOT_PATH = Path(__file__).resolve().parents[3] / "bot" / "bot.js"

async def launch_bot(meeting_id: str):
    meeting = MEETINGS.get(meeting_id)
    if not meeting:
        raise ValueError(f"Meeting {meeting_id} not found")

    payload = {
        "meeting_id": meeting_id,
        "meeting_url": meeting["meeting_url"],
        "bot_name": meeting.get("bot_name", "AI Bot")
    }
    print(f"[BOT] Launching for meeting {meeting_id} with payload: {payload}")

    # Run subprocess in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        subprocess.Popen,
        ["node", str(BOT_PATH), json.dumps(payload)],
        subprocess.DEVNULL,
        subprocess.DEVNULL
    )

    print(f"[BOT] Launched for meeting {meeting_id}")
