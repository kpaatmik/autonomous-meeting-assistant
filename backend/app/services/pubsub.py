import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=False
)

def publish_pcm(meeting_id: str, pcm_bytes: bytes):
    redis_client.xadd(
        f"meeting:{meeting_id}:pcm",
        {"pcm": pcm_bytes}
    )
