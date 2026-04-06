import sqlite3
import threading
import pickle
import json
from pathlib import Path
from typing import Optional
import logging

import faiss
import numpy as np

from services.embeddings import EmbeddingService

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "meetings.db"

FAISS_DIR = DB_DIR / "faiss"
FAISS_DIR.mkdir(parents=True, exist_ok=True)


class Persistence:

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)

        self.embedding = EmbeddingService()
        self.locks: dict[str, threading.Lock] = {}

        self._init_db()

        logger.info("Persistence initialized")

    # ---------------- DB INIT ----------------

    def _init_db(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT,
                speaker TEXT,
                start REAL,
                end REAL,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_metadata (
                meeting_id TEXT PRIMARY KEY,
                meeting_url TEXT,
                bot_name TEXT,
                start_time TEXT,
                status TEXT,
                pre_intents TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def save_meeting_metadata(self, meeting_id: str, meeting_url: str, bot_name: str, start_time: str, status: str = "scheduled", pre_intents: Optional[list[str]] = None):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO meeting_metadata(meeting_id, meeting_url, bot_name, start_time, status, pre_intents, updated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                meeting_id,
                meeting_url,
                bot_name,
                start_time,
                status,
                json.dumps(pre_intents or []),
            )
        )
        self.conn.commit()

    def update_meeting_metadata(self, meeting_id: str, **kwargs):
        if not kwargs:
            return

        fields = []
        values = []
        if "pre_intents" in kwargs:
            fields.append("pre_intents = ?")
            values.append(json.dumps(kwargs["pre_intents"] or []))
        if "status" in kwargs:
            fields.append("status = ?")
            values.append(kwargs["status"])
        if "meeting_url" in kwargs:
            fields.append("meeting_url = ?")
            values.append(kwargs["meeting_url"])
        if "bot_name" in kwargs:
            fields.append("bot_name = ?")
            values.append(kwargs["bot_name"])
        if "start_time" in kwargs:
            fields.append("start_time = ?")
            values.append(kwargs["start_time"])

        if not fields:
            return

        values.append(meeting_id)
        cur = self.conn.cursor()
        cur.execute(
            f"UPDATE meeting_metadata SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE meeting_id = ?",
            tuple(values)
        )
        self.conn.commit()

    def get_meeting_metadata(self, meeting_id: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT meeting_id, meeting_url, bot_name, start_time, status, pre_intents FROM meeting_metadata WHERE meeting_id = ?",
            (meeting_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "meeting_id": row[0],
            "meeting_url": row[1],
            "bot_name": row[2],
            "start_time": row[3],
            "status": row[4],
            "pre_intents": json.loads(row[5] or "[]")
        }

    def list_meeting_metadata(self, status: Optional[str] = None):
        cur = self.conn.cursor()
        if status:
            cur.execute(
                "SELECT meeting_id, meeting_url, bot_name, start_time, status, pre_intents FROM meeting_metadata WHERE status = ? ORDER BY start_time DESC",
                (status,)
            )
        else:
            cur.execute(
                "SELECT meeting_id, meeting_url, bot_name, start_time, status, pre_intents FROM meeting_metadata ORDER BY start_time DESC"
            )

        rows = cur.fetchall()
        results = []
        for row in rows:
            results.append({
                "meeting_id": row[0],
                "meeting_url": row[1],
                "bot_name": row[2],
                "start_time": row[3],
                "status": row[4],
                "pre_intents": json.loads(row[5] or "[]")
            })
        return results

    # ---------------- LOCK ----------------

    def _get_lock(self, meeting_id: str):
        if meeting_id not in self.locks:
            self.locks[meeting_id] = threading.Lock()
        return self.locks[meeting_id]

    # ---------------- FAISS PATH ----------------

    def _faiss_index_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_{meeting_id}.index"

    def _faiss_meta_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_meta_{meeting_id}.pkl"

    # ---------------- LOAD FAISS ----------------

    def _load_faiss(self, meeting_id: str):

        idx_path = self._faiss_index_path(meeting_id)
        meta_path = self._faiss_meta_path(meeting_id)

        if idx_path.exists() and meta_path.exists():
            index = faiss.read_index(str(idx_path))
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            return index, meta

        return None, []

    # ---------------- SAVE FAISS ----------------

    def _save_faiss(self, meeting_id: str, index, meta):

        faiss.write_index(index, str(self._faiss_index_path(meeting_id)))

        with open(self._faiss_meta_path(meeting_id), "wb") as f:
            pickle.dump(meta, f)

    # ---------------- SAVE SEGMENT ----------------

    def save_segment(self, meeting_id: str, segment: dict):

        cur = self.conn.cursor()

        cur.execute(
            "INSERT OR IGNORE INTO meetings(meeting_id) VALUES (?)",
            (meeting_id,)
        )

        cur.execute(
            "INSERT INTO segments(meeting_id, speaker, start, end, text) VALUES (?, ?, ?, ?, ?)",
            (
                meeting_id,
                segment.get("speaker"),
                segment.get("start"),
                segment.get("end"),
                segment.get("text"),
            )
        )

        self.conn.commit()
        segment_id = cur.lastrowid

        # embed
        vec = self.embedding.embed(segment.get("text", ""), mode="doc")
        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)

        lock = self._get_lock(meeting_id)

        with lock:

            index, meta = self._load_faiss(meeting_id)

            if index is None:
                dim = vec.shape[1]
                index = faiss.IndexFlatIP(dim)
                meta = []

           # logger.debug(f"Adding vector to FAISS index...")
           ########
            index.add(vec)
            meta.append(segment_id)
            #logger.debug(f"Vector added to index (new size: {index.ntotal})")

           
            
            self._save_faiss(meeting_id, index, meta)

        return segment_id

    # ---------------- GET ALL SEGMENTS (FOR SUMMARY) ----------------

    def get_all_segments(self, meeting_id: str):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT id, meeting_id, speaker, start, end, text
            FROM segments
            WHERE meeting_id = ?
            ORDER BY start ASC
        """, (meeting_id,))

        rows = cur.fetchall()
        return rows

    # ---------------- SEARCH ----------------

    def search(self, meeting_id: str, query: str, top_k: int = 5):

        vec = self.embedding.embed(query, mode="query")
        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)

        index, meta = self._load_faiss(meeting_id)

        if index is None:
            return []

        D, I = index.search(vec, top_k)

        ids = []
        for pos in I[0]:
            if 0 <= pos < len(meta):
                ids.append(meta[pos])

        if not ids:
            return []

        placeholders = ",".join(["?"] * len(ids))
        cur = self.conn.cursor()

        cur.execute(
            f"SELECT id, meeting_id, speaker, start, end, text FROM segments WHERE id IN ({placeholders})",
            tuple(ids)
        )

        rows = cur.fetchall()
        row_map = {r[0]: r for r in rows}

        results = []
        for pos, sim in zip(I[0], D[0]):
            if 0 <= pos < len(meta):
                seg_id = meta[pos]
                row = row_map.get(seg_id)
                if row:
                    results.append((row, float(sim)))

        return results


_persistence: Optional[Persistence] = None


def get_persistence():

    global _persistence

    if _persistence is None:
        _persistence = Persistence()

    return _persistence
