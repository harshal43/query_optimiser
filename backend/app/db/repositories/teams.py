from __future__ import annotations
import json
from typing import Any
from app.db.connection import get_pool


async def list_teams() -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT team_id::text, name, warehouse, warehouse_size, enforcement_level, ab_test_config, standardization_rules, created_at FROM teams ORDER BY name"
        )
    return [_row_to_dict(r) for r in rows]


async def get_team(team_id: str) -> dict[str, Any] | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT team_id::text, name, warehouse, warehouse_size, enforcement_level, ab_test_config, standardization_rules, created_at FROM teams WHERE team_id = $1::uuid",
            team_id,
        )
    return _row_to_dict(row) if row else None


async def insert_team(
    name: str,
    warehouse: str = "COMPUTE_WH",
    warehouse_size: str = "X-Small",
    enforcement_level: str = "passive",
    ab_test_config: dict[str, Any] | None = None,
    standardization_rules: dict[str, Any] | None = None,
) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO teams (name, warehouse, warehouse_size, enforcement_level, ab_test_config, standardization_rules)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
            RETURNING team_id::text
            """,
            name, warehouse, warehouse_size, enforcement_level,
            json.dumps(ab_test_config or {}),
            json.dumps(standardization_rules or {}),
        )
    return row["team_id"]


async def update_team(
    team_id: str,
    name: str | None = None,
    warehouse: str | None = None,
    warehouse_size: str | None = None,
    enforcement_level: str | None = None,
    ab_test_config: dict[str, Any] | None = None,
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        if name is not None:
            await conn.execute("UPDATE teams SET name = $1, updated_at = NOW() WHERE team_id = $2::uuid", name, team_id)
        if warehouse is not None:
            await conn.execute("UPDATE teams SET warehouse = $1, updated_at = NOW() WHERE team_id = $2::uuid", warehouse, team_id)
        if warehouse_size is not None:
            await conn.execute("UPDATE teams SET warehouse_size = $1, updated_at = NOW() WHERE team_id = $2::uuid", warehouse_size, team_id)
        if enforcement_level is not None:
            await conn.execute("UPDATE teams SET enforcement_level = $1, updated_at = NOW() WHERE team_id = $2::uuid", enforcement_level, team_id)
        if ab_test_config is not None:
            await conn.execute("UPDATE teams SET ab_test_config = $1::jsonb, updated_at = NOW() WHERE team_id = $2::uuid", json.dumps(ab_test_config), team_id)


async def delete_team(team_id: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM teams WHERE team_id = $1::uuid", team_id)
    return result != "DELETE 0"


def _row_to_dict(row: Any) -> dict[str, Any]:
    d = dict(row)
    for f in ("ab_test_config", "standardization_rules"):
        v = d.get(f)
        if isinstance(v, str):
            d[f] = json.loads(v)
        elif v is None:
            d[f] = {}
    return d
