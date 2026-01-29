import os
import sqlite3
import threading
import pickle
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from services.embeddings import EmbeddingService

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "meetings.db"
FAISS_DIR = DB_DIR / "faiss"
FAISS_DIR.mkdir(parents=True, exist_ok=True)

class Persistence:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        # sqlite connection that can be used from multiple threads
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()
        self.embedding = EmbeddingService()
        self.locks: dict[str, threading.Lock] = {}

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT,
                speaker TEXT,
                start REAL,
                end REAL,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def _get_lock(self, meeting_id: str) -> threading.Lock:
        if meeting_id not in self.locks:
            self.locks[meeting_id] = threading.Lock()
        return self.locks[meeting_id]

    def _faiss_index_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_{meeting_id}.index"

    def _faiss_meta_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_meta_{meeting_id}.pkl"

    def _load_faiss(self, meeting_id: str):
        idx_path = self._faiss_index_path(meeting_id)
        meta_path = self._faiss_meta_path(meeting_id)

        if idx_path.exists() and meta_path.exists():
            index = faiss.read_index(str(idx_path))
            with open(meta_path, "rb") as fh:
                meta = pickle.load(fh)
            return index, meta
        return None, []

    def _save_faiss(self, meeting_id: str, index, meta: list[int]):
        idx_path = self._faiss_index_path(meeting_id)
        meta_path = self._faiss_meta_path(meeting_id)
        faiss.write_index(index, str(idx_path))
        with open(meta_path, "wb") as fh:
            pickle.dump(meta, fh)

    def save_segment(self, meeting_id: str, segment: dict):
        """
        segment: {speaker, start, end, text}
        Saves to sqlite and FAISS (embedding + index)
        """
        # Insert or ensure meeting exists
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO meetings(meeting_id) VALUES (?)", (meeting_id,))

        cur.execute(
            "INSERT INTO segments(meeting_id, speaker, start, end, text) VALUES (?, ?, ?, ?, ?)",
            (meeting_id, segment.get("speaker"), segment.get("start"), segment.get("end"), segment.get("text"))
        )
        self.conn.commit()
        segment_id = cur.lastrowid

        # Compute embedding
        text = segment.get("text") or ""
        vec = self.embedding.embed(text)

        lock = self._get_lock(meeting_id)
        with lock:
            index, meta = self._load_faiss(meeting_id)
            if index is None:
                dim = vec.shape[0]
                index = faiss.IndexFlatL2(dim)
                meta = []

            # add vector and append segment id to meta
            index.add(np.expand_dims(vec, axis=0))
            meta.append(segment_id)

            # Persist
            self._save_faiss(meeting_id, index, meta)

        return segment_id

    def search(self, meeting_id: str, query: str, top_k: int = 5):
        """
        Returns list of (segment_row, score) for the top_k nearest segments to the query
        """
        # embed
        vec = self.embedding.embed(query)

        index, meta = self._load_faiss(meeting_id)
        if index is None or len(meta) == 0:
            return []

        # search
        D, I = index.search(np.expand_dims(vec, axis=0), top_k)
        ids = []
        for idx in I[0]:
            if idx < 0 or idx >= len(meta):
                continue
            segment_id = meta[idx]
            ids.append(segment_id)

        # fetch segments
        if not ids:
            return []

        placeholders = ",".join(["?" for _ in ids])
        cur = self.conn.cursor()
        cur.execute(f"SELECT id, meeting_id, speaker, start, end, text, created_at FROM segments WHERE id IN ({placeholders})", tuple(ids))
        rows = cur.fetchall()

        # map id->row
        rows_by_id = {r[0]: r for r in rows}

        results = []
        for pos, sim in zip(I[0], D[0]):
            if pos < 0 or pos >= len(meta):
                continue
            sid = meta[pos]
            row = rows_by_id.get(sid)
            if row:
                results.append((row, float(sim)))
        return results

# module-level singleton
_persistence: Optional[Persistence] = None

def get_persistence() -> Persistence:
    global _persistence
    if _persistence is None:
        _persistence = Persistence()
    return _persistence
