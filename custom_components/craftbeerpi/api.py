"""Kleine client voor de CraftBeerPi 4 REST-API."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class CBPiError(Exception):
    """Algemene fout."""


class CBPiAuthError(CBPiError):
    """Geen toegang."""


def _rows(j: Any) -> list[dict]:
    if isinstance(j, dict) and isinstance(j.get("data"), list):
        return j["data"]
    return j if isinstance(j, list) else []


class CBPiClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, username: str | None = None, password: str | None = None) -> None:
        if not url.startswith("http"):
            url = "http://" + url
        self._base = url.rstrip("/")
        self._session = session
        self._auth = aiohttp.BasicAuth(username, password or "") if username else None

    async def _req(self, method: str, path: str, body: Any = None) -> Any:
        try:
            async with asyncio.timeout(10):
                async with self._session.request(method, self._base + path, json=body, auth=self._auth) as r:
                    if r.status in (401, 403):
                        raise CBPiAuthError("Geen toegang")
                    if r.status >= 300:
                        raise CBPiError(f"HTTP {r.status} voor {path}")
                    if r.content_length == 0:
                        return None
                    try:
                        return await r.json(content_type=None)
                    except Exception:  # noqa: BLE001
                        return None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CBPiError(str(err)) from err

    async def get(self, path: str) -> Any:
        return await self._req("GET", path)

    async def post(self, path: str, body: Any = None) -> None:
        await self._req("POST", path, body)

    async def fetch_all(self) -> dict[str, Any]:
        """Alles in één keer: vergisters, ketels, actoren, sensoren (met waarde)."""
        fermenters, kettles, actors, sensors = await asyncio.gather(
            self.get("/fermenter/"), self.get("/kettle/"), self.get("/actor/"), self.get("/sensor/")
        )
        fermenters, kettles, actors, sensors = _rows(fermenters), _rows(kettles), _rows(actors), _rows(sensors)
        sensors = [s for s in sensors if s.get("id")]

        async def value(sid: str) -> Any:
            try:
                j = await self.get(f"/sensor/{sid}")
            except CBPiAuthError:
                raise
            except CBPiError:
                return None
            v = j.get("value") if isinstance(j, dict) else j
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        vals = await asyncio.gather(*(value(s["id"]) for s in sensors))
        for s, v in zip(sensors, vals):
            s["value"] = v
        return {
            "fermenters": {f["id"]: f for f in fermenters if f.get("id")},
            "kettles": {k["id"]: k for k in kettles if k.get("id")},
            "actors": {a["id"]: a for a in actors if a.get("id")},
            "sensors": {s["id"]: s for s in sensors},
        }
