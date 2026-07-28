from fastapi import APIRouter

RESOURCE_NAME = "auth"
router = APIRouter(prefix=f"/{RESOURCE_NAME}", tags=["Auth"])


__all__ = [
    "router",
    "RESOURCE_NAME",
]
