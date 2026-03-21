"""
LLM Responder Module - Production Version (Local LLM via Ollama)

Consumes questions from Redis stream and generates responses using a local LLM.
"""

import asyncio
import logging
import threading
import redis.asyncio as redis
import ollama

from services.persistence import get_persistence

logger = logging.getLogger(__name__)

# Local model settings
MODEL_NAME = "llama3"
MODEL_ID = "llama3-local"

# Singleton lock to avoid race conditions when initializing
_llm_responder_lock = threading.Lock()


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate text for safe logging without cutting word boundaries."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


class LLMResponder:
    def __init__(self):
        logger.info("Initializing LLMResponder...")
        self.redis_client = None
        logger.info("LLMResponder ready (Ollama enabled)")
    
    async def _get_redis_client(self):
        """Get or create redis client (async)"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(host="localhost", port=6379)
            logger.debug("Redis client created")
        return self.redis_client

    async def close(self):
        """Close any open resources (e.g., Redis client)."""
        if self.redis_client is None:
            return

        try:
            await self.redis_client.aclose()
            logger.debug("Redis client closed")
        except Exception as e:
            logger.warning("Error closing Redis client: %s", e)
        finally:
            self.redis_client = None
    
    async def generate_response(self, question: str, context: str = "") -> dict:
        """
        Generate a response to a question using an LLM.

        Workflow:
        1. Build a prompt that includes meeting context (if non-empty) and the question.
        2. Call the synchronous Ollama client via asyncio.to_thread to avoid blocking.
        3. Enforce a timeout so stalled model calls do not lock the responder loop.
        4. Return structured output (question, response text, model tag, error).
        """
        try:
            logger.debug(f"Generating response for: '{_truncate(question)}'")

            # Insert Context only when available (avoid blank context section)
            context_section = f"Context:\n{context}\n" if context.strip() else ""

            prompt = f"""

You are an AI meeting assistant.

Use the provided meeting context to answer accurately.
If the answer is not in the context, say "I don't have enough information."

Context:
{context}

Question:
{question}

Answer:
"""

            # ollama.chat is synchronous; offload to a thread to avoid blocking the event loop.
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama.chat,
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    options={
                        "temperature": 0.5,
                        "num_predict": 150,
                    },
                ),
                timeout=15,
            )

            response_text = response.message.content

            return {
                "question": question,
                "response": response_text,
                "model": MODEL_ID,
                "error": None,
            }

        except asyncio.TimeoutError as e:
            logger.error("LLM call timed out", exc_info=e)
            return {
                "question": question,
                "response": "",
                "model": "",
                "error": "LLM request timed out",
            }
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return {
                "question": question,
                "response": "",
                "model": "",
                "error": str(e),
            }
    
    async def _handle_question(self, redis_client, answer_stream, msg_id, data, meeting_id):
        """Process a single question (used for concurrency)."""
        try:
            # Decode incoming Redis stream entry fields.
            question_text = data[b'text'].decode('utf-8')
            speaker = data.get(b'speaker', b'unknown').decode('utf-8')
            segment_id = data.get(b'segment_id', b'').decode('utf-8')

            logger.info(f"Processing question from '{speaker}': '{_truncate(question_text)}'")

            # 1) Fetch context from meeting vector database (FAISS) via persistence layer.
            persistence = get_persistence()
            results = await asyncio.to_thread(persistence.search, meeting_id, question_text, 3)

            # 2) Build a context string with speaker + text snippets.
            context_parts = []
            for row, sim in results:
                ctx_speaker = row[2]  # row[2] is speaker
                text = row[5]         # row[5] is text
                context_parts.append(f"{ctx_speaker}: {text}")
            context = "\n".join(context_parts)

            # 3) Generate answer using LLM with context.
            response_data = await self.generate_response(question_text, context)

            print(f"[LLM] Question: {question_text} || Answer: {response_data['response']}")


            # 4) Write the answer to the meeting answer stream.
            await redis_client.xadd(
                answer_stream,
                {
                    'segment_id': segment_id,
                    'question': question_text,
                    'speaker': speaker,
                    'response': response_data['response'],
                    'model': response_data['model'],
                },
            )

            logger.debug(f"Answer added to {answer_stream}")

        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)

    async def consume_and_respond(self, meeting_id: str):
        """Main loop: consume incoming questions and respond with LLM answers."""
        stream = f"meeting:{meeting_id}:questions"
        answer_stream = f"meeting:{meeting_id}:answers"
        last_id = "$"

        # Redis async client, reused while responder runs
        redis_client = await self._get_redis_client()

        logger.info(f"Starting LLM responder for meeting: {meeting_id}")

        try:
            while True:
                try:
                    # XREAD from question stream with blocking poll (1 second)
                    msgs = await redis_client.xread(
                        {stream: last_id},
                        count=10,
                        block=1000,
                    )

                    if not msgs:
                        # No new messages, continue waiting
                        continue

                    for stream_key, entries in msgs:
                        tasks = []
                        last_id_in_batch = last_id

                        # Create concurrent tasks for each question in batch
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

                        # Run all question tasks concurrently and log task exceptions
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for res in results:
                            if isinstance(res, Exception):
                                logger.error("Error in task while handling questions", exc_info=res)

                        # Advance last_id to the last message successfully queued for handling
                        last_id = last_id_in_batch

                except asyncio.CancelledError:
                    logger.info(f"LLM responder cancelled for meeting: {meeting_id}")
                    break

                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    await asyncio.sleep(1)

        finally:
            logger.info(f"LLM responder stopped for meeting: {meeting_id}")


# Singleton instance
_llm_responder: LLMResponder = None


def get_llm_responder() -> LLMResponder:
    """Get or initialize the global LLM responder instance."""
    global _llm_responder
    if _llm_responder is None:
        with _llm_responder_lock:
            if _llm_responder is None:
                logger.info("Creating new LLMResponder instance")
                _llm_responder = LLMResponder()
    return _llm_responder
