import asyncio
import redis
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
        print(f"[SESSION] {self.meeting_id} stopped")

    async def _consume_pcm(self):
        stream = f"meeting:{self.meeting_id}:pcm"
        last_id = "0-0"

        while self.running:
            msgs = redis_client.xread(
                {stream: last_id},
                block=1000
            )

            for _, entries in msgs:
                for msg_id, data in entries:
                    pcm = np.frombuffer(data[b"pcm"], dtype=np.float32)
                    audio = self.buffer.add(pcm)

                    if audio is not None:
                        results = self.pipeline.process(audio)
                        for r in results:
                            print(r)

                    last_id = msg_id
