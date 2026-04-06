import logging
from transformers import pipeline
from services.persistence import get_persistence
from storage.meetings import MEETINGS

logger = logging.getLogger(__name__)


class FlanQABot:

    def __init__(self):
        logger.info("Loading FLAN QA model...")
        self.pipe = pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            max_length=256
        )
        self.persistence = get_persistence()
        logger.info("FLAN QA bot ready")

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

        prompt = f"""
You are an assistant answering questions based on the meeting transcript and the pre-meeting agenda.

{pre_intent_section}
Transcript:
{transcript_context}

Question: {question}

Answer the question using the available meeting context. If the answer is not present, say: Not discussed.
"""

        output = self.pipe(prompt)[0]["generated_text"]

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
