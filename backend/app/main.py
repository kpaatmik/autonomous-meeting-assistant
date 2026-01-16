from fastapi import FastAPI
from contextlib import asynccontextmanager
from services.meeting_manager import MeetingManager
from services.scheduler import scheduler
from api.meetings import router as meetings_router

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
    await manager.stop_all()

app = FastAPI(lifespan=lifespan)
app.include_router(meetings_router)