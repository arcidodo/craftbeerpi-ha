"""Vergisting: volgende stap, pauzeren, (verder) starten."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import CBPiEntity

ACTIONS = (("nextstep", "Volgende stap", "mdi:skip-next"), ("stopstep", "Pauzeren", "mdi:pause"), ("startstep", "Start / verder", "mdi:play"))


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    add([Act(coord, fid, *a) for fid in coord.data["fermenters"] for a in ACTIONS])


class Act(CBPiEntity, ButtonEntity):
    def __init__(self, c, oid, action, name, icon):
        super().__init__(c, "fermenters", oid, action)
        self._action = action
        self._attr_name = name
        self._attr_icon = icon

    async def async_press(self) -> None:
        await self.coordinator.client.post(f"/fermenter/{self._oid}/{self._action}")
        await self.coordinator.async_request_refresh()
