from fastapi import APIRouter

from app.api.v1.endpoints import samples, process, test, users, collections, admin, webhooks, subscriptions, credits, stems

api_router = APIRouter()

api_router.include_router(samples.router, prefix="/samples", tags=["samples"])
api_router.include_router(process.router, prefix="/process", tags=["processing"])
api_router.include_router(test.router, prefix="/test", tags=["testing"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(stems.router, prefix="/stems", tags=["stems"])