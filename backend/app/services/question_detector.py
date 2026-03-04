"""
Question Detection Module using FLAN-T5

Consumes segments from Redis stream, classifies if they are questions,
and pushes questions to a separate stream for LLM processing.
"""

import asyncio
import json
import logging
import redis.asyncio as redis
from transformers import pipeline

logger = logging.getLogger(__name__)


class QuestionDetector:
    def __init__(self):
        logger.info("Initializing QuestionDetector with google/flan-t5-base...")
        
        # Load FLAN-T5 model for question classification
        try:
            self.classifier = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                device=-1,  # -1 for CPU, 0 for GPU if available
                trust_remote_code=True
            )
            logger.info("FLAN-T5 model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading FLAN-T5 model: {e}")
            raise
        
        self.redis_client = None  # Will be initialized on demand
        logger.info("QuestionDetector initialized")
    
    async def _get_redis_client(self):
        """Get or create redis client (async)"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(host="localhost", port=6379)
            logger.debug("Redis client created")
        return self.redis_client
    
    async def classify_text(self, text: str) -> dict:
        """
        Classify if text is a question using FLAN-T5
        
        Returns:
            {
                "is_question": bool,
                "confidence": float,
                "text": str,
                "response": str,
                "error": Optional[str]
            }
        """
        try:
            logger.debug(f"Classifying text: '{text[:80]}...'")
            
            # Create prompt for FLAN-T5
            prompt = f"Is this a question? Answer with 'yes' or 'no'.\nText: {text}"
            
            # Run model in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.classifier(prompt, max_length=10)
            )
            
            response = result[0]['generated_text'].strip().lower()
            is_question = 'yes' in response
            
            logger.debug(f"Classification result: is_question={is_question}, response='{response}'")
            
            return {
                "is_question": is_question,
                "confidence": 0.95 if is_question else 0.85,
                "text": text,
                "response": response,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error classifying text: {e}", exc_info=True)
            return {
                "is_question": False,
                "confidence": 0.0,
                "text": text,
                "response": "error",
                "error": str(e)
            }
    
    async def consume_and_detect(self, meeting_id: str):
        """
        Main loop: consume segments from Redis stream and detect questions
        
        Reads from: meeting:{meeting_id}:segments
        Writes to: meeting:{meeting_id}:questions (for questions only)
        """
        stream = f"meeting:{meeting_id}:segments"
        question_stream = f"meeting:{meeting_id}:questions"
        last_id = "$"  # Start from NOW
        
        redis_client = await self._get_redis_client()
        
        logger.info(f"Starting question detection for meeting: {meeting_id}")
        logger.info(f"Reading from stream: {stream}")
        logger.info(f"Writing questions to stream: {question_stream}")
        
        try:
            while True:
                try:
                    # Read segments from Redis stream
                    logger.debug(f"Waiting for segments from {stream}...")
                    msgs = await asyncio.wait_for(
                        redis_client.xread(
                            {stream: last_id},
                            count=10,
                            block=1000  # 1 second block
                        ),
                        timeout=2.0  # 2 second overall timeout
                    )
                    
                    if not msgs:
                        logger.debug(f"No new segments in {stream}")
                        continue
                    
                    for stream_key, entries in msgs:
                        for msg_id, data in entries:
                            try:
                                # Decode segment data
                                segment_text = data[b'text'].decode('utf-8')
                                speaker = data[b'speaker'].decode('utf-8') if b'speaker' in data else "unknown"
                                segment_id = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else str(msg_id)
                                
                                logger.info(f"Processing segment ({segment_id}) from '{speaker}': '{segment_text[:60]}...'")
                                
                                # Classify if it's a question
                                classification = await self.classify_text(segment_text)
                                
                                # Add metadata
                                classification['speaker'] = speaker
                                classification['segment_id'] = segment_id
                                classification['meeting_id'] = meeting_id
                                
                                if classification['is_question']:
                                    logger.info(f"✓ QUESTION DETECTED from '{speaker}': '{segment_text[:60]}...'")
                                    
                                    # Push to questions stream for LLM module
                                    try:
                                        question_msg_id = await redis_client.xadd(
                                            question_stream,
                                            {
                                                'segment_id': segment_id,
                                                'text': segment_text,
                                                'speaker': speaker,
                                                'is_question': 'true',
                                                'confidence': str(classification['confidence']),
                                                'original_response': classification['response']
                                            }
                                        )
                                        logger.debug(f"Question pushed to {question_stream} with id: {question_msg_id}")
                                    except Exception as e:
                                        logger.error(f"Failed to push question to stream: {e}")
                                else:
                                    logger.debug(f"✗ Not a question from '{speaker}': '{segment_text[:60]}...'")
                                
                                # Update stream position
                                last_id = msg_id
                                
                            except Exception as e:
                                logger.error(f"Error processing segment entry: {e}", exc_info=True)
                                last_id = msg_id  # Still advance to avoid re-processing
                
                except asyncio.TimeoutError:
                    logger.debug("Question detector read timeout (normal)")
                    continue
                    
                except asyncio.CancelledError:
                    logger.info(f"Question detector cancelled for meeting: {meeting_id}")
                    break
                    
                except Exception as e:
                    logger.error(f"Error in question detection loop: {e}", exc_info=True)
                    await asyncio.sleep(1)
        
        finally:
            logger.info(f"Question detection stopped for meeting: {meeting_id}")


# Singleton instance
_question_detector: QuestionDetector = None


def get_question_detector() -> QuestionDetector:
    """Get or initialize the global question detector instance"""
    global _question_detector
    if _question_detector is None:
        logger.info("Creating new QuestionDetector instance")
        _question_detector = QuestionDetector()
    return _question_detector
