__pattern__ = "Observer"

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.dependencies import get_event_bus
from api.routers import agents, builder, judge, kernels, meta, problems, tasks, telemetry
from api.routers.context import router as context_router
from api.routers.cortex import router as cortex_router
from api.routers.goals import router as goals_router
from api.routers.mailbox import router as mailbox_router
from api.routers.manifest import router as manifest_router
from api.routers.rewards import router as rewards_router
from api.routers.tools import router as tools_router
from api.ws import stream


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    import asyncio
    get_event_bus()  # Register EventBus subscribers on startup
    if settings.cortex_autostart:
        from api.services.cortex import get_cortex
        cortex = get_cortex()
        cortex._task = asyncio.create_task(cortex.run())
    yield


app = FastAPI(
    title="ACORN API",
    description="Agent-Centric Orchestration and Runtime Network -- TRUNK layer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(problems.router)
app.include_router(tasks.router)
app.include_router(agents.router)
app.include_router(kernels.router)
app.include_router(telemetry.router)
app.include_router(judge.router)
app.include_router(meta.router)
app.include_router(builder.router)
app.include_router(context_router)
app.include_router(cortex_router)
app.include_router(mailbox_router)
app.include_router(manifest_router)
app.include_router(rewards_router)
app.include_router(tools_router)
app.include_router(goals_router)
app.include_router(stream.router)



@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "acorn_mode": settings.acorn_mode,
        "routing_strategy": settings.routing_strategy,
        "stall_detection_enabled": settings.stall_detection_enabled,
        "max_agents_per_problem": settings.max_agents_per_problem,
        "max_concurrent_problems": settings.max_concurrent_problems,
        "models": {
            "default": settings.default_model,
            "coder": settings.coder_model,
            "analysis": settings.analysis_model,
        },
        "feature_flags": {
            "telemetry_enabled": settings.telemetry_enabled,
            "kernel_extraction_enabled": settings.kernel_extraction_enabled,
            "judge_required": settings.judge_required,
            "meta_agent_enabled": settings.meta_agent_enabled,
            "builder_enabled": settings.builder_enabled,
        },
        "api_key_present": bool(settings.anthropic_api_key_real),
    }


@app.post("/internal/events")
async def receive_event(request: Request) -> dict[str, str]:
    """Hook relay endpoint. Receives AgentEvent from post-tool-use.sh and publishes to EventBus."""
    from api.events.bus import AgentEvent as BusEvent
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    event_type = body.get("event_type")
    if not event_type or not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Missing or invalid event_type")
    bus = get_event_bus()
    await bus.publish(BusEvent(
        event_type=event_type,
        agent_id=body.get("agent_id", "unknown"),
        problem_uuid=body.get("problem_uuid", "unknown"),
        timestamp_utc=body.get("timestamp_utc", 0.0),
        payload=body.get("payload", {}),
    ))
    return {"status": "ok"}
