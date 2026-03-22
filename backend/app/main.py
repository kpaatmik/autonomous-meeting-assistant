from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from services.scheduler import start_scheduler, get_scheduler
from api.meetings import router as meetings_router
from services.meeting_manager import manager
from api.audio_ws import router as audio_ws_router
from services.scheduler import start_scheduler, set_event_loop
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
app.mount("/static", StaticFiles(directory="static"), name="static")
