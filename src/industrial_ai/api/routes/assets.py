"""List factories, lines, machines, suppliers, warehouses, and products."""

from fastapi import APIRouter, Request

from industrial_ai.api.deps import platform_of

router = APIRouter()


@router.get("/assets")
def list_assets(request: Request) -> dict[str, object]:
    graph = platform_of(request)
    return {"assets": graph.assets()}
