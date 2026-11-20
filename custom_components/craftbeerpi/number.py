"""Doeltemperatuur instellen."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .entity import CBPiEntity


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    ents = []
    for kind in ("fermenters", "kettles"):
        ents += [Target(coord, kind, oid) for oid in coord.data[kind]]
    for fid in coord.data["fermenters"]:
        ents += [Gravity(coord, fid, "og", "Start-SG (OG)"), Gravity(coord, fid, "fg", "Eind-SG (FG)")]
    add(ents)


class Target(CBPiEntity, NumberEntity):
    _attr_name = "Doel instellen"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 0
    _attr_native_max_value = 110
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, c, kind, oid):
        super().__init__(c, kind, oid, "settarget")
        self._path = "fermenter" if kind == "fermenters" else "kettle"

    @property
    def native_value(self):
        try:
            return float(self.obj.get("target_temp"))
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.post(f"/{self._path}/{self._oid}/target_temp", {"temp": value})
        await self.coordinator.async_request_refresh()


class Gravity(CBPiEntity, RestoreNumber):
    """Begin- of eind-SG van het brouwsel; CBPi bewaart die niet, dus houdt HA ze bij."""
    _attr_native_min_value = 0.9
    _attr_native_max_value = 1.2
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:flask-outline"

    def __init__(self, c, fid, key, name):
        super().__init__(c, "fermenters", fid, key)
        self._fid = fid
        self._key = key
        self._attr_name = name

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last and last.native_value:
            self.coordinator.local.setdefault(self._fid, {})[self._key] = last.native_value

    @property
    def native_value(self):
        return self.coordinator.local.get(self._fid, {}).get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_local(self._fid, self._key, value if value > 0.98 else None)
