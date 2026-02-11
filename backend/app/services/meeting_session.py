import asyncio
import redis.asyncio as redis
import numpy as np
from services.bot_launcher import launch_bot
from services.audio_buffer import AudioBuffer
from services.streaming_pipeline import StreamingPipeline

redis_client = redis.Redis(host="localhost", port=6379)

class MeetingSession:
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id
        self.buffer = AudioBuffer()
        self.pipeline = StreamingPipeline(meeting_id)
        self.running = False
        self.task = None

    async def start(self):
        await launch_bot(self.meeting_id)
        self.running = True
        self.task = asyncio.create_task(self._consume_pcm())
        print(f"[SESSION] {self.meeting_id} started")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
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
                    for msg_id, data in entries:
                        try:
                            if b"pcm" not in data:
                                print(f"[PCM] Warning: no 'pcm' key in message")
                                last_id = msg_id
                                continue
                            
                            pcm_bytes = data[b"pcm"]
                            print(f"[PCM] Got chunk: {len(pcm_bytes)} bytes")
                            
                            pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                            
                            energy = np.mean(np.abs(pcm))
                            print(f"[PCM] Energy: {energy:.6f}")

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

                            
                            # Update position AFTER successful processing
                            last_id = msg_id

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

