from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))
    from app import app  # type: ignore
else:
    from .app import app


async def _run() -> None:
    await app.run()


if __name__ == "__main__":
    asyncio.run(_run())
