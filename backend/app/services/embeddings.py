# services/embeddings.py
from typing import List, Optional
import os
import torch
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SBERT = True
except Exception:
    SentenceTransformer = None
    _HAS_SBERT = False

try:
    from transformers import AutoTokenizer, AutoModel
    _HAS_TRANSFORMERS = True
except Exception:
    AutoTokenizer = None
    AutoModel = None
    _HAS_TRANSFORMERS = False

DEFAULT_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-base-en-v1.5")


class EmbeddingService:
    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.backend = None

        # Sentence-Transformers backend
        if _HAS_SBERT:
            try:
                self.sbert = SentenceTransformer(model_name, device=self.device)
                self.backend = "sbert"
            except Exception:
                self.sbert = None

        # Transformers fallback
        if self.backend is None and _HAS_TRANSFORMERS:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
            self.model = AutoModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
            self.backend = "transformers"

        if self.backend is None:
            raise RuntimeError(
                "No embedding backend available. Install sentence-transformers or transformers."
            )

    def _apply_bge_prefix(self, text: str, mode: str) -> str:
        """
        BGE models REQUIRE these prefixes.
        """
        if self.model_name.startswith("BAAI/bge"):
            if mode == "query":
                return "Represent the question for retrieval: " + text
            return "Represent the document for retrieval: " + text
        return text

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

    def embed(self, text: str, mode: str = "doc") -> np.ndarray:
        """
        Returns a normalized float32 vector.
        mode: 'doc' | 'query'
        """
        text = self._apply_bge_prefix(text, mode)

        if self.backend == "sbert":
            emb = self.sbert.encode(
                [text],
                convert_to_numpy=True,
                normalize_embeddings=True
            )[0]
            return emb.astype("float32")

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        pooled = self._mean_pooling(outputs, inputs["attention_mask"])
        emb = pooled[0].cpu().numpy().astype("float32")

        # Normalize for cosine similarity
        emb /= np.linalg.norm(emb) + 1e-12
        return emb
