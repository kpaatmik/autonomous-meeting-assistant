import numpy as np

SAMPLE_RATE = 16000
CHUNK_SECONDS = 5

class AudioBuffer:
    def __init__(self):
        self.buffer = []

    def add(self, chunk):
        self.buffer.append(chunk)
        total_samples = sum(len(c) for c in self.buffer)

        if total_samples >= SAMPLE_RATE * CHUNK_SECONDS:
            audio = np.concatenate(self.buffer)
            self.buffer.clear()
            return audio

        return None
