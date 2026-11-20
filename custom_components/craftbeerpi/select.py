"""Welke iSpindel de SG van een vergister levert."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import CBPiEntity

AUTO = "auto"


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    add([SGSource(coord, fid) for fid in coord.data["fermenters"]])


class SGSource(CBPiEntity, SelectEntity, RestoreEntity):
    _attr_name = "SG-bron"
    _attr_icon = "mdi:flask-outline"

    def __init__(self, c, fid):
        super().__init__(c, "fermenters", fid, "sgsource")
        self._fid = fid

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            self.coordinator.local.setdefault(self._fid, {})["src"] = last.state

    @property
    def options(self) -> list[str]:
        return [AUTO] + self.coordinator.sg_options()

    @property
    def current_option(self):
        v = self.coordinator.local.get(self._fid, {}).get("src", AUTO)
        return v if v in self.options else AUTO

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_local(self._fid, "src", option)
