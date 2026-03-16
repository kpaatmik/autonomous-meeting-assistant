# Quick Start Guide - Question Detection

## ⚡ Get Started in 5 Minutes

### Prerequisites
- Redis running (`redis-server`)
- Python 3.9+ with conda/venv
- ~3GB free disk (for FLAN-T5 model)

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

If `transformers` not installed:
```bash
pip install transformers==4.35.2
```

### Step 2: Start Redis
```bash
# Linux/Mac
redis-server

# Windows (if installed)
redis-server.exe

# Or using Docker
docker run -d -p 6379:6379 redis:7
```

### Step 3: Run the Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
[INFO] Initializing QuestionDetector with google/flan-t5-base...
[INFO] FLAN-T5 model loaded successfully
[INFO] Starting backend...
```

### Step 4: Test Question Detection

**Option A: Using the Demo Script**
```bash
cd backend
python demo_question_detection.py
# Select option 1 (Redis stream demo)
```

**Option B: Manual Test**
```bash
redis-cli

# In Redis CLI
XADD meeting:test:segments * text "What is the agenda?" speaker "Alice"
XADD meeting:test:segments * text "The project is due Friday" speaker "Bob"
XADD meeting:test:segments * text "Can we extend the deadline?" speaker "Charlie"

# Wait 10 seconds, then check questions
XRANGE meeting:test:questions - +
```

**Option C: API Endpoint**
```bash
# Start a meeting
curl -X POST http://localhost:8000/meetings/meeting_001/start

# Then segments will automatically flow through the system
# Check Redis:
redis-cli XRANGE meeting:meeting_001:questions - +
```

## 📊 What You Should See

### In Console Logs
```
[INFO] Starting question detection for meeting: meeting_001
[DEBUG] Waiting for segments from meeting:meeting_001:segments...
[INFO] Processing segment from 'Alice': 'What is the agenda?'...
[DEBUG] Classifying text: 'What is the agenda?'...
[INFO] ✓ QUESTION DETECTED from 'Alice': 'What is the agenda?'...
[DEBUG] Question pushed to meeting:meeting_001:questions
```

### In Redis
```bash
$ redis-cli XLEN meeting:meeting_001:segments
(integer) 5

$ redis-cli XLEN meeting:meeting_001:questions  
(integer) 3

$ redis-cli XRANGE meeting:meeting_001:questions - +
1) 1) "1710000000000-0"
   2) 1) "segment_id"
      2) "some_id_1"
   3) "text"
      4) "What is the agenda?"
   5) "speaker"
      6) "Alice"
   7) "is_question"
      8) "true"
   9) "confidence"
     10) "0.95"
```

## 🎮 Interactive Commands

### Monitor Questions in Real-Time
```bash
# Terminal 1: Watch segments
watch -n 1 'redis-cli XLEN meeting:meeting_001:segments'

# Terminal 2: Watch questions
watch -n 1 'redis-cli XLEN meeting:meeting_001:questions'

# Terminal 3: Watch answers (after LLM implementation)
watch -n 1 'redis-cli XLEN meeting:meeting_001:answers'
```

### Test Classification Speed
```bash
python -c "
import asyncio
from services.question_detector import get_question_detector

async def test():
    detector = get_question_detector()
    texts = ['What time is it?', 'The weather is nice.', 'Can we reschedule?']
    for text in texts:
        result = await detector.classify_text(text)
        print(f'{text:30} -> {\"QUESTION\" if result[\"is_question\"] else \"STATEMENT\"}')"

asyncio.run(test())
```

Output:
```
What time is it?             -> QUESTION
The weather is nice.         -> STATEMENT
Can we reschedule?           -> QUESTION
```

## 🐛 Troubleshooting

### "Model loading takes forever"
First download is slow (~5-10 min depending on internet). It's cached after that.

```bash
# Pre-download model
python -c "from transformers import pipeline; pipeline('text2text-generation', model='google/flan-t5-base')"
```

### "Redis connection refused"
Make sure Redis is running:
```bash
redis-cli ping
# Should output: PONG
```

### "No questions being detected"
Check logs for FLAN-T5 errors:
```bash
python -m uvicorn app.main:app 2>&1 | grep -i "error\|question"
```

Verify streams exist:
```bash
redis-cli KEYS "meeting:*"
```

### "Classification always says 'not a question'"
Model prefers clear question indicators (?, did, can, what, when, etc.)
Try explicit prompts in testing.

## 📚 Next Steps

1. **Monitor in Production** - Set up logging/monitoring
2. **Implement LLM Responder** - See `llm_responder.py` for template
3. **Add API Endpoints** - Create endpoints to retrieve questions/answers
4. **Real-time WebSocket** - Stream questions to frontend
5. **Context Window** - Add recent transcript context to LLM

## 🔗 Useful Links

- Demo Script: `demo_question_detection.py`
- Full Docs: `QUESTION_DETECTION.md`
- Implementation Details: `IMPLEMENTATION_SUMMARY.md`
- Source Code: `services/question_detector.py`
- LLM Template: `services/llm_responder.py`

## 💡 Tips

**Tip 1**: Use `logging.DEBUG` level to see classification details
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Tip 2**: Test with batch/multiple questions for stress testing
```bash
for i in {1..100}; do
  redis-cli XADD meeting:stress:segments * text "Question $i?" speaker "User"
done
```

**Tip 3**: Monitor FLAN-T5 latency with timestamps
```bash
redis-cli XADD test * timestamp "$(date +%s%N)" question "Test?"
```

---

**Status**: ✅ Ready to use!

Need help? Check QUESTION_DETECTION.md for detailed docs.
