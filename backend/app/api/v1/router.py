from fastapi import APIRouter

from app.api.v1 import auth, router_charts, health, photo, training, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(router_charts.router)
api_router.include_router(health.service_router)
api_router.include_router(photo.router)
api_router.include_router(training.router)
