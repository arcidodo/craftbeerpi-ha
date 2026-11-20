"""Coordinator: haalt alles periodiek bij CraftBeerPi."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import CBPiAuthError, CBPiClient, CBPiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class CBPiCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: CBPiClient, interval: int, entry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=interval), config_entry=entry)
        self.client = client
        self.local: dict[str, dict] = {}   # per vergister: og, fg, src (door de gebruiker ingesteld, door HA onthouden)

    async def _async_update_data(self):
        try:
            return await self.client.fetch_all()
        except CBPiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CBPiError as err:
            raise UpdateFailed(str(err)) from err

    # Hulpfuncties voor de entiteiten
    @staticmethod
    def active_step(fermenter: dict) -> dict | None:
        for st in fermenter.get("steps") or []:
            if st.get("status") == "A":
                return st
        return None

    def set_local(self, fid: str, key: str, value) -> None:
        self.local.setdefault(fid, {})[key] = value
        self.async_update_listeners()

    def sg_id(self, fid: str) -> str | None:
        """SG-sensor van een vergister: de gekozen bron, anders sensor2 uit CBPi."""
        choice = self.local.get(fid, {}).get("src")
        if choice and choice != "auto":
            for sid, s in (self.data or {}).get("sensors", {}).items():
                if s.get("name") == choice:
                    return sid
            return None
        return ((self.data or {}).get("fermenters", {}).get(fid) or {}).get("sensor2") or None

    def sg_value(self, fid: str):
        sid = self.sg_id(fid)
        v = ((self.data or {}).get("sensors", {}).get(sid) or {}).get("value") if sid else None
        return v if isinstance(v, (int, float)) and 0.98 < v < 1.2 else None

    def sg_options(self) -> list[str]:
        out = []
        for s in (self.data or {}).get("sensors", {}).values():
            n = (s.get("name") or "")
            l = n.lower()
            if ("gravity" in l or l.endswith(" sg")) and "plato" not in l:
                out.append(n)
        return sorted(out)
