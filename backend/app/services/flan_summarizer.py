import math
import logging
import os
import re
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class FlanSummarizer:

    def __init__(self):
        logger.info("Loading extractive summarizer with T5...")
        # Use extractive summarization for better transcript handling
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.abstractive_pipe = pipeline(
            "summarization",
            model="t5-small",  # Smaller model for resource constraints
            tokenizer="t5-small"
        )
        logger.info("Extractive + T5-small summarizer ready")

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

    def _extractive_summarize(self, texts, max_sentences=10):
        """Extract most important sentences using TF-IDF"""
        try:
            # Split into sentences
            all_sentences = []
            for text in texts:
                processed = self._preprocess_text(text)
                sentences = re.split(r'[.!?]+', processed)
                sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
                all_sentences.extend(sentences)

            if len(all_sentences) <= max_sentences:
                return " ".join(all_sentences)

            # Vectorize sentences
            tfidf_matrix = self.vectorizer.fit_transform(all_sentences)

            # Calculate sentence scores based on TF-IDF importance
            sentence_scores = np.sum(tfidf_matrix.toarray(), axis=1)

            # Get top sentences
            top_indices = np.argsort(sentence_scores)[-max_sentences:][::-1]
            top_sentences = [all_sentences[i] for i in sorted(top_indices)]

            return " ".join(top_sentences)

        except Exception as e:
            logger.error(f"Extractive summarization failed: {e}")
            return " ".join(texts[:5])  # fallback

    def summarize_meeting(self, segments):
        """
        segments = list of DB rows
        """

        texts = [s[5] for s in segments]  # text column

        if not texts:
            return {"summary": "No transcript available"}

        # Step 1: Extractive summarization to get key sentences
        extracted_text = self._extractive_summarize(texts, max_sentences=15)

        # Step 2: Abstractive summarization for final coherent summary
        try:
            input_text = f"summarize: {extracted_text}"
            result = self.abstractive_pipe(input_text, max_length=300, min_length=100, do_sample=False)
            final = result[0]["summary_text"]
        except Exception as e:
            logger.error(f"Abstractive summarization failed: {e}")
            final = extracted_text[:500]  # fallback to extractive

        return {
            "summary": final,
            "method": "extractive + abstractive"
        }


_summarizer = None

def get_flan_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = FlanSummarizer()
    return _summarizer
