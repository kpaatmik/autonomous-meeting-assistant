import math
import logging
import os
import re
from groq import Groq

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading Groq mixtral for summarization...")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=self.groq_api_key)
        logger.info("Groq mixtral summarizer ready")

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

    def _summarize_with_llama(self, text):
        """Use Groq Mixtral for high-quality summarization"""
        prompt = f"""Please provide a comprehensive and well-structured summary of the following meeting transcript. Focus on:

1. Main topics discussed
2. Key decisions made
3. Important action items or next steps
4. Any conclusions or outcomes

Be detailed but concise, and ensure the summary captures all important information from the transcript.

Transcript:
{text}

Summary:"""

        try:
            message = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",  # Currently supported model
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing meeting transcripts. Provide clear, concise, and well-structured summaries that capture all important points while being comprehensive."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # Allow longer summaries
                temperature=0.3
            )
            return message.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq summarization failed: {e}")
            return text[:500]  # fallback

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
            final = self._summarize_with_llama(chunks[0])
        else:
            # Multiple chunks - summarize each then combine and re-summarize
            chunk_summaries = []
            for chunk in chunks:
                summary = self._summarize_with_llama(chunk)
                chunk_summaries.append(summary)

            # Combine chunk summaries and create final summary
            combined_text = "\n\n".join(chunk_summaries)
            final = self._summarize_with_llama(combined_text)

        return {
            "summary": final,
            "method": "groq-mixtral-8x7b"
        }


_summarizer = None

def get_flan_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = FlanSummarizer()
    return _summarizer
