"""
Demo: Question Detection System

This demonstrates the full flow:
1. Segments pushed to Redis stream
2. Question detector classifies them
3. Questions pushed to answer stream

Run this after starting Redis and the main app.
"""

import asyncio
import logging
import redis.asyncio as redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def demo():
    """Demo the question detection pipeline"""
    
    redis_client = redis.Redis(host="localhost", port=6379)
    
    meeting_id = "demo_meeting_001"
    segments_stream = f"meeting:{meeting_id}:segments"
    questions_stream = f"meeting:{meeting_id}:questions"
    
    logger.info("=== Question Detection Demo ===\n")
    
    # Test segments
    test_segments = [
        {
            "text": "What time is the meeting tomorrow?",
            "speaker": "Alice"
        },
        {
            "text": "The project deadline is next Friday.",
            "speaker": "Bob"
        },
        {
            "text": "Can we discuss the Q4 budget?",
            "speaker": "Charlie"
        },
        {
            "text": "Our quarterly revenue increased by 15%.",
            "speaker": "Diana"
        },
        {
            "text": "Do we need to update the documentation?",
            "speaker": "Eve"
        }
    ]
    
    logger.info(f"Pushing {len(test_segments)} test segments to {segments_stream}\n")
    
    for i, segment in enumerate(test_segments, 1):
        try:
            msg_id = await redis_client.xadd(
                segments_stream,
                {
                    'text': segment['text'],
                    'speaker': segment['speaker'],
                    'start': str(i * 10),
                    'end': str(i * 10 + 5)
                }
            )
            logger.info(f"[{i}] Pushed: '{segment['text'][:50]}...'")
            logger.info(f"    Speaker: {segment['speaker']}")
            logger.info(f"    Stream ID: {msg_id}\n")
        except Exception as e:
            logger.error(f"Failed to push segment {i}: {e}\n")
    
    # Wait for question detection to process
    logger.info("\n⏳ Waiting for question detection (15 seconds)...\n")
    await asyncio.sleep(15)
    
    # Check what questions were detected
    logger.info(f"\n=== Checking {questions_stream} ===\n")
    
    try:
        # Get all messages in the questions stream
        questions = await redis_client.xrange(questions_stream)
        
        if not questions:
            logger.warning("No questions detected yet. Make sure:")
            logger.warning("1. Redis is running")
            logger.warning("2. Question detector is running (from main app)")
            logger.warning("3. FLAN-T5 model is loaded")
        else:
            logger.info(f"Found {len(questions)} detected questions:\n")
            
            for i, (msg_id, data) in enumerate(questions, 1):
                text = data.get(b'text', b'').decode('utf-8')
                speaker = data.get(b'speaker', b'').decode('utf-8')
                confidence = data.get(b'confidence', b'0').decode('utf-8')
                
                logger.info(f"[QUESTION {i}]")
                logger.info(f"  Text: {text}")
                logger.info(f"  Speaker: {speaker}")
                logger.info(f"  Confidence: {confidence}")
                logger.info(f"  Stream ID: {msg_id}\n")
    
    except Exception as e:
        logger.error(f"Error reading questions stream: {e}")
    
    # Clean up
    try:
        await redis_client.delete(segments_stream)
        await redis_client.delete(questions_stream)
        logger.info("Cleaned up demo streams")
    except Exception as e:
        logger.warning(f"Could not clean up streams: {e}")
    
    await redis_client.close()


async def manual_test():
    """Manual classification test (without Redis streams)"""
    
    logger.info("=== Manual Classification Test ===\n")
    
    try:
        from services.question_detector import get_question_detector
        
        detector = get_question_detector()
        
        test_texts = [
            "What is the project timeline?",
            "The project is due next month.",
            "Can we reschedule the meeting?",
            "Our sales increased by 20%.",
            "How will this affect the budget?",
        ]
        
        logger.info(f"Testing FLAN-T5 classification:\n")
        
        for text in test_texts:
            result = await detector.classify_text(text)
            
            status = "✓ QUESTION" if result['is_question'] else "✗ NOT QUESTION"
            logger.info(f"{status}")
            logger.info(f"  Text: {text}")
            logger.info(f"  Confidence: {result['confidence']:.2f}")
            logger.info(f"  Model response: {result['response']}\n")
    
    except Exception as e:
        logger.error(f"Error in manual test: {e}")
        logger.error("Make sure the main app is running or FLAN-T5 model is loaded")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("Question Detection System - Demo")
    print("="*60 + "\n")
    print("Options:")
    print("  1: Demo with Redis streams (requires running app)")
    print("  2: Manual classification test")
    print("  q: Quit\n")
    
    choice = input("Select option (1/2/q): ").strip().lower()
    
    if choice == "1":
        asyncio.run(demo())
    elif choice == "2":
        asyncio.run(manual_test())
    elif choice == "q":
        print("Exiting...")
    else:
        print("Invalid choice")
