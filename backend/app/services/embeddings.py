from sentence_transformers import SentenceTransformer

_model = None

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        global _model
        if _model is None:
            _model = SentenceTransformer(model_name)
        self.model = _model

    def embed(self, text: str):
        # Returns a numpy float32 vector
        emb = self.model.encode([text], convert_to_numpy=True)[0]
        return emb.astype("float32")

    def embed_batch(self, texts: list[str]):
        embs = self.model.encode(texts, convert_to_numpy=True)
        return embs.astype("float32")
