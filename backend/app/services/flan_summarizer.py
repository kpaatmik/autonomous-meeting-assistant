import math
import logging
import os
import requests

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading BART-large-cnn summarizer via HF Inference...")
        self.hf_token = os.getenv("HUGGINGFACE_API_KEY")
        if not self.hf_token:
            raise ValueError("HUGGINGFACE_API_KEY environment variable not set")
        self.model_id = "facebook/bart-large-cnn"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {"Authorization": f"Bearer {self.hf_token}"}
        logger.info("BART-large-cnn summarizer ready")

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
        payload = {"inputs": chunk}
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        if response.status_code == 200:
            out = response.json()[0]["summary_text"]
        else:
            logger.error(f"HF API error: {response.text}")
            out = chunk[:200]  # fallback
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
        payload = {"inputs": combined_summaries}
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        if response.status_code == 200:
            final = response.json()[0]["summary_text"]
        else:
            logger.error(f"HF API error: {response.text}")
            final = combined_summaries[:500]  # fallback

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
