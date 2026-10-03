from fastapi import APIRouter

from app.api.v1 import router_auth, router_photo, router_questionnaire, router_training, router_users

api_router = APIRouter()
api_router.include_router(router_auth.router)
api_router.include_router(router_users.router)
api_router.include_router(router_photo.router)
api_router.include_router(router_training.router)
api_router.include_router(router_questionnaire.router)
