import math
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading DistilBART summarizer...")
        self.pipe = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6"
        )
        logger.info("DistilBART summarizer ready")

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
        out = self.pipe(chunk, max_length=150, min_length=30, do_sample=False)[0]["summary_text"]
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
        combined_summaries = " ".join(mini_summaries)
        final = self.pipe(combined_summaries, max_length=300, min_length=100, do_sample=False)[0]["summary_text"]

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
