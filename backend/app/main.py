from fastapi import FastAPI
from app.services.scheduler import start_scheduler
from app.api.meetings import router

app = FastAPI()
app.include_router(router)

@app.on_event("startup")
def startup():
    start_scheduler()
