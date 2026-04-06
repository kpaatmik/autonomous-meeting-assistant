import logging
from transformers import pipeline
from services.persistence import get_persistence

logger = logging.getLogger(__name__)

class MeetingSummarizer:

    def __init__(self):
        logger.info("Loading FLAN-T5 summarization model...")
        self.summarizer = pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            max_length=512
        )
        logger.info("FLAN summarizer ready")

    def summarize_meeting(self, meeting_id: str):

        persistence = get_persistence()

        # Fetch ALL segments from DB
        conn = persistence.conn
        cur = conn.cursor()

        cur.execute(
            "SELECT speaker, text FROM segments WHERE meeting_id=? ORDER BY id",
            (meeting_id,)
        )

        rows = cur.fetchall()

        if not rows:
            return {"summary": "No meeting data found"}

        transcript = "\n".join([f"{r[0]}: {r[1]}" for r in rows])

        prompt = f"""
        Summarize the following meeting.
        Include:
        - key discussion points
        - decisions
        - action items
        
        Meeting Transcript:
        {transcript}
        """

        result = self.summarizer(prompt)[0]["generated_text"]

        return {
            "meeting_id": meeting_id,
            "summary": result
        }


_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = MeetingSummarizer()
    return _summarizer