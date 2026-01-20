from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from services.scheduler import start_scheduler, get_scheduler
from api.meetings import router as meetings_router
from services.meeting_manager import manager
from services.scheduler import start_scheduler, set_event_loop


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
app.include_router(meetings_router)