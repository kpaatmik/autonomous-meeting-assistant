import subprocess
import json
from pathlib import Path
from app.storage.meetings import MEETINGS

BOT_PATH = Path(__file__).resolve().parents[2] / "bot" / "bot.js"

def launch_bot(meeting_id: str):
    meeting = MEETINGS.get(meeting_id)
    if not meeting:
        raise ValueError(f"Meeting {meeting_id} not found")

    payload = {
        "meeting_id": meeting_id,
        "meeting_url": meeting["meeting_url"],
        "bot_name": meeting.get("bot_name", "AI Bot")
    }

    subprocess.Popen(
        ["node", str(BOT_PATH), json.dumps(payload)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print(f"[BOT] Launched for meeting {meeting_id}")
