# FAISS & Embeddings Setup

This project now persists meeting segments to SQLite and stores embeddings in FAISS.

Quick setup:

1. Install the new Python dependencies (from the `backend` folder):

   pip install -r requirements.txt

2. Ensure `torch` is available and CUDA is set up if you want GPU acceleration for embeddings. The default model used is `all-MiniLM-L6-v2` from `sentence-transformers` (fast on CPU).

3. Run the backend as usual (uvicorn). FAISS indices will be created under `backend/db/faiss` and the SQLite DB will be `backend/db/meetings.db`.

Usage:

- While meetings run, segments are saved automatically in the background.
- To search a meeting: GET /meetings/{meeting_id}/search?q=your+query

Notes:

- FAISS index files and metadata are stored per-meeting as `faiss_{meeting_id}.index` and `faiss_meta_{meeting_id}.pkl`.
- This is a minimal, file-backed approach meant for local development. For production consider using a more robust vector DB (Milvus, Pinecone, Weaviate) and a proper RDBMS.
