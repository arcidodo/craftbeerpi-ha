"""Vergisting: volgende stap, pauzeren, (verder) starten."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import CBPiEntity

ACTIONS = (("nextstep", "Volgende stap", "mdi:skip-next"), ("stopstep", "Pauzeren", "mdi:pause"), ("startstep", "Start / verder", "mdi:play"))

MASH = (("next", "Volgende stap", "mdi:skip-next"), ("stop", "Stop", "mdi:stop"), ("start", "Start brouwdag", "mdi:play"))


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    add([Act(coord, fid, *a) for fid in coord.data["fermenters"] for a in ACTIONS] + [Mash(coord, *m) for m in MASH])


class Act(CBPiEntity, ButtonEntity):
    def __init__(self, c, oid, action, name, icon):
        super().__init__(c, "fermenters", oid, action)
        self._action = action
        self._attr_name = name
        self._attr_icon = icon

    async def async_press(self) -> None:
        await self.coordinator.client.post(f"/fermenter/{self._oid}/{self._action}")
        await self.coordinator.async_request_refresh()


class Mash(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, c, action, name, icon):
        super().__init__(c)
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{c.config_entry.entry_id}_brouwdag_{action}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{c.config_entry.entry_id}_brouwdag")}, name="Brouwdag", manufacturer="CraftBeerPi 4", model="Brouwdag")

    async def async_press(self) -> None:
        await self.coordinator.client.post(f"/step2/{self._action}")
        await self.coordinator.async_request_refresh()
