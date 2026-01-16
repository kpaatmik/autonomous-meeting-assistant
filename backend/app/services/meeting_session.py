# from app.services.audio_ingest import AudioIngestService
# from app.services.diarization import DiarizationService
# from app.services.asr import WhisperService
# from app.services.intent import IntentService
# from app.services.tts import TTSService
from app.services.bot_launcher import launch_bot
class MeetingSession:
    def __init__(self, meeting_id):
        self.meeting_id = meeting_id

        # self.audio = AudioIngestService(meeting_id)
        # self.diar = DiarizationService(meeting_id)
        # self.asr = WhisperService(meeting_id)
        # self.intent = IntentService(meeting_id)
        # self.tts = TTSService(meeting_id)

    def start(self):
        # 1️⃣ Launch bot
        launch_bot(self.meeting_id)

        # 2️⃣ Start audio pipeline
        self.audio.start()

        print(f"[SESSION] Meeting {self.meeting_id} started")

    def stop(self):
        #self.audio.stop()
        print(f"[SESSION] Meeting {self.meeting_id} stopped")
