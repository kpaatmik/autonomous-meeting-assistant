from fastapi import FastAPI
from api import demo
app = FastAPI()

app.include_router(demo.router)
@app.get("/")
async def read_root():
    return {"Hello": "World"}