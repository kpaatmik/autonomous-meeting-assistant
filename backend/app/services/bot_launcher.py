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
    print(f"[BOT] Bot path: {BOT_PATH}")
    print(f"[BOT] Bot path exists: {BOT_PATH.exists()}")

    # Run subprocess in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    
    def spawn_bot():
        process = subprocess.Popen(
                    ["node", str(BOT_PATH), json.dumps(payload)],
                    stdout=None,    # show logs
                    stderr=None
                )
        return process
    
    try:
        process = await loop.run_in_executor(None, spawn_bot)
        print(f"[BOT] Bot process spawned with PID: {process.pid}")
    except Exception as e:
        print(f"[BOT] Error spawning bot: {e}")
