"""Verwarmt / koelt / regeling actief."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from .entity import CBPiEntity


def _on(coord, aid):
    a = coord.data["actors"].get(aid) if aid else None
    st = (a or {}).get("state")
    return st if isinstance(st, bool) else str(st).lower() == "on" if st is not None else None


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    ents = []
    for kind in ("fermenters", "kettles"):
        for oid, o in coord.data[kind].items():
            if o.get("heater"):
                ents.append(Out(coord, kind, oid, "heater", "Verwarming", "mdi:fire", BinarySensorDeviceClass.HEAT))
            if o.get("cooler"):
                ents.append(Out(coord, kind, oid, "cooler", "Koeling", "mdi:snowflake", BinarySensorDeviceClass.COLD))
            ents.append(Running(coord, kind, oid))
    add(ents)


class Out(CBPiEntity, BinarySensorEntity):
    def __init__(self, c, kind, oid, field, name, icon, dc):
        super().__init__(c, kind, oid, field)
        self._field = field
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_class = dc

    @property
    def is_on(self):
        return _on(self.coordinator, self.obj.get(self._field))


class Running(CBPiEntity, BinarySensorEntity):
    _attr_name = "Regeling actief"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, c, kind, oid):
        super().__init__(c, kind, oid, "running")

    @property
    def is_on(self):
        return bool(self.obj.get("state"))
