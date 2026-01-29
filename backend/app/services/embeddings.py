from typing import List, Optional
import os

import torch

# Prefer sentence-transformers when possible (convenient API)
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SBERT = True
except Exception:
    SentenceTransformer = None
    _HAS_SBERT = False

# Fallback to transformers+mean-pooling for models that aren't SBERT format
try:
    from transformers import AutoTokenizer, AutoModel
    _HAS_TRANSFORMERS = True
except Exception:
    AutoTokenizer = None
    AutoModel = None
    _HAS_TRANSFORMERS = False

# Default model: can be overridden by setting EMBED_MODEL env var
DEFAULT_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-base-en-v1.5")

class EmbeddingService:
    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.backend = None

        # Try SentenceTransformer first
        if _HAS_SBERT:
            try:
                self.sbert = SentenceTransformer(model_name, device=self.device)
                self.backend = "sbert"
            except Exception:
                self.sbert = None

        # Fallback to transformers
        if self.backend is None and _HAS_TRANSFORMERS:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
                self.model = AutoModel.from_pretrained(model_name)
                self.model.to(self.device)
                self.model.eval()
                self.backend = "transformers"
            except Exception:
                self.tokenizer = None
                self.model = None

        if self.backend is None:
            raise RuntimeError(
                "No embedding backend available. Install 'sentence-transformers' or 'transformers', and ensure the model name is correct."
            )

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return sum_embeddings / sum_mask

    def embed(self, text: str):
        """Return a single float32 vector for the input text."""
        if self.backend == "sbert":
            emb = self.sbert.encode([text], convert_to_numpy=True)[0]
            return emb.astype("float32")

        # transformers path
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        pooled = self._mean_pooling(outputs, inputs["attention_mask"])
        emb = pooled[0].cpu().numpy().astype("float32")
        return emb

    def embed_batch(self, texts: List[str]):
        """Return numpy array (n, d) of float32 embeddings for a list of texts."""
        if self.backend == "sbert":
            embs = self.sbert.encode(texts, convert_to_numpy=True)
            return embs.astype("float32")

        inputs = self.tokenizer(texts, return_tensors="pt", truncation=True, padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        pooled = self._mean_pooling(outputs, inputs["attention_mask"])
        embs = pooled.cpu().numpy().astype("float32")
        return embs
