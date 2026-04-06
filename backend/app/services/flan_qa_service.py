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

    def answer_question(self, meeting_id: str, question: str, top_k: int = 12):

        # 🔵 Retrieve relevant segments using FAISS
        results = self.persistence.search(meeting_id, question, top_k)

        meeting = MEETINGS.get(meeting_id, {})
        pre_intents = meeting.get("pre_intents", [])

        if not results and not pre_intents:
            return {
                "answer": "No relevant discussion found in the meeting.",
                "sources": []
            }

        # ⭐ Re-rank results → prioritize segments containing keyword, then by similarity
        results = sorted(
            results,
            key=lambda x: (question.lower() in x[0][5].lower(), x[1]),
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

        transcript_context = "\n".join(context_blocks[:8])  # Limit to top 8 most relevant segments
        pre_intent_section = ""
        if pre_intents:
            pre_intent_section = "Pre-Meeting Context:\n" + "\n".join(f"- {intent}" for intent in pre_intents) + "\n\n"

        full_context = pre_intent_section + transcript_context

        prompt = f"""You are an AI assistant answering questions about a meeting based on the transcript and pre-meeting agenda.

{full_context}

Question: {question}

Provide a detailed and comprehensive answer using the meeting context above. Include specific details, quotes, and examples from the discussion when relevant. If the information is not available in the context, clearly state that it was not discussed."""

        try:
            message = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides detailed, accurate answers about meeting discussions. Always be thorough and include relevant details from the context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.5
            )

            output = message.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            output = "Sorry, I encountered an error while processing your question. Please try again."
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
