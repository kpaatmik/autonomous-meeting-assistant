import redis.asyncio as redis

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=False)

# In services/pubsub.py
async def publish_pcm(meeting_id: str, data: bytes):
    try:
        print(f"[REDIS] Publishing {len(data)} bytes for {meeting_id}")
        # Your existing redis.publish() call
        #await redis_client.publish(f"pcm:{meeting_id}", data)
        await redis_client.xadd(
            f"meeting:{meeting_id}:pcm",
            {"pcm": data}
        )
        print(f"[REDIS] Published successfully")
    except Exception as e:
        print(f"[REDIS] Publish error: {e}")
