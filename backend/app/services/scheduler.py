from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
import asyncio

scheduler = None

IST = pytz.timezone("Asia/Kolkata")
scheduler = None
event_loop = None   # 🔑 GLOBAL LOOP

def set_event_loop(loop):
    global event_loop
    event_loop = loop

def get_event_loop():
    return event_loop

def get_scheduler():
    global scheduler
    if scheduler is None:
        try:
            loop = asyncio.get_running_loop()
            scheduler = AsyncIOScheduler(event_loop=loop, timezone=IST)
        except RuntimeError:
            scheduler = AsyncIOScheduler(timezone=IST)
    return scheduler

def start_scheduler():
    global scheduler
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        print("[SCHEDULER] Started with IST timezone")
