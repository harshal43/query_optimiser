from __future__ import annotations
import asyncio
import json
import logging
from typing import Any
from app.services.admin_config import get_config

logger = logging.getLogger(__name__)


async def fire_webhook(event_type: str, payload: dict[str, Any]) -> None:
    config = get_config()
    slack = str(config.get("slack_webhook_url", "") or "")
    email = str(config.get("email_webhook_url", "") or "")
    urls = [u for u in [slack, email] if u.startswith("http")]
    if not urls:
        return
    import urllib.request
    body = json.dumps({"event": event_type, "payload": payload}).encode()
    for url in urls:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda u=url: urllib.request.urlopen(
                    urllib.request.Request(u, data=body, headers={"Content-Type": "application/json"}),
                    timeout=5,
                ),
            )
            logger.info("Webhook fired: %s → %s", event_type, url)
        except Exception:
            logger.warning("Webhook failed: %s → %s", event_type, url, exc_info=True)
