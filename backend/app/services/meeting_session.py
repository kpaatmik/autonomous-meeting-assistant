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
        last_id = "0"  # Start from beginning, not "$"

        while self.running:
            try:
                print(f"[PCM] Listening for stream {stream} from {last_id}")
                
                msgs = await redis_client.xread(
                    {stream: last_id},
                    count=10,  # Read up to 10 messages per call
                    block=500  # Shorter timeout
                )
                
                if not msgs:
                    print(f"[PCM] No new messages (timeout)")
                    continue
                
                print(f"[PCM] Got {len(msgs)} streams with data")

                for stream_key, entries in msgs:
                    print(f"[PCM] Processing {len(entries)} entries")
                    
                    for msg_id, data in entries:
                        try:
                            print(f"[PCM] Entry keys: {data.keys()}")
                            
                            if b"pcm" not in data:
                                print(f"[PCM] Warning: no 'pcm' key in message")
                                last_id = msg_id
                                continue
                            
                            pcm_bytes = data[b"pcm"]
                            print(f"[PCM] Raw bytes: {len(pcm_bytes)}")
                            
                            pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                            print(f"[PCM] Chunk size: {len(pcm)} samples")
                            
                            energy = np.mean(np.abs(pcm))
                            print(f"[PCM] Energy: {energy:.6f}")

                            audio = self.buffer.add(pcm)

                            if audio is not None:
                                print(f"[PCM] Buffer full, processing audio...")
                                results = self.pipeline.process(audio)
                                for r in results:
                                    print(f"[RESULT] {r}")
                            
                            last_id = msg_id

                        except Exception as e:
                            print(f"[PCM] Error processing entry: {e}")
                            last_id = msg_id
                            continue

            except asyncio.CancelledError:
                print(f"[SESSION] {self.meeting_id} cancelled")
                break
            except Exception as e:
                print(f"[PCM] Stream read error: {e}")
                await asyncio.sleep(0.5)
                continue

