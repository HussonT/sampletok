from fastapi import APIRouter

from app.api.v1.endpoints import samples, process, test, users, collections

api_router = APIRouter()

api_router.include_router(samples.router, prefix="/samples", tags=["samples"])
api_router.include_router(process.router, prefix="/process", tags=["processing"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])