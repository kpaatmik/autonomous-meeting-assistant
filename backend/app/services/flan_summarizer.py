import math
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading FLAN-T5 summarizer...")
        self.pipe = pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            max_length=512
        )
        logger.info("FLAN summarizer ready")

    def _chunk_text(self, texts, chunk_size=1200):
        """
        Hierarchical chunking.
        texts = list of segment texts
        """
        joined = " ".join(texts)
        words = joined.split()

        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)

        return chunks

    def _summarize_chunk(self, chunk):
        prompt = f"""
Summarize this meeting discussion clearly:

{chunk}

Return short bullet summary.
"""
        out = self.pipe(prompt)[0]["generated_text"]
        return out

    def summarize_meeting(self, segments):
        """
        segments = list of DB rows
        """

        texts = [s[5] for s in segments]  # text column

        if not texts:
            return {"summary": "No transcript available"}

        # 🔵 MAP STEP
        chunks = self._chunk_text(texts)

        mini_summaries = []
        for ch in chunks:
            mini = self._summarize_chunk(ch)
            mini_summaries.append(mini)

        # 🔴 REDUCE STEP
        final_prompt = f"""
Combine these summaries into one final meeting summary.

Also extract:
- Key Decisions
- Action Items
- Open Questions

Summaries:
{mini_summaries}
"""

        final = self.pipe(final_prompt)[0]["generated_text"]

        return {
            "summary": final,
            "num_chunks": len(chunks)
        }


_summarizer = None

def get_flan_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = FlanSummarizer()
    return _summarizer
