from services.diarization import DiarizationService
from services.transcription import TranscriptionService

class StreamingPipeline:
    def __init__(self, meeting_id):
        self.diar = DiarizationService(meeting_id)
        self.asr = TranscriptionService(meeting_id)

    def process(self, audio, sample_rate=16000):
        diarized = self.diar.diarize(audio, sample_rate)
        results = []

        for seg in diarized:
            start = int(seg["start"] * sample_rate)
            end = int(seg["end"] * sample_rate)
            speaker_audio = audio[start:end]

            if len(speaker_audio) == 0:
                continue

            text = self.asr.transcribe_segment(speaker_audio)

            results.append({
                "speaker": seg["speaker"],
                "start": seg["start"],
                "end": seg["end"],
                "text": text
            })

        return results
