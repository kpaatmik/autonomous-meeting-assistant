import asyncio
import logging
import redis.asyncio as redis
import numpy as np
from services.bot_launcher import launch_bot
from services.audio_buffer import AudioBuffer
from services.streaming_pipeline import StreamingPipeline
from services.persistence import get_persistence
from services.question_detector import get_question_detector

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="localhost", port=6379)

# shared persistence instance
persistence = get_persistence()
question_detector = get_question_detector()

class MeetingSession:
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id
        self.buffer = AudioBuffer()
        self.pipeline = StreamingPipeline(meeting_id)
        self.running = False
        self.pcm_task = None
        self.question_detector_task = None  # Task for question detection loop

    async def start(self):
        await launch_bot(self.meeting_id)
        self.running = True
        
        # Start PCM consumption task
        self.pcm_task = asyncio.create_task(self._consume_pcm())
        logger.info(f"[SESSION] PCM consumer started for {self.meeting_id}")
        
        # Start question detection task
        self.question_detector_task = asyncio.create_task(
            question_detector.consume_and_detect(self.meeting_id)
        )
        logger.info(f"[SESSION] Question detector started for {self.meeting_id}")
        
        print(f"[SESSION] {self.meeting_id} started")

    async def stop(self):
        self.running = False
        
        # Cancel PCM consumer task
        if self.pcm_task:
            self.pcm_task.cancel()
            try:
                await self.pcm_task
            except asyncio.CancelledError:
                logger.debug(f"[SESSION] PCM task cancelled")
        
        # Cancel question detector task
        if self.question_detector_task:
            self.question_detector_task.cancel()
            try:
                await self.question_detector_task
            except asyncio.CancelledError:
                logger.debug(f"[SESSION] Question detector task cancelled")
        
        print(f"[SESSION] {self.meeting_id} stopped")

    async def _consume_pcm(self):
        stream = f"meeting:{self.meeting_id}:pcm"
        last_id = "$"  # Start from NOW, only new messages

        # Give bot time to start sending before we start reading
        await asyncio.sleep(2)

        while self.running:
            try:
                # Use non-blocking read with timeout
                msgs = await asyncio.wait_for(
                    redis_client.xread(
                        {stream: last_id},
                        count=10,
                        block=1000  # 1 second block
                    ),
                    timeout=2.0  # 2 second overall timeout
                )
                
                if not msgs:
                    print(f"[PCM] No new messages")
                    continue
                
                for stream_key, entries in msgs:
                    for pcm_msg_id, data in entries:
                        try:
                            if b"pcm" not in data:
                                print(f"[PCM] Warning: no 'pcm' key in message")
                                last_id = pcm_msg_id
                                continue
                            
                            pcm_bytes = data[b"pcm"]
                            #print(f"[PCM] Got chunk: {len(pcm_bytes)} bytes")
                            
                            pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                            
                            energy = np.mean(np.abs(pcm))
                            #print(f"[PCM] Energy: {energy:.6f}")
                            


                            audio = self.buffer.add(pcm)

                
                            
                            if audio is not None:
                                print(f"[PCM] Buffer ready ({len(audio)} samples), processing...")

                                loop = asyncio.get_running_loop()
                                results = await loop.run_in_executor(
                                    None,
                                    self.pipeline.process,
                                    audio
                                )

                                for r in results:
                                    print(f"[RESULT] {r}")
                                    
                                    # Push segment to Redis stream for question detection
                                    # This ensures no loss and allows async question detection
                                    try:
                                        segment_stream   = f"meeting:{self.meeting_id}:segments"
                                        segment_msg_id  = await redis_client.xadd(
                                            segment_stream,
                                            {
                                                'text': r.get('text', ''),
                                                'speaker': r.get('speaker', 'unknown'),
                                                'start': str(r.get('start', 0)),
                                                'end': str(r.get('end', 0))
                                            }
                                        )
                                        logger.debug(f"Segment pushed to stream {stream} with id: {pcm_msg_id}")
                                        print(f"[SEGMENT] Pushed to stream with id: {segment_msg_id}")
                                    except Exception as e:
                                        logger.error(f"Error pushing segment to stream: {e}")
                                    
                                    # Persist segment immediately for reference
                                    # (can also be done after question detection if needed)
                                    """
                                    asyncio.create_task(
                                        asyncio.to_thread(persistence.save_segment, self.meeting_id, r)
                                    )
                                    """
                                    
                            
                            # Update position AFTER successful processing
                            last_id = pcm_msg_id

                        except Exception as e:
                            print(f"[PCM] Entry error: {e}")
                            last_id = msg_id  # Still advance to avoid re-processing

            except asyncio.TimeoutError:
                # Normal timeout, just continue
                continue
                
            except asyncio.CancelledError:
                print(f"[SESSION] {self.meeting_id} cancelled")
                break
                
            except Exception as e:
                print(f"[PCM] Read error: {e}")
                await asyncio.sleep(0.5)

