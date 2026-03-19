from pyannote.audio import Pipeline
import numpy as np
import soundfile as sf
import uuid, os
from dotenv import load_dotenv
import torch
import warnings
warnings.filterwarnings("ignore")
load_dotenv()
class DiarizationService:
    def __init__(self, meeting_id):
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization@2.1",
            use_auth_token=os.getenv("HUGGINGFACE_HUB_TOKEN")
            
        )
        print(f"{self.pipeline} loaded for meeting {meeting_id}")

    def diarize(self, audio, sample_rate=16000):
        print(f"[DIARIZATION] Starting diarization for audio of length {len(audio)/sample_rate:.2f} seconds")

        # Convert numpy -> torch tensor
        waveform = torch.from_numpy(audio).float().unsqueeze(0)

        diarization = self.pipeline({
            "waveform": waveform,
            "sample_rate": sample_rate
        })

        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": turn.start,
                "end": turn.end
            })

        return segments
