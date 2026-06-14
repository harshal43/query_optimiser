from __future__ import annotations
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.sse_manager import event_stream

router = APIRouter(tags=["stream"])


@router.get("/optimize/stream")
async def optimize_stream():
    client_id = str(uuid.uuid4())[:8]
    return StreamingResponse(
        event_stream(client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
