from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone="UTC")

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
