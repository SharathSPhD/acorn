__pattern__ = "EventDriven"

import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from api.config import settings

try:
    import redis.asyncio as aioredis  # available at runtime inside Docker
except ImportError:  # pragma: no cover — redis absent only in bare test envs
    aioredis = None

router = APIRouter()


@router.websocket("/ws/{problem_uuid}")
async def websocket_stream(websocket: WebSocket, problem_uuid: str) -> None:
    """Stream agent events to Hub via WebSocket. Subscribes to acorn:stream:{problem_uuid}."""
    await websocket.accept()
    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        channel = f"acorn:stream:{problem_uuid}"
        await pubsub.subscribe(channel)
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])
            else:
                # Send heartbeat to keep connection alive
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        if pubsub:
            await pubsub.unsubscribe()
            await pubsub.aclose()
        if redis_client:
            await redis_client.aclose()


@router.websocket("/ws/problems/{problem_uuid}/logs")
async def websocket_docker_logs(websocket: WebSocket, problem_uuid: str) -> None:
    """Stream live Docker container logs via WebSocket (GAP 7 fix)."""
    await websocket.accept()
    container_name = f"acorn-harness-{problem_uuid}"
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "-f", "--tail", "200", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if proc.stdout is None:
            await websocket.close(code=1011, reason="Failed to attach to container")
            return

        while True:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=60.0)
            if not line:
                break
            await websocket.send_text(line.decode(errors="replace").rstrip("\n"))
    except WebSocketDisconnect:
        pass
    except TimeoutError:
        await websocket.send_text("[timeout] No output for 60s")
    except FileNotFoundError:
        await websocket.close(code=1011, reason="docker not available")
    except OSError:
        await websocket.close(code=1011, reason=f"Container {container_name} not found")
    finally:
        if proc and proc.returncode is None:
            proc.kill()
            await proc.wait()
