from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from app.api.meetings import router as meetings_router
from app.api.audio_ws import router as audio_ws_router
from app.services.scheduler import start_scheduler, get_scheduler, set_event_loop
from app.services.meeting_manager import manager

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔵 Startup logic
    print("Starting backend...")
    loop = asyncio.get_running_loop()
    set_event_loop(loop)   # SAVE LOOP
    start_scheduler()

    yield  #  App runs here

    # 🔴 Shutdown logic
    print("Stopping backend...")
    scheduler = get_scheduler()
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    await manager.stop_all()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(meetings_router)
app.include_router(audio_ws_router)
"""app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent / "static"),
    name="static"
)
"""
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
