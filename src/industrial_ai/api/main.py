"""Application factory. The default process uses SQLite and the in-process graph."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from industrial_ai import __version__
from industrial_ai.api.routes import approvals, assets, events, graph, plans, scenarios
from industrial_ai.domain.decisions import FlowError
from industrial_ai.platform import Platform
from industrial_ai.runtime_gates import adapter_report


def create_app(platform: Platform | None = None) -> FastAPI:
    app = FastAPI(
        title="Industrial AI Knowledge Graph Optimizer",
        version=__version__,
        description=(
            "Simulated operational graph, constraint solver, and human approval. "
            "No industrial controller is contacted."
        ),
    )
    app.state.platform = platform or Platform()

    @app.exception_handler(FlowError)
    def on_flow(_request: Request, exc: FlowError) -> JSONResponse:
        return JSONResponse(
            {"error": exc.code, "message": exc.message}, status_code=exc.status_code
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        current = app.state.platform
        kind = current.store.kind if isinstance(current, Platform) else "unknown"
        return {
            "status": "ok",
            "simulation": True,
            "version": __version__,
            "store": kind,
            "adapters": adapter_report(),
            "controller_calls": current.controller_calls if isinstance(current, Platform) else None,
        }

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        current = app.state.platform
        if not isinstance(current, Platform):
            return PlainTextResponse("")
        return PlainTextResponse(current.metrics.render(), media_type="text/plain")

    app.include_router(scenarios.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(graph.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(plans.router, prefix="/api/v1")
    app.include_router(approvals.router, prefix="/api/v1")
    return app


app = create_app()
