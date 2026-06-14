from __future__ import annotations
import asyncio
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_clients: dict[str, asyncio.Queue[str]] = {}
_HEARTBEAT_INTERVAL = 30


def _make_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def broadcast(event: str, data: dict[str, Any]) -> None:
    msg = _make_event(event, data)
    dead = []
    for cid, q in _clients.items():
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            dead.append(cid)
    for cid in dead:
        _clients.pop(cid, None)
    logger.debug("SSE broadcast %s to %d clients", event, len(_clients))


async def event_stream(client_id: str):
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _clients[client_id] = q
    logger.info("SSE client connected: %s (total=%d)", client_id, len(_clients))
    try:
        yield _make_event("connected", {"client_id": client_id, "ts": time.time()})
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_INTERVAL)
                yield msg
            except asyncio.TimeoutError:
                yield f": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _clients.pop(client_id, None)
        logger.info("SSE client disconnected: %s (total=%d)", client_id, len(_clients))
