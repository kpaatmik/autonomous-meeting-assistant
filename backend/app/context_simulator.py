"""
Real-Time Dummy Context Generator

Simulates live meeting transcript ingestion.
"""

import time
import random

from services.persistence import get_persistence


MEETING_ID = "Testingpahse"


def generate_dummy_segments():
    return [
        ("SPEAKER_00", "We are planning to deploy the backend using FastAPI."),
        ("SPEAKER_01", "The database chosen for this project is PostgreSQL."),
        ("SPEAKER_02", "Redis will be used for caching frequently accessed data."),
        ("SPEAKER_00", "The deployment will happen on Azure cloud infrastructure."),
        ("SPEAKER_01", "We should also consider Docker for containerization."),
        ("SPEAKER_02", "Monitoring will be done using Prometheus and Grafana."),
        ("SPEAKER_00", "The API performance needs to be optimized."),
        ("SPEAKER_01", "Security measures like JWT authentication will be implemented."),
        ("SPEAKER_02", "We may scale using Kubernetes in the future."),
        ("SPEAKER_00", "Logging will be handled using centralized logging tools."),
    ]


def run_live_context_feed():
    persistence = get_persistence()

    segments = generate_dummy_segments()

    print("\n[SIMULATION] Starting live context feed...\n")

    i = 0
    start_time = 1.0

    while True:
        speaker, text = segments[i % len(segments)]

        segment = {
            "speaker": speaker,
            "start": start_time,
            "end": start_time + 2.0,
            "text": text,
        }

        persistence.save_segment(MEETING_ID, segment)

        print(f"[ADDED] {speaker}: {text}")

        # simulate real-time delay
        time.sleep(random.uniform(2, 4))

        start_time += 2.5
        i += 1


if __name__ == "__main__":
    run_live_context_feed()