# Question Detection System

## Overview

The question detection system classifies meeting transcripts to identify questions and route them for LLM-based answering. It uses **Google's FLAN-T5-base** model for efficient question classification with async streaming via Redis.

## Architecture Flow

```
┌─────────────────────┐
│  Audio Pipeline     │
│  (Transcription)    │
└──────────┬──────────┘
           │
           ├─ Save to DB (persistence)
           │
           └─ Push to Redis Stream
              (meeting:ID:segments)
                     │
                     ▼
         ┌───────────────────────┐
         │  Question Detector    │
         │  (FLAN-T5-base)       │
         │  classify each text   │
         └───────────┬───────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼ (is_question=true)     ▼ (is_question=false)
    ┌─────────────┐          ┌────────────┐
    │ Questions   │          │   Skip     │
    │ Stream      │          │  (logged)  │
    └──────┬──────┘          └────────────┘
           │
           ▼
    ┌──────────────────┐
    │  LLM Responder   │
    │  (Future)        │
    │  generate answer │
    └─────────┬────────┘
              │
              ▼
         ┌─────────────┐
         │ Answers     │
         │ Stream      │
         └─────────────┘
```

## Components

### 1. Question Detector (`question_detector.py`)

**Responsibility**: Classify segments as questions or non-questions

**Key Features**:
- Uses `google/flan-t5-base` transformer model
- Runs classification in thread pool (non-blocking)
- Async Redis stream consumption
- Configurable confidence scores

**Stream Input**: `meeting:{meeting_id}:segments`
- Expected keys: `text`, `speaker`, `start`, `end`

**Stream Output**: `meeting:{meeting_id}:questions`
- Contains: `segment_id`, `text`, `speaker`, `is_question`, `confidence`, `original_response`

**Methods**:
```python
async def classify_text(text: str) -> dict
    # Classify single text, returns classification result
    
async def consume_and_detect(meeting_id: str)
    # Main loop: reads segments, classifies, pushes questions
```

**Usage**:
```python
from services.question_detector import get_question_detector

detector = get_question_detector()
# Start async loop
asyncio.create_task(detector.consume_and_detect(meeting_id))
```

### 2. Meeting Session (`meeting_session.py`)

**Changes**:
1. Now pushes each segment to Redis stream immediately
2. Starts question detector as background task
3. Maintains persistence for all segments (for reference)

**Segment Stream Format**:
```json
{
    "text": "What is the agenda for today?",
    "speaker": "Alice",
    "start": 10.5,
    "end": 12.3
}
```

### 3. LLM Responder (`llm_responder.py`) - *Stub*

**Responsibility**: Answer detected questions using an LLM

**Stream Input**: `meeting:{meeting_id}:questions`

**Stream Output**: `meeting:{meeting_id}:answers`

**Future Implementation Options**:
- OpenAI GPT-4 / GPT-3.5
- Ollama (local LLM)
- Hugging Face transformers
- Azure OpenAI

## Installation

Add to `requirements.txt`:
```
transformers==4.35.2  # Already included
torch==2.1.0          # Already included
redis==5.0.4          # Already included
```

First run will download the FLAN-T5 model (~3GB).

## Configuration

### Environment Variables
```bash
# Optional: Set CUDA device (default: -1 for CPU)
export TORCH_DEVICE=0  # Use GPU if available
```

### Redis Requirements
- Redis running on `localhost:6379`
- Streams support (Redis 5.0+)

## Usage Example

```python
import asyncio
from services.meeting_session import MeetingSession

async def main():
    meeting = MeetingSession("meeting_001")
    
    # Starts:
    # 1. Audio processing
    # 2. Question detection (async)
    await meeting.start()
    
    # Run for some time...
    await asyncio.sleep(300)
    
    await meeting.stop()

asyncio.run(main())
```

## Debugging & Logging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Watch the logs:
```bash
# PowerShell
python -m app.main 2>&1 | grep -i "question"

# Check Redis streams
redis-cli XLEN meeting:meeting_001:segments
redis-cli XLEN meeting:meeting_001:questions
```

## Performance Notes

- **Classification Speed**: ~200-500ms per segment (CPU)
- **Async Design**: Non-blocking, can classify while listening
- **Memory**: ~2GB for FLAN-T5 model + overhead
- **Redis Streams**: Durable, survives consumer restarts

## Troubleshooting

### Model Download Fails
```
Error: Failed to load transformers model
```
**Solution**: Download model first
```bash
python -c "from transformers import pipeline; pipeline('text2text-generation', model='google/flan-t5-base')"
```

### Redis Connection Error
```
Error: Redis connection refused
```
**Solution**: Start Redis server
```bash
redis-server  # Windows or Linux
```

### Classification Always Returns "Not a Question"
**Check**: 
1. Model confidence threshold (adjust in code)
2. Text format/length (very short texts may be misclassified)
3. Language mismatch (model trained on English)

## Next Steps

1. **Implement LLM Responder** (`llm_responder.py`):
   - Choose LLM provider
   - Implement `generate_response()` method
   - Add context window management
   
2. **Add API Endpoints** for:
   - Checking question stream status
   - Retrieving questions/answers
   - Real-time webhooks
   
3. **Optimization**:
   - Batch classification for speed
   - Model quantization for memory
   - GPU inference if available

## File Structure

```
backend/app/services/
├── question_detector.py    # ✓ Implemented
├── llm_responder.py        # Stub (implement later)
├── meeting_session.py      # ✓ Updated
├── persistence.py          # ✓ Existing (stores all segments)
├── audio_buffer.py         # Existing
├── streaming_pipeline.py   # Existing (transcription)
└── ...
```

## References

- [FLAN-T5 Model Card](https://huggingface.co/google/flan-t5-base)
- [Transformers Library](https://huggingface.co/docs/transformers/)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [AsyncIO](https://docs.python.org/3/library/asyncio.html)
