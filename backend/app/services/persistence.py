# services/persistence.py
import sqlite3
import threading
import pickle
from pathlib import Path
from typing import Optional
import logging

import faiss
import numpy as np

from app.services.embeddings import EmbeddingService

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
logger.debug(f"Database directory: {DB_DIR}")

DB_PATH = DB_DIR / "meetings.db"
FAISS_DIR = DB_DIR / "faiss"
FAISS_DIR.mkdir(parents=True, exist_ok=True)
logger.debug(f"FAISS directory: {FAISS_DIR}")


class Persistence:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        logger.info(f"Initializing Persistence with DB path: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

        self.embedding = EmbeddingService()
        self.locks: dict[str, threading.Lock] = {}
        logger.info("Persistence initialized successfully")

    def _init_db(self):
        cur = self.conn.cursor()
        logger.debug("Creating meetings table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.debug("Creating segments table...")
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
        self.conn.commit()
        logger.info("Database tables initialized")

    def _get_lock(self, meeting_id: str) -> threading.Lock:
        if meeting_id not in self.locks:
            self.locks[meeting_id] = threading.Lock()
            logger.debug(f"Created new lock for meeting_id: {meeting_id}")
        return self.locks[meeting_id]

    def _faiss_index_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_{meeting_id}.index"

    def _faiss_meta_path(self, meeting_id: str):
        return FAISS_DIR / f"faiss_meta_{meeting_id}.pkl"

    def _load_faiss(self, meeting_id: str):
        idx_path = self._faiss_index_path(meeting_id)
        meta_path = self._faiss_meta_path(meeting_id)
        
        logger.debug(f"Attempting to load FAISS index from: {idx_path}")
        logger.debug(f"Attempting to load FAISS meta from: {meta_path}")

        if idx_path.exists() and meta_path.exists():
            logger.info(f"Loading existing FAISS index for meeting_id: {meeting_id}")
            index = faiss.read_index(str(idx_path))
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            logger.debug(f"Loaded FAISS index with {len(meta)} segments")
            return index, meta
        
        logger.debug(f"No existing FAISS index found for meeting_id: {meeting_id}")
        return None, []

    def _save_faiss(self, meeting_id: str, index, meta: list[int]):
        idx_path = self._faiss_index_path(meeting_id)
        meta_path = self._faiss_meta_path(meeting_id)
        
        logger.debug(f"Saving FAISS index to: {idx_path}")
        faiss.write_index(index, str(idx_path))
        logger.debug(f"FAISS index saved successfully (size: {index.ntotal} vectors)")
        
        logger.debug(f"Saving FAISS metadata to: {meta_path}")
        with open(meta_path, "wb") as f:
            pickle.dump(meta, f)
        logger.debug(f"FAISS metadata saved successfully ({len(meta)} entries)")

    def save_segment(self, meeting_id: str, segment: dict):
        """
        segment: {speaker, start, end, text}
        """
        logger.info(f"Saving segment for meeting_id: {meeting_id}")
        logger.debug(f"Segment data: speaker={segment.get('speaker')}, "
                    f"start={segment.get('start')}, end={segment.get('end')}, "
                    f"text_length={len(segment.get('text', ''))}")
        
        cur = self.conn.cursor()

        logger.debug(f"Inserting meeting record for meeting_id: {meeting_id}")
        cur.execute(
            "INSERT OR IGNORE INTO meetings(meeting_id) VALUES (?)",
            (meeting_id,)
        )

        logger.debug("Inserting segment record into database...")
        cur.execute(
            "INSERT INTO segments(meeting_id, speaker, start, end, text) VALUES (?, ?, ?, ?, ?)",
            (
                meeting_id,
                segment.get("speaker"),
                segment.get("start"),
                segment.get("end"),
                segment.get("text")
            )
        )
        self.conn.commit()
        segment_id = cur.lastrowid
        logger.info(f"Segment inserted successfully with segment_id: {segment_id}")

        # 🔑 Embed DOCUMENT
        logger.debug(f"Embedding segment text (mode: doc)...")
        vec = self.embedding.embed(segment.get("text", ""), mode="doc")
        vec = vec.reshape(1, -1)
        logger.debug(f"Vector shape: {vec.shape}, dtype: {vec.dtype}")
        
        faiss.normalize_L2(vec)
        logger.debug(f"Vector normalized (L2)")

        lock = self._get_lock(meeting_id)
        with lock:
            logger.debug(f"Acquired lock for meeting_id: {meeting_id}")
            index, meta = self._load_faiss(meeting_id)

            if index is None:
                dim = vec.shape[1]
                logger.info(f"Creating new FAISS index with dimension: {dim}")
                index = faiss.IndexFlatIP(dim)  # Cosine similarity
                meta = []
            else:
                logger.debug(f"Using existing FAISS index (current size: {index.ntotal})")

            logger.debug(f"Adding vector to FAISS index...")
            index.add(vec)
            meta.append(segment_id)
            logger.debug(f"Vector added to index (new size: {index.ntotal})")

            logger.debug(f"Saving FAISS index and metadata...")
            self._save_faiss(meeting_id, index, meta)
            logger.info(f"FAISS index saved successfully for meeting_id: {meeting_id}")


        return segment_id




	def get_all_segments(self, meeting_id: str):
    		conn = self._get_connection()
    		cursor = conn.cursor()

    		cursor.execute("""
        		SELECT id, meeting_id, speaker, start_time, end_time, text
        		FROM segments
        		WHERE meeting_id = ?
        		ORDER BY start_time ASC
		""", (meeting_id,))

    		rows = cursor.fetchall()
    		conn.close()

   	 	return rows	





    def search(self, meeting_id: str, query: str, top_k: int = 5):
        """
        Returns list of (segment_row, similarity)
        """
        logger.info(f"Searching for query in meeting_id: {meeting_id}, top_k: {top_k}")
        logger.debug(f"Query text: {query}")
        
        # 🔑 Embed QUERY
        logger.debug(f"Embedding query (mode: query)...")
        vec = self.embedding.embed(query, mode="query")
        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)
        logger.debug(f"Query vector shape: {vec.shape}")

        index, meta = self._load_faiss(meeting_id)
        if index is None or not meta:
            logger.warning(f"No FAISS index found for meeting_id: {meeting_id}")
            return []

        logger.debug(f"Searching FAISS index with top_k: {top_k}")
        D, I = index.search(vec, top_k)
        logger.debug(f"Search results - distances: {D[0]}, indices: {I[0]}")

        ids = []
        for pos in I[0]:
            if 0 <= pos < len(meta):
                ids.append(meta[pos])

        logger.debug(f"Extracted segment IDs: {ids}")
        
        if not ids:
            logger.warning(f"No valid segment IDs found in search results")
            return []

        placeholders = ",".join(["?"] * len(ids))
        cur = self.conn.cursor()
        logger.debug(f"Querying database for segment IDs: {ids}")
        cur.execute(
            f"SELECT id, meeting_id, speaker, start, end, text FROM segments WHERE id IN ({placeholders})",
            tuple(ids)
        )

        rows = cur.fetchall()
        logger.debug(f"Retrieved {len(rows)} rows from database")
        row_map = {r[0]: r for r in rows}

        results = []
        for pos, similarity in zip(I[0], D[0]):
            if 0 <= pos < len(meta):
                seg_id = meta[pos]
                row = row_map.get(seg_id)
                if row:
                    results.append((row, float(similarity)))
                    logger.debug(f"Added result - segment_id: {seg_id}, similarity: {similarity:.4f}")

        logger.info(f"Search completed - returned {len(results)} results")
        return results


_persistence: Optional[Persistence] = None


def get_persistence() -> Persistence:
    global _persistence
    if _persistence is None:
        logger.info("Creating new Persistence instance")
        _persistence = Persistence()
    return _persistence
"""
def get_all_segments(self, meeting_id: str):
    conn = self._get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, meeting_id, speaker, start_time, end_time, text
        FROM segments
        WHERE meeting_id = ?
        ORDER BY start_time ASC
    """, (meeting_id,))

    rows = cursor.fetchall()
    conn.close()

    return rows
"""
