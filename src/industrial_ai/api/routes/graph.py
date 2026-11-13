"""Dependency and impact queries. Results are candidates, not a plan."""

from fastapi import APIRouter, Request

from industrial_ai.api.deps import platform_of

router = APIRouter()


@router.get("/graph/dependencies/{asset_id}")
def dependencies(asset_id: str, request: Request) -> dict[str, object]:
    return platform_of(request).dependency_view(asset_id)


@router.get("/graph/impact/{asset_id}")
def impact(asset_id: str, request: Request) -> dict[str, object]:
    return platform_of(request).impact_view(asset_id)
