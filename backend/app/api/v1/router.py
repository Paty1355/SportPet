from fastapi import APIRouter

from app.api.v1 import auth, photo, training, users, vision

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(photo.router)
api_router.include_router(training.router)
api_router.include_router(vision.router)
