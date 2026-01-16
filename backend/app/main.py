from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.meeting_manager import MeetingManager
from app.services.scheduler import scheduler

manager = MeetingManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔵 Startup logic
    print("Starting backend...")
    # restore_jobs()
    scheduler.start()

    yield  # ⬅️ App runs here

    # 🔴 Shutdown logic
    print("Stopping backend...")
    scheduler.shutdown(wait=False)
    manager.stop_all()

app = FastAPI(lifespan=lifespan)
