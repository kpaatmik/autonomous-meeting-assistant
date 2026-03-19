import logging
from transformers import pipeline
from app.services.persistence import get_persistence

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

    def answer_question(self, meeting_id: str, question: str, top_k: int = 5):

        # 🔵 Retrieve relevant segments using FAISS
        results = self.persistence.search(meeting_id, question, top_k)

        if not results:
            return {
                "answer": "No relevant discussion found in the meeting.",
                "sources": []
            }

        # Extract text + ids
        context_blocks = []
        source_ids = []

        for row, similarity in results:
            seg_id = row[0]
            speaker = row[2]
            text = row[5]

            context_blocks.append(f"{speaker}: {text}")
            source_ids.append(seg_id)

        context = "\n".join(context_blocks)

        # 🔴 Build RAG Prompt
        prompt = f"""
Answer the question ONLY using the meeting context.

Context:
{context}

Question:
{question}

If answer not found in context say "Not discussed".
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
