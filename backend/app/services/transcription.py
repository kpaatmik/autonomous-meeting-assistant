import whisper
import numpy as np

class TranscriptionService:
    def __init__(self, meeting_id: str, model_name="base"):
        self.meeting_id = meeting_id
        self.model = whisper.load_model(model_name)

    def transcribe_segment(self, audio_segment: np.ndarray):
        """
        Input:
            audio_segment: np.ndarray (PCM 16kHz, mono)
        Output:
            str (transcribed text)
        """
        result = self.model.transcribe(
            audio_segment,
            language="en",
            fp16=False
        )
        return result["text"]


