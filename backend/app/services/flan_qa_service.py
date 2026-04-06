import logging
import os
from groq import Groq
from services.persistence import get_persistence
from storage.meetings import MEETINGS

logger = logging.getLogger(__name__)


class FlanQABot:

    def __init__(self):
        logger.info("Loading Groq Llama 8B QA model...")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=self.groq_api_key)
        self.persistence = get_persistence()
        logger.info("Groq Llama 8B QA bot ready")

    def answer_question(self, meeting_id: str, question: str, top_k: int = 8):

        # 🔵 Retrieve relevant segments using FAISS
        results = self.persistence.search(meeting_id, question, top_k)

        meeting = MEETINGS.get(meeting_id, {})
        pre_intents = meeting.get("pre_intents", [])

        if not results and not pre_intents:
            return {
                "answer": "No relevant discussion found in the meeting.",
                "sources": []
            }

        # ⭐ Re-rank results → prioritize segments containing keyword
        results = sorted(
            results,
            key=lambda x: question.lower() in x[0][5].lower(),
            reverse=True
        )

        # 🔵 Build context
        context_blocks = []
        source_ids = []

        for row, similarity in results:
            seg_id = row[0]
            text = row[5]

            context_blocks.append(text.strip())
            source_ids.append(seg_id)

        transcript_context = "\n".join(context_blocks)
        pre_intent_section = ""
        if pre_intents:
            pre_intent_section = "Pre-Meeting Context:\n" + "\n".join(f"- {intent}" for intent in pre_intents) + "\n\n"

        full_context = pre_intent_section + transcript_context

        prompt = f"""You are an AI assistant answering questions about a meeting based on the transcript and pre-meeting agenda.

{full_context}

Question: {question}

Answer the question using only the information from the meeting context above. If the information is not available in the context, say "This was not discussed in the meeting." Keep the answer concise and relevant."""

        message = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=512,
            temperature=0.3
        )

        output = message.choices[0].message.content
        return {
            "answer": output,
            "sources": source_ids
        }


_qa_bot = None


def get_flan_qa_bot():
    global _qa_bot
    if _qa_bot is None:
        _qa_bot = FlanQABot()
    return _qa_bot
