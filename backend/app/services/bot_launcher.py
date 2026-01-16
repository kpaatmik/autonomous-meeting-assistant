
import subprocess
import json
from pathlib import Path

BOT_PATH = Path(__file__).resolve().parents[2] / "bot" / "bot.js"

def launch_bot(meeting):
    payload = {
        "meeting_id": meeting["meeting_id"],
        "meeting_url": meeting["meeting_url"],
        "bot_name": meeting["bot_name"]
    }

    subprocess.Popen(
        ["node", str(BOT_PATH), json.dumps(payload)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
