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
        logger.info("Initializing QuestionDetector with question-vs-statement classifier...")
        
        try:
            # Use a dedicated question detection model
            self.classifier = pipeline(
                "text-classification", 
                model="shahrukhx01/question-vs-statement-classifier",
                return_all_scores=None
            )
            logger.info("Question detection model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load question detector: {e}")
            raise
        
        self.redis_client = None
        logger.info("QuestionDetector initialized")
    
    async def _get_redis_client(self):
        """Get or create redis client (async)"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(host="localhost", port=6379)
            logger.debug("Redis client created")
        return self.redis_client
    
    

    async def classify_text(self, text: str) -> dict:
        """
        Classify if text is a question using dedicated classifier
        
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
            logger.debug(f"Classifying text: '{text}'")
            
            # Run classification in thread pool
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, lambda: self.classifier(text))
            
            # Results format: [{'label': 'LABEL_0', 'score': 0.9}, {'label': 'LABEL_1', 'score': 0.1}]
            # LABEL_0 = statement, LABEL_1 = question (based on model)
            
            question_score = 0.0
            statement_score = 0.0
            
            for result in results[0]:  # results is list of lists
                if result['label'] == 'LABEL_1':  # Question
                    question_score = result['score']
                elif result['label'] == 'LABEL_0':  # Statement
                    statement_score = result['score']
            
            is_question = question_score > statement_score
            confidence = max(question_score, statement_score)
            
            response = f"Question: {question_score:.3f}, Statement: {statement_score:.3f}"
            
            logger.debug(f"Classification result: is_question={is_question}, confidence={confidence:.3f}")
            
            return {
                "is_question": is_question,
                "confidence": confidence,
                "text": text,
                "response": response,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error classifying text: {e}")
            return {
                "is_question": False,
                "confidence": 0.0,
                "text": text,
                "response": "",
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
