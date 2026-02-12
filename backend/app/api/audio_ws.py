from fastapi import WebSocket, APIRouter
from services.pubsub import publish_pcm

router = APIRouter()

@router.websocket("/ws/audio/{meeting_id}")
async def audio_ws(ws: WebSocket, meeting_id: str):
    await ws.accept()
    print(f"[WS] Audio connected for {meeting_id}")

    try:
        while True:
            data = await ws.receive_bytes()
            #print(f"[WS] Received PCM chunk: {len(data)} bytes from {meeting_id}")
            await publish_pcm(meeting_id, data)

    except Exception as e:
        print(f"[WS] Audio disconnected {meeting_id}: {e}")
