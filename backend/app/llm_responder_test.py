"""
End-to-End LLM Test Script

Simulates:
Transcripts → FAISS → Question → LLM → Answer
"""

import asyncio
import redis.asyncio as redis

from services.persistence import get_persistence
from services.llm_responder import get_llm_responder


MEETING_ID = "test_meeting"


# -----------------------------
# 1. ADD CONTEXT (simulate transcripts)
# -----------------------------
def add_test_context():
    persistence = get_persistence()

    print("\n[TEST] Adding context...")

    segments = [
        ("SPEAKER_00", "We will deploy the backend using FastAPI."),
        ("SPEAKER_01", "The database we are using is PostgreSQL."),
        ("SPEAKER_00", "Redis will be used for caching."),
        ("SPEAKER_02", "The deployment will happen on Azure cloud."),
    ]

    for i, (speaker, text) in enumerate(segments, start=1):
        persistence.save_segment(
                MEETING_ID,
                {
                    "speaker": speaker,
                    "start": float(i),
                    "end": float(i + 1),
                    "text": text,
                },
            )

    print("[TEST] Context added\n")


# -----------------------------
# 2. PUSH QUESTION TO REDIS
# -----------------------------
async def push_question(r):
    print("[TEST] Sending question...")

    await r.xadd(
        f"meeting:{MEETING_ID}:questions",
        {
            "text": "What database are we using?",
            "speaker": "TEST_USER",
            "segment_id": "test-1",
        },
    )


# -----------------------------
# 3. READ ANSWER FROM REDIS
# -----------------------------
async def read_answer(r):
    print("[TEST] Waiting for answer...\n")

    last_id = "$"

    while True:
        messages = await r.xread(
            {f"meeting:{MEETING_ID}:answers": last_id},
            block=5000,
            count=1,
        )

        if messages:
            for _, entries in messages:
                for msg_id, data in entries:
                    print("\n===== ANSWER RECEIVED =====")
                    print("Question :", data[b"question"].decode())
                    print("Answer   :", data[b"response"].decode())
                    print("Model    :", data[b"model"].decode())
                    print("===========================\n")
                    return


# -----------------------------
# 4. RUN LLM RESPONDER
# -----------------------------
async def run_llm_responder():
    responder = get_llm_responder()
    await responder.consume_and_respond(MEETING_ID)


# -----------------------------
# MAIN TEST
# -----------------------------
async def main():
    # Step 1: Add context
    add_test_context()

    # Step 2: Setup Redis
    r = redis.Redis(host="localhost", port=6379)

    # Step 3: Start LLM responder in background
    responder_task = asyncio.create_task(run_llm_responder())

    # Small delay to ensure responder is ready
    await asyncio.sleep(1)

    # Step 4: Send question
    await push_question(r)

    # Step 5: Read answer
    await read_answer(r)

    # Cleanup
    responder_task.cancel()
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())