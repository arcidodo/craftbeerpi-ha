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
        """SG-sensor van een vergister: de gekozen bron; anders sensor2 uit CBPi; anders (bij een brouwsel) automatisch de
        iSpindel met een SG die bij dit brouwsel past en die niet al bij een andere vergister hoort."""
        data = self.data or {}
        sensors = data.get("sensors", {})
        choice = self.local.get(fid, {}).get("src")
        if choice and choice != "auto":
            for sid, s in sensors.items():
                if s.get("name") == choice:
                    return sid
            return None
        f = data.get("fermenters", {}).get(fid) or {}
        if f.get("sensor2"):
            return f["sensor2"]
        if not f.get("brewname"):
            return None
        claimed = set()
        for oid, o in data.get("fermenters", {}).items():
            if oid == fid:
                continue
            if o.get("sensor2"):
                claimed.add(o["sensor2"])
            c = self.local.get(oid, {}).get("src")
            if c and c != "auto":
                claimed |= {sid for sid, s in sensors.items() if s.get("name") == c}
        og = self.local.get(fid, {}).get("og")
        fg = self.local.get(fid, {}).get("fg")
        lo = fg - 0.012 if fg and fg > 0.98 else 0.99
        hi = og + 0.012 if og and og > 1 else 1.15
        names = set(self.sg_options())
        for sid, s in sensors.items():
            v = s.get("value")
            if s.get("name") in names and sid not in claimed and isinstance(v, (int, float)) and lo <= v <= hi:
                return sid
        return None

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

    # Rol van een actor: waar hij bij hoort, zodat apps geen namen hoeven te raden.
    def actor_role(self, aid: str) -> tuple[str, str | None]:
        data = self.data or {}
        for kind in ("fermenters", "kettles"):
            for o in data.get(kind, {}).values():
                for field, rol in (("heater", "heater"), ("cooler", "cooler"), ("valve", "valve"), ("agitator", "agitator")):
                    if o.get(field) == aid:
                        return rol, o.get("name")
        name = ((data.get("actors", {}).get(aid) or {}).get("name") or "")
        norm = "".join(ch for ch in name.lower() if ch.isalnum())
        if norm.startswith("autostart"):
            rest = norm[9:]
            for o in data.get("fermenters", {}).values():
                n = "".join(ch for ch in (o.get("name") or "").lower() if ch.isalnum())
                if n == rest or n + "1" == rest or n == rest + "1":
                    return "autostart", o.get("name")
        return "los", None

    @staticmethod
    def step_start(fermenter: dict):
        """Starttijd (unix) van de actieve stap: einde min de ingestelde duur."""
        st = None
        for s in fermenter.get("steps") or []:
            if s.get("status") == "A":
                st = s
        if not st:
            return None
        pr = st.get("props") or {}

        def num(k):
            try:
                return float(pr.get(k) or 0)
            except (TypeError, ValueError):
                return 0.0

        dur = num("TimerD") * 86400 + num("TimerH") * 3600 + (num("TimerM") + num("Timer")) * 60
        try:
            end = float(st.get("endtime") or 0)
        except (TypeError, ValueError):
            return None
        if end > 1e11:
            end /= 1000
        return end - dur if end > 1e9 and dur > 0 else None
