# 🧠 Autonomous Meeting Assistant

An intelligent real-time meeting assistant powered by FastAPI, Redis, FAISS, and AI models. Automatically transcribe meetings, detect questions, generate insightful answers, and provide comprehensive post-meeting intelligence.

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## ✨ Features

### **Real-Time Meeting Processing**
- ✅ **Live Audio Streaming**: WebSocket-based audio capture and processing
- ✅ **Speech Recognition**: Whisper-based transcription with multi-speaker support
- ✅ **Speaker Diarization**: Pyannote-powered speaker identification and tracking
- ✅ **Question Detection**: ML-based detection of questions in meetings

### **Intelligent Answering**
- ✅ **FAISS Vector Search**: Fast similarity search for relevant context
- ✅ **LLM QA**: Groq Mixtral-8x7b for high-quality answer generation
- ✅ **Context-Aware**: Considers pre-meeting agenda and meeting context
- ✅ **Multi-Source**: Retrieves up to 12 relevant segments for comprehensive answers

### **Meeting Intelligence**
- ✅ **Live Summarization**: Groq Llama/Mixtral-based meeting summarization
- ✅ **Post-Meeting Analysis**: List completed meetings and query meeting-specific data
- ✅ **Pre-Intent Support**: Store and use pre-meeting agenda for better context
- ✅ **Meeting Metadata**: Persistent storage of meeting information

### **Bot Integration**
- ✅ **Jitsi Integration**: Automated bot for live chat message injection
- ✅ **Answer Delivery**: Real-time injection of AI responses into meeting chat
- ✅ **Browser Automation**: Puppeteer-based Jitsi meeting participation

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│           Frontend (Streamlit)                       │
│  - Schedule meetings                                 │
│  - Edit pre-meeting agendas                          │
│  - View post-meeting intelligence                    │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│         Backend (FastAPI)                           │
│  ✓ Meeting Management                               │
│  ✓ Question Detection                               │
│  ✓ Answer Generation (QA)                           │
│  ✓ Meeting Summarization                            │
│  ✓ WebSocket Audio Streaming                        │
└──────────────┬──────────────────────────────────────┘
               │
        ┌──────┴───────┬──────────────┬─────────────┐
        ▼              ▼              ▼             ▼
    ┌────────┐    ┌─────────┐   ┌──────────┐   ┌───────┐
    │ Redis  │    │ SQLite  │   │  FAISS   │   │ Groq  │
    │(Streams)   │(Metadata)   │(Vectors) │   │ API   │
    └────────┘    └─────────┘   └──────────┘   └───────┘
        ▲              ▲              ▲
        └──────────────┴──────────────┘
         Services Layer
         - Transcription
         - Diarization
         - Question Detection
         - Embeddings
         - LLM Integration
```

### **Key Components**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Schedule & manage meetings, view intelligence |
| **Backend API** | FastAPI | REST API for all operations |
| **Real-time Streaming** | WebSocket | Audio and segment streaming |
| **Message Queue** | Redis Streams | Publish-subscribe for real-time data |
| **Vector Database** | FAISS | Semantic search for meeting segments |
| **Persistent Storage** | SQLite | Meeting metadata, segments, embeddings |
| **Speech Recognition** | Whisper | Audio transcription |
| **Speaker ID** | Pyannote.audio | Multi-speaker diarization |
| **LLM Services** | Groq Mixtral-8x7b | QA and summarization |
| **Bot Automation** | Node.js/Puppeteer | Jitsi meeting integration |

---

## 📦 Requirements

### **System Requirements**
- **OS**: Linux/MacOS/Windows
- **CPU**: 4+ vCPUs recommended
- **RAM**: 8GB+ (16GB+ recommended for better performance)
- **Storage**: 20GB+ for models

### **Azure VM Specs** (Tested Configuration)
```
- VM Size: Standard B4als v2
- vCPUs: 4
- RAM: 8 GiB
- OS: Ubuntu 20.04+
```

### **Software Requirements**
- Python 3.10+
- Node.js 16+ (for bot)
- Redis Server
- FFmpeg (for audio processing)

### **API Keys Required**
- **Groq API Key** (Free tier available)
- **Hugging Face API Key** (Optional, for model access)

---

## 🚀 Installation

### **Quick Install Summary**

Here's a quick overview of the complete installation process:

```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && pip install streamlit requests

# Bot
cd bot && npm install

# System services
redis-server  # Start Redis

# Create database
cd backend && python -c "from services.persistence import get_persistence; get_persistence()"
```

### **Detailed Installation Steps**

### **Step 1: Clone Repository**

```bash
git clone https://github.com/yourusername/autonomous-meeting-assistant.git
cd autonomous-meeting-assistant
```

### **Step 2: Backend Setup**

#### Create Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

#### Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    ffmpeg \
    redis-server \
    libsndfile1 \
    python3-dev
```

**MacOS:**
```bash
brew install ffmpeg redis
```

**Windows (with Chocolatey):**
```bash
choco install ffmpeg redis
```

### **Step 3: Frontend Setup**

Install Streamlit and frontend dependencies:

```bash
cd frontend
pip install streamlit requests
```

**Frontend Dependencies:**
- streamlit>=1.28.0 - UI framework
- requests>=2.31.0 - HTTP client for API calls

### **Step 4: Bot Setup**

Install Node.js dependencies for the Jitsi meeting bot:

```bash
cd bot
npm install
```

**Bot Dependencies** (from package.json):
- puppeteer ^22.15.0 - Browser automation for Jitsi
- redis ^5.11.0 - Redis client for message queue

### **Backend Dependencies (requirements.txt)**

Here are all the Python packages required for the backend:

```
# -------------------------
# Backend Framework
# -------------------------
fastapi==0.110.3
uvicorn==0.29.0
starlette==0.37.2
websockets==12.0
anyio==4.3.0

# -------------------------
# Scheduling & PubSub
# -------------------------
APScheduler==3.10.4
redis==5.0.4

# -------------------------
# Audio Processing
# -------------------------
numpy==1.26.4
soundfile==0.12.1

# -------------------------
# PyTorch (CUDA 11.8 – SAFE)
# -------------------------
torch
torchaudio
torchvision

# -------------------------
# Diarization
# -------------------------
pyannote.audio==3.1.1
pyannote.core==5.0.0
pyannote.database==5.1.0

# -------------------------
# Speech Recognition
# -------------------------
openai-whisper==20250625

# -------------------------
# Utilities
# -------------------------
pydantic==2.7.1
python-dotenv==1.0.1
tqdm==4.66.4

# -------------------------
# Embeddings / Vector DB
# -------------------------
sentence-transformers==2.2.2
transformers==4.35.2
faiss-cpu==1.9.0

# -------------------------
# LLM & API Integration
# -------------------------
groq>=0.4.1
requests>=2.31.0
```

### **Dependency Breakdown**

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.110.3 | Web framework |
| uvicorn | 0.29.0 | ASGI server |
| redis | 5.0.4 | Message queue & caching |
| APScheduler | 3.10.4 | Job scheduling |
| torch | Latest | ML computations |
| transformers | 4.35.2 | Hugging Face models |
| whisper | 20250625 | Speech recognition |
| pyannote.audio | 3.1.1 | Speaker diarization |
| faiss-cpu | 1.9.0 | Vector similarity search |
| groq | >=0.4.1 | Groq LLM API |
| sentence-transformers | 2.2.2 | Embeddings generation |

### **Component-Specific Dependencies**

**Core Backend** (Always required):
- fastapi, uvicorn, starlette, pydantic, python-dotenv

**Audio & Speech** (Required for transcription):
- numpy, soundfile, torch, torchaudio, transformers, openai-whisper

**Speaker Diarization** (Required for multi-speaker meetings):
- pyannote.audio, pyannote.core, pyannote.database, torch

**Vector Search** (Required for question answering):
- faiss-cpu, sentence-transformers, transformers

**LLM Integration** (Required for QA and summarization):
- groq, requests

**Task Scheduling** (Required for meeting automation):
- APScheduler

**Message Queue** (Required for real-time streaming):
- redis

### **Quick Install Verification**

After installation, verify all packages are installed:

```bash
pip list | grep -E "fastapi|redis|torch|whisper|groq|faiss|pyannote"
```

Or verify programmatically:

```python
import fastapi
import redis
import torch
import whisper
import groq
import faiss
import pyannote

print("✅ All core packages installed successfully!")
```

### **Step 5: Services Setup**

#### Start Redis Server

```bash
# Linux/MacOS
redis-server

# Windows
redis-server.exe

# Docker
docker run -d -p 6379:6379 redis:latest
```

#### Create SQLite Database

```bash
cd backend
python -c "from services.persistence import get_persistence; get_persistence()"
```

---

## 🔧 Environment Setup

### **Create `.env` File**

Create `backend/.env`:

```bash
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Hugging Face API (Optional)
HUGGINGFACE_API_KEY=your_hf_api_key_here

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Database Configuration
DATABASE_PATH=./data/meetings.db
FAISS_INDEX_PATH=./data/faiss_index

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Bot Configuration
BOT_HEADLESS=true
BOT_LOG_LEVEL=info

# Logging
LOG_LEVEL=INFO
```

### **Get API Keys**

#### **Groq API Key** (Required)
1. Visit https://console.groq.com/keys
2. Sign up (free account)
3. Create a new API key
4. Copy and add to `.env`

#### **Hugging Face API Key** (Optional)
1. Visit https://huggingface.co/settings/tokens
2. Create a new token (read access)
3. Copy and add to `.env`

### **Set Environment Variables**

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY = "your_api_key"
$env:HUGGINGFACE_API_KEY = "your_hf_key"
```

**Linux/MacOS:**
```bash
export GROQ_API_KEY="your_api_key"
export HUGGINGFACE_API_KEY="your_hf_key"
```

---

## ⚙️ Configuration

### **Backend Configuration** (`backend/app/main.py`)

```python
# Default settings
API_HOST = "0.0.0.0"
API_PORT = 8000
RELOAD = True  # Set to False for production
```

### **Frontend Configuration** (`frontend/app.py`)

```python
API_BASE_URL = "http://localhost:8000"
```

### **Audio Processing Settings** (`backend/app/services/streaming_pipeline.py`)

```python
SAMPLE_RATE = 16000  # Hz
CHUNK_SIZE = 1024    # Samples
BUFFER_SIZE = 32000  # Samples
```

### **LLM Model Settings**

**Summarization** (`backend/app/services/flan_summarizer.py`):
- Model: Groq Mixtral-8x7b-32768
- Max Tokens: 1500
- Temperature: 0.3

**QA** (`backend/app/services/flan_qa_service.py`):
- Model: Groq Mixtral-8x7b-32768
- Max Tokens: 1024
- Temperature: 0.5
- Top-K Segments: 12

---

## 📖 Usage

### **Start Backend Server**

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **Start Frontend Application**

```bash
cd frontend
streamlit run app.py
```

### **Start Dummy Context Simulator** (for testing)

```bash
cd backend
python app/context_simulator.py
```

### **Start Bot** (for Jitsi meetings)

```bash
cd bot
npm start
```

---

## 🔌 API Endpoints

### **Meeting Management**

#### **List Meetings**
```http
GET /meetings?status=scheduled|completed
```

### Schedule Meeting
```http
POST /meetings/schedule
Content-Type: application/json

{
  "meeting_id": "team-standup-001",
  "meeting_url": "https://jitsi.example.com/teamroom",
  "bot_name": "AI Assistant",
  "start_time": "2026-04-06T10:00:00",
  "pre_intents": [
    "Discuss Q2 roadmap",
    "Review Q1 metrics",
    "Plan team outing"
  ]
}
```

#### **Get Meeting Details**
```http
GET /meetings/{meeting_id}
```

#### **Update Pre-Intents**
```http
PUT /meetings/{meeting_id}/preintents
Content-Type: application/json

{
  "pre_intents": ["Updated item 1", "Updated item 2"]
}
```

### **Intelligence Endpoints**

#### **Get Meeting Summary**
```http
GET /meetings/{meeting_id}/summary
```

**Response:**
```json
{
  "summary": "The team discussed deploying FastAPI backend on Azure...",
  "method": "groq-mixtral-8x7b"
}
```

#### **Ask Meeting Question**
```http
POST /meetings/{meeting_id}/ask
Content-Type: application/json

{
  "question": "What database was chosen for the project?"
}
```

**Response:**
```json
{
  "answer": "PostgreSQL was chosen as the database for the project...",
  "sources": [1, 5, 8]
}
```

#### **Search Meeting Segments**
```http
GET /meetings/{meeting_id}/search?q=deployment&top_k=5
```

---

## 🐛 Troubleshooting

### **Common Issues & Solutions**

#### **1. Groq API Error: Model Decommissioned**
```
Error: The model `llama-3.1-70b-versatile` has been decommissioned
```

**Solution:**
- Update to `mixtral-8x7b-32768` in `flan_summarizer.py` and `flan_qa_service.py`
- Check Groq deprecations: https://console.groq.com/docs/deprecations

#### **2. Redis Connection Error**
```
ConnectionError: Cannot connect to Redis at localhost:6379
```

**Solution:**
```bash
# Start Redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest

# Test connection
redis-cli ping  # Should return PONG
```

#### **3. Whisper Model Download Fails**
```
HTTPError: Model not found
```

**Solution:**
```bash
# Manually download model
python -c "import whisper; whisper.load_model('base')"
```

#### **4. CUDA Out of Memory**
```
RuntimeError: CUDA out of memory
```

**Solution:**
```bash
# Set CPU-only mode
export CUDA_VISIBLE_DEVICES=""

# Or reduce model size in flan_summarizer.py
model="t5-small"  # Instead of t5-base
```

#### **5. FFmpeg Not Found**
```
FileNotFoundError: ffmpeg not found
```

**Solution:**
```bash
# Ubuntu
sudo apt-get install ffmpeg

# MacOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

#### **6. Meeting Metadata Not Persisting**
```
Meeting ID not found in database
```

**Solution:**
```bash
# Check database exists
ls backend/data/

# Reset database
rm backend/data/meetings.db
python -c "from services.persistence import get_persistence; get_persistence()"
```

---

## 📁 Project Structure

```
autonomous-meeting-assistant/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── meetings.py          # Meeting management endpoints
│   │   │   ├── audio_ws.py          # WebSocket audio streaming
│   │   │   └── demo.py              # Demo endpoints
│   │   ├── services/
│   │   │   ├── flan_summarizer.py   # Summarization service (Groq)
│   │   │   ├── flan_qa_service.py   # QA service (Groq)
│   │   │   ├── transcription.py     # Whisper integration
│   │   │   ├── diarization.py       # Pyannote speaker ID
│   │   │   ├── question_detector.py # Question detection
│   │   │   ├── embeddings.py        # Embedding generation
│   │   │   ├── persistence.py       # Database operations
│   │   │   ├── meeting_manager.py   # Meeting lifecycle
│   │   │   ├── scheduler.py         # APScheduler integration
│   │   │   ├── streaming_pipeline.py # Real-time pipeline
│   │   │   ├── audio_buffer.py      # Audio buffering
│   │   │   ├── pubsub.py            # Redis pub-sub
│   │   │   └── bot_launcher.py      # Bot automation
│   │   ├── storage/
│   │   │   └── meetings.py          # In-memory meeting storage
│   │   ├── static/
│   │   │   └── audioWorklet.js      # Web Audio API
│   │   ├── context_simulator.py     # Dummy data generator
│   │   └── llm_responder_test.py   # LLM testing
│   ├── requirements.txt             # Python dependencies
│   └── data/                        # Persistent storage
│       ├── meetings.db              # SQLite database
│       └── faiss_index              # FAISS vector index
│
├── frontend/                         # Streamlit UI
│   ├── app.py                       # Main Streamlit app
│   └── requirements.txt
│
├── bot/                             # Node.js bot automation
│   ├── bot.js                       # Main bot logic
│   ├── browserPool.js               # Browser pool management
│   ├── package.json
│   └── node_modules/
│
├── README.md                        # This file
└── .env                             # Environment variables (create this)
```

---

## 📊 Database Schema

### **Meeting Metadata Table**
```sql
CREATE TABLE meeting_metadata (
    id INTEGER PRIMARY KEY,
    meeting_id TEXT UNIQUE,
    meeting_url TEXT,
    bot_name TEXT,
    start_time TEXT,
    status TEXT,  -- scheduled|running|completed
    pre_intents TEXT,  -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### **Segments Table**
```sql
CREATE TABLE segments (
    id INTEGER PRIMARY KEY,
    meeting_id TEXT,
    speaker TEXT,
    start REAL,
    end REAL,
    text TEXT,
    embedding BLOB,  -- Vector embedding
    FOREIGN KEY (meeting_id) REFERENCES meeting_metadata(meeting_id)
);
```

---

## 🔄 Data Flow

```
1. MEETING SCHEDULING
   User Schedule → API → Database → APScheduler

2. LIVE MEETING
   Jitsi → Browser Audio → WebSocket → Streaming Pipeline
   → Whisper (Transcription) → Pyannote (Diarization)
   → Segments → FAISS Embedding + Redis + SQLite

3. QUESTION IN MEETING
   Question Detection → LLM QA (Groq) → Redis Stream
   → Bot Listener → Jitsi Chat Injection

4. POST-MEETING
   User Queries → API → FAISS Search → LLM Summarization/QA
   → Response to Frontend

5. ANALYTICS
   Completed Meeting → Database → Streamlit Dashboard
```

---

## 📈 Performance Optimization Tips

| Optimization | Impact | Difficulty |
|-------------|--------|-----------|
| Use FAISS GPU support | 10x faster search | High |
| Cache summaries | 5x faster re-queries | Low |
| Batch segment processing | 2x throughput | Medium |
| Use Mixtral instead of Llama | Better quality/speed | Low |
| Quantize embeddings | 4x memory savings | High |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs/features.

---

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📞 Support & Issues

For issues, questions, or feature requests:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Groq docs: https://console.groq.com/docs
3. Check Streamlit docs: https://docs.streamlit.io
4. Open a GitHub issue with error logs

---

## 🎯 Roadmap

- [ ] Support for multiple video conference platforms (Zoom, Google Meet, Teams)
- [ ] Real-time translation for multilingual meetings
- [ ] Sentiment analysis and emotion detection
- [ ] Action item auto-assignment
- [ ] Meeting minutes generation (markdown/PDF)
- [ ] Integration with calendar systems (Google Calendar, Outlook)
- [ ] Custom model fine-tuning for domain-specific meetings
- [ ] Mobile app for on-the-go meeting access

---

**Last Updated**: April 6, 2026  
**Version**: 1.0.0  
**Status**: Production Ready