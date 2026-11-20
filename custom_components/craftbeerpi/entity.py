"""Basisentiteit."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CBPiCoordinator


class CBPiEntity(CoordinatorEntity[CBPiCoordinator]):
    _attr_has_entity_name = True
    _kind = ""   # fermenters / kettles / actors / sensors

    def __init__(self, coord: CBPiCoordinator, kind: str, oid: str, key: str) -> None:
        super().__init__(coord)
        self._kind = kind
        self._oid = oid
        self._attr_unique_id = f"{coord.config_entry.entry_id}_{kind}_{oid}_{key}"
        label = {"fermenters": "Vergister", "kettles": "Ketel", "actors": "Actor", "sensors": "Sensor"}[kind]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coord.config_entry.entry_id}_{kind}_{oid}")},
            name=self.obj.get("name", oid),
            manufacturer="CraftBeerPi 4",
            model=label,
        )

    @property
    def obj(self) -> dict:
        return (self.coordinator.data or {}).get(self._kind, {}).get(self._oid) or getattr(self, "_last", {})

    @property
    def available(self) -> bool:
        return super().available and bool((self.coordinator.data or {}).get(self._kind, {}).get(self._oid))

    def sensor_value(self, sid: str | None):
        if not sid:
            return None
        return ((self.coordinator.data or {}).get("sensors", {}).get(sid) or {}).get("value")
