import redis.asyncio as redis

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=False)

async def publish_pcm(meeting_id: str, data: bytes):
    try:
        print(f"[REDIS] Publishing {len(data)} bytes for {meeting_id}")
        stream_key = f"meeting:{meeting_id}:pcm"
        
        # Add to stream with binary data
        await redis_client.xadd(stream_key, {"pcm": data})
        print(f"[REDIS] Published to stream {stream_key}")
    except Exception as e:
        print(f"[REDIS] Publish error: {e}")
