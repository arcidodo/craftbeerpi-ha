"""Actoren (pompen, kleppen, relais) en de regeling (autostart) van vergisters en ketels."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import CBPiEntity


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    ents = [Actor(coord, aid) for aid in coord.data["actors"]]
    for kind in ("fermenters", "kettles"):
        ents += [Control(coord, kind, oid) for oid in coord.data[kind]]
    add(ents)


class Actor(CBPiEntity, SwitchEntity):
    _attr_name = None

    def __init__(self, c, oid):
        super().__init__(c, "actors", oid, "switch")

    @property
    def is_on(self):
        st = self.obj.get("state")
        return st if isinstance(st, bool) else str(st).lower() == "on"

    async def async_turn_on(self, **kw):
        await self.coordinator.client.post(f"/actor/{self._oid}/on")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kw):
        await self.coordinator.client.post(f"/actor/{self._oid}/off")
        await self.coordinator.async_request_refresh()


class Control(CBPiEntity, SwitchEntity):
    """Temperatuurregeling aan/uit (CBPi 'toggle')."""
    _attr_name = "Regeling"
    _attr_icon = "mdi:thermostat-auto"

    def __init__(self, c, kind, oid):
        super().__init__(c, kind, oid, "control")
        self._path = "fermenter" if kind == "fermenters" else "kettle"

    @property
    def is_on(self):
        return bool(self.obj.get("state"))

    async def async_turn_on(self, **kw):
        if not self.is_on:
            await self.coordinator.client.post(f"/{self._path}/{self._oid}/toggle")
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kw):
        if self.is_on:
            await self.coordinator.client.post(f"/{self._path}/{self._oid}/toggle")
            await self.coordinator.async_request_refresh()
