import math
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading Pegasus-XSum via HF Inference for high-quality summarization...")
        self.hf_token = os.getenv("HUGGINGFACE_API_KEY")
        if not self.hf_token:
            raise ValueError("HUGGINGFACE_API_KEY environment variable not set")
        self.model_id = "google/pegasus-xsum"  # Best free summarization model
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {"Authorization": f"Bearer {self.hf_token}"}
        logger.info("Pegasus-XSum summarizer ready")

    def _preprocess_text(self, text):
        """Clean up transcript text for better summarization"""
        # Remove common filler words and phrases
        fillers = [
            r'\b(um|uh|like|you know|so|well|actually|basically|i mean|sort of|kind of)\b',
            r'\b(bye bye|thanks for watching|see you|next video)\b',
            r'\b(if you see this|pin as|i don\'t know)\b',
            r'\.\s*\.\s*\.',  # Multiple dots
            r'\s+',  # Multiple spaces
        ]

        for pattern in fillers:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

        # Fix common typos and clean up
        text = re.sub(r'(\w)\1{2,}', r'\1', text)  # Remove repeated characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)  # Remove special chars except basic punctuation

        # Clean up spacing
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _preprocess_text(self, text):
        """Clean up transcript text for better summarization"""
        # Remove common filler words and phrases
        fillers = [
            r'\b(um|uh|like|you know|so|well|actually|basically|i mean|sort of|kind of)\b',
            r'\b(bye bye|thanks for watching|see you|next video)\b',
            r'\b(if you see this|pin as|i don\'t know)\b',
            r'\.\s*\.\s*\.',  # Multiple dots
            r'\s+',  # Multiple spaces
        ]

        for pattern in fillers:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

        # Fix common typos and clean up
        text = re.sub(r'(\w)\1{2,}', r'\1', text)  # Remove repeated characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)  # Remove special chars except basic punctuation

        # Clean up spacing
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _chunk_text(self, texts, chunk_size=3000):
        """Chunk text for API limits"""
        processed_texts = [self._preprocess_text(text) for text in texts if text.strip()]
        joined = " ".join(processed_texts)
        words = joined.split()

        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)

        return chunks

    def _summarize_with_pegasus(self, text):
        """Use Pegasus-XSum for high-quality abstractive summarization"""
        try:
            payload = {"inputs": text, "parameters": {"max_length": 200, "min_length": 50, "do_sample": False}}
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and result:
                    return result[0].get("summary_text", text[:300])
                else:
                    return text[:300]
            else:
                logger.error(f"HF API error: {response.text}")
                return text[:300]
        except Exception as e:
            logger.error(f"Pegasus summarization failed: {e}")
            return text[:300]

    def summarize_meeting(self, segments):
        """
        segments = list of DB rows
        """

        texts = [s[5] for s in segments]  # text column

        if not texts:
            return {"summary": "No transcript available"}

        # Process all text together for comprehensive summarization
        chunks = self._chunk_text(texts)

        if len(chunks) == 1:
            # Single chunk - summarize directly
            final = self._summarize_with_pegasus(chunks[0])
        else:
            # Multiple chunks - summarize each then combine and re-summarize
            chunk_summaries = []
            for chunk in chunks:
                summary = self._summarize_with_pegasus(chunk)
                chunk_summaries.append(summary)

            # Combine chunk summaries and create final summary
            combined_text = " ".join(chunk_summaries)
            if len(combined_text.split()) > 100:  # Only re-summarize if substantial content
                final = self._summarize_with_pegasus(combined_text)
            else:
                final = combined_text

        return {
            "summary": final,
            "method": "pegasus-xsum-hf"
        }


_summarizer = None

def get_flan_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = FlanSummarizer()
    return _summarizer
