from fastapi import APIRouter

from app.api.v1 import (
    health,
    router_auth,
    router_charts,
    router_diet,
    router_photo,
    router_questionnaire,
    router_training,
    router_users,
    vision,
)

api_router = APIRouter()

api_router.include_router(vision.router)
api_router.include_router(router_auth.router)
api_router.include_router(router_users.router)
api_router.include_router(health.router)
api_router.include_router(router_charts.router)
api_router.include_router(health.service_router)
api_router.include_router(router_photo.router)
api_router.include_router(router_training.router)
api_router.include_router(router_questionnaire.router)
api_router.include_router(router_diet.router)
