from fastapi import APIRouter
router = APIRouter()
@router.get("/demo")
async def demo_endpoint():
    return {"message": "This is a demo endpoint"}