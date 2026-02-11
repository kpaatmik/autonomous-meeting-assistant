from pyannote.audio import Pipeline
import numpy as np
import soundfile as sf
import uuid, os
from dotenv import load_dotenv
load_dotenv()
class DiarizationService:
    def __init__(self, meeting_id):
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization@2.1",
            use_auth_token=os.getenv("HUGGINGFACE_HUB_TOKEN")
            
        )

    def diarize(self, audio, sample_rate=16000):
        tmp = f"/tmp/{uuid.uuid4()}.wav"
        sf.write(tmp, audio, sample_rate)

        diarization = self.pipeline(tmp)
        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": turn.start,
                "end": turn.end
            })

        os.remove(tmp)
        return segments
