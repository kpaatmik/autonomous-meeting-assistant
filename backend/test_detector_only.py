import asyncio
import logging
from app.services.question_detector import get_question_detector
import redis

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    meeting_id = "demo_meeting_001"
    logger.info(f"Starting question detector for {meeting_id}...")
    
    detector = get_question_detector()
    
    # Run the consumer (this blocks)
    await detector.consume_and_detect(meeting_id)

if __name__ == "__main__":
    asyncio.run(main())