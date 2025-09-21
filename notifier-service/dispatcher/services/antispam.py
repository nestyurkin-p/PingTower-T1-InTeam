from __future__ import annotations

import asyncio
import time
from typing import Dict, Tuple


class AntiSpamService:
    """In-memory guard to avoid spamming identical alerts."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = max(0, ttl_seconds)
        self._entries: Dict[Tuple[int, str], float] = {}
        self._lock = asyncio.Lock()

    async def should_send(self, site_id: int, incident_key: str) -> bool:
        """Return True when the alert is outside the suppression window."""
        if self.ttl == 0:
            return True
        now = time.monotonic()
        async with self._lock:
            self._cleanup(now)
            key = (site_id, incident_key)
            last = self._entries.get(key)
            if last is None or now - last >= self.ttl:
                return True
            return False

    async def mark_sent(self, site_id: int, incident_key: str) -> None:
        """Record send timestamp for the alert key."""
        if self.ttl == 0:
            return
        now = time.monotonic()
        async with self._lock:
            self._entries[(site_id, incident_key)] = now
            self._cleanup(now)

    def _cleanup(self, now: float) -> None:
        if not self._entries or self.ttl == 0:
            return
        stale = [key for key, ts in self._entries.items() if now - ts >= self.ttl]
        for key in stale:
            self._entries.pop(key, None)
