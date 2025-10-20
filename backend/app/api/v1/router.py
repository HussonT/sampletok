from fastapi import APIRouter

from app.api.v1.endpoints import samples, process, test, tags

api_router = APIRouter()

api_router.include_router(samples.router, prefix="/samples", tags=["samples"])
api_router.include_router(process.router, prefix="/process", tags=["processing"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])