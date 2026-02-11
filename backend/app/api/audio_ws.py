from fastapi import WebSocket, APIRouter
from services.pubsub import publish_pcm

router = APIRouter()

@router.websocket("/ws/audio/{meeting_id}")
async def audio_ws(ws: WebSocket, meeting_id: str):
    await ws.accept()
    print(f"[WS] Audio connected for {meeting_id}")

    try:
        # while True:
        #     data = await ws.receive_bytes()
        #     print(f"Received PCM chunk: {len(data)} bytes")
        #     publish_pcm(meeting_id, data)
        while True:
            data = await ws.receive()

            print("WS raw message:", data["type"])

            if data["type"] == "websocket.receive":
                if "bytes" in data:
                    print("Received bytes:", len(data["bytes"]))
                    publish_pcm(meeting_id, data["bytes"])
                elif "text" in data:
                    print("Received text:", data["text"])

    except Exception as e:
        print(f"[WS] Audio disconnected {meeting_id}: {e}")
