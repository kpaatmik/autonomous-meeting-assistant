"""
LLM Responder Module - 
"""

import asyncio
import logging
import threading
import redis.asyncio as redis
import ollama

from services.persistence import get_persistence
from storage.meetings import MEETINGS

logger = logging.getLogger(__name__)

MODEL_NAME = "phi3"
MODEL_ID = "phi3-local"

_llm_responder_lock = threading.Lock()


def _truncate(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


class LLMResponder:
    def __init__(self):
        logger.info("Initializing LLMResponder (Llama3)")
        self.redis_client = None

    async def _get_redis_client(self):
        if self.redis_client is None:
            self.redis_client = redis.Redis(host="localhost", port=6379)
        return self.redis_client

    async def close(self):
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception as e:
                logger.warning("Error closing Redis client: %s", e)
            finally:
                self.redis_client = None

    async def generate_response(self, question: str, context: str = "") -> dict:
        try:
            logger.debug("Generating response for: '%s'", _truncate(question))

            context = context[:1500]

            context_section = f"Context:\n{context}\n" if context.strip() else ""

            prompt = f"""
You are an AI meeting assistant.

Rules:
- Answer only using the provided context.
- Do not make up information.
- If the answer is not present, say: "I don't have enough information."

{context_section}

Question: {question}

Answer:
"""

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama.chat,
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise and factual assistant."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        },
                    ],
                    options={
                        "temperature": 0.3,
                        "num_predict": 150,
                    },
                ),
                timeout=90,
            )

            response_text = response.message.content.strip()
            print(f"[LLM RESPONSE]:- {response_text}")

            return {
                "question": question,
                "response": response_text,
                "model": MODEL_ID,
                "error": None,
            }

        except asyncio.TimeoutError:
            logger.error("LLM request timed out")
            return {
                "question": question,
                "response": "",
                "model": MODEL_ID,
                "error": "timeout",
            }

        except Exception as e:
            logger.error("Error generating response: %s", e, exc_info=True)
            return {
                "question": question,
                "response": "",
                "model": MODEL_ID,
                "error": str(e),
            }

    async def _handle_question(self, redis_client, answer_stream, msg_id, data, meeting_id):
        try:
            question_text = data[b"text"].decode("utf-8")
            speaker = data.get(b"speaker", b"unknown").decode("utf-8")
            segment_id = data.get(b"segment_id", b"").decode("utf-8")

            logger.info("Question from %s: %s", speaker, _truncate(question_text))

            persistence = get_persistence()

            results = await asyncio.to_thread(
                persistence.search, meeting_id, question_text, 3
            )

            context_parts = []
            for row, sim in results:
                ctx_speaker = row[2]
                text = row[5]

                context_parts.append(
                    f"[Speaker: {ctx_speaker} | Score: {sim:.2f}] {text}"
                )

            transcript_context = "\n".join(context_parts)
            meeting = MEETINGS.get(meeting_id, {})
            pre_intents = meeting.get("pre_intents", [])
            pre_intent_context = ""
            if pre_intents:
                pre_intent_context = "Pre-meeting context:\n" + "\n".join(f"- {item}" for item in pre_intents) + "\n\n"

            context = f"{pre_intent_context}{transcript_context}".strip()

            response_data = await self.generate_response(question_text, context)

            logger.info("Response: %s", _truncate(response_data["response"]))
            print(f"[RESPONSE] {response_data}")

            await redis_client.xadd(
                answer_stream,
                {
                    "segment_id": segment_id,
                    "question": question_text,
                    "speaker": speaker,
                    "response": response_data["response"],
                    "model": response_data["model"],
                },
            )

        except Exception as e:
            logger.error("Error processing question: %s", e, exc_info=True)

    async def consume_and_respond(self, meeting_id: str):
        stream = f"meeting:{meeting_id}:questions"
        answer_stream = f"meeting:{meeting_id}:answers"
        last_id = "$"

        redis_client = await self._get_redis_client()

        logger.info("Starting responder for meeting: %s", meeting_id)

        try:
            while True:
                try:
                    msgs = await redis_client.xread(
                        {stream: last_id},
                        count=10,
                        block=1000,
                    )

                    if not msgs:
                        continue

                    for _, entries in msgs:
                        tasks = []
                        last_id_in_batch = last_id

                        for msg_id, data in entries:
                            tasks.append(
                                self._handle_question(
                                    redis_client,
                                    answer_stream,
                                    msg_id,
                                    data,
                                    meeting_id,
                                )
                            )
                            last_id_in_batch = msg_id

                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for res in results:
                            if isinstance(res, Exception):
                                logger.error("Task error", exc_info=res)

                        last_id = last_id_in_batch

                except asyncio.CancelledError:
                    logger.info("Responder cancelled")
                    break

                except Exception as e:
                    logger.error("Main loop error: %s", e, exc_info=True)
                    await asyncio.sleep(1)

        finally:
            logger.info("Responder stopped for meeting: %s", meeting_id)


_llm_responder = None


def get_llm_responder() -> LLMResponder:
    global _llm_responder
    if _llm_responder is None:
        with _llm_responder_lock:
            if _llm_responder is None:
                logger.info("Creating LLMResponder instance")
                _llm_responder = LLMResponder()
    return _llm_responder