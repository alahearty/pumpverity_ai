from fastapi import APIRouter

from app.api.v1 import (
    acquisition,
    alert_reviews,
    alerts,
    auth,
    copilot,
    demo,
    models,
    monitoring,
    predictions,
    pumps,
    reference,
    reports,
    sensors,
    system,
    users,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(pumps.router)
api_router.include_router(sensors.router)
api_router.include_router(reference.router)
api_router.include_router(acquisition.router)
api_router.include_router(monitoring.router)
api_router.include_router(models.router)
api_router.include_router(predictions.router)
api_router.include_router(alerts.router)
api_router.include_router(alert_reviews.router)
api_router.include_router(copilot.router)
api_router.include_router(reports.router)
api_router.include_router(demo.router)


