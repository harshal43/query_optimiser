from __future__ import annotations
import hashlib
import json
from typing import Any
from app.db.connection import get_pool


async def insert_audit_log(
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    pool = get_pool()
    payload_dict = payload or {}
    payload_str = json.dumps(payload_dict, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (actor, action, resource_type, resource_id, payload_hash, payload)
            VALUES ($1, $2, $3, $4::uuid, $5, $6::jsonb)
            """,
            actor, action, resource_type, resource_id, payload_hash, payload_str,
        )
