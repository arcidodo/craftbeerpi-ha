"""Sensoren: temperatuur, SG, stap, brouwsel, eindtijd, losse CBPi-sensoren."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .entity import CBPiEntity


def _step_end(f: dict):
    st = next((s for s in f.get("steps") or [] if s.get("status") == "A"), None)
    try:
        e = float((st or {}).get("endtime") or 0)
    except (TypeError, ValueError):
        return None
    if e <= 1e9:
        return None
    return datetime.fromtimestamp(e / 1000 if e > 1e11 else e, tz=timezone.utc)


async def async_setup_entry(hass, entry, add):
    coord = hass.data[DOMAIN][entry.entry_id]
    ents = []
    for fid, f in coord.data["fermenters"].items():
        ents += [FermTemp(coord, fid), FermTarget(coord, fid), FermBrew(coord, fid), FermStep(coord, fid), FermStepEnd(coord, fid)]
        ents += [FermSG(coord, fid), AlcoholNow(coord, fid), AlcoholFinal(coord, fid), Attenuation(coord, fid)]
    for kid in coord.data["kettles"]:
        ents.append(KettleTemp(coord, kid))
    for sid, s in coord.data["sensors"].items():
        ents.append(RawSensor(coord, sid, s))
    add(ents)


class FermTemp(CBPiEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Temperatuur"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "temp")

    @property
    def native_value(self):
        return self.sensor_value(self.obj.get("sensor"))


class FermTarget(CBPiEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_name = "Doeltemperatuur"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "target")

    @property
    def native_value(self):
        return self.obj.get("target_temp")


class FermSG(CBPiEntity, SensorEntity):
    _attr_name = "SG"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3
    _attr_icon = "mdi:flask-outline"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "sg")

    @property
    def native_value(self):
        return self.coordinator.sg_value(self._oid)


class FermBrew(CBPiEntity, SensorEntity):
    _attr_name = "Brouwsel"
    _attr_icon = "mdi:beer"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "brew")

    @property
    def native_value(self):
        return self.obj.get("brewname") or None


class FermStep(CBPiEntity, SensorEntity):
    _attr_name = "Actieve stap"
    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "step")

    @property
    def native_value(self):
        st = self.coordinator.active_step(self.obj)
        return st.get("name") if st else "Geen"

    @property
    def extra_state_attributes(self):
        f = self.obj
        steps = f.get("steps") or []
        st = self.coordinator.active_step(f)
        return {
            "status_tekst": (st or {}).get("state_text"),
            "stappen_totaal": len(steps),
            "stappen_klaar": sum(1 for s in steps if s.get("status") == "D"),
            "stappen": [{"naam": s.get("name"), "status": s.get("status")} for s in steps],
        }


class FermStepEnd(CBPiEntity, SensorEntity):
    _attr_name = "Stap eindigt"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "stepend")

    @property
    def native_value(self):
        return _step_end(self.obj)


class KettleTemp(CBPiEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Temperatuur"

    def __init__(self, c, oid):
        super().__init__(c, "kettles", oid, "temp")

    @property
    def native_value(self):
        return self.sensor_value(self.obj.get("sensor"))


class RawSensor(CBPiEntity, SensorEntity):
    """Elke CBPi-sensor (OneWire, iSpindel, ESPHome, …) als eigen entiteit. Eenheid wordt uit de naam afgeleid."""
    _attr_name = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, c, oid, s):
        super().__init__(c, "sensors", oid, "value")
        n = (s.get("name") or "").lower()
        if "battery" in n:
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = "V"
        elif "plato" in n:
            self._attr_native_unit_of_measurement = "°P"
        elif "gravity" in n or n.endswith(" sg"):
            self._attr_suggested_display_precision = 3
            self._attr_icon = "mdi:flask-outline"
        elif "temp" in n or s.get("type") in ("OneWire",) or "thermowell" in n or "koelkast" in n:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        return self.obj.get("value")


def _gl(c, fid):
    d = c.local.get(fid, {})
    return d.get("og"), d.get("fg")


class AlcoholNow(CBPiEntity, SensorEntity):
    """Alcohol nu = (OG - SG nu) x 131,25."""
    _attr_name = "Alcohol (nu)"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:glass-mug-variant"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "abv_now")

    @property
    def native_value(self):
        og, _ = _gl(self.coordinator, self._oid)
        sg = self.coordinator.sg_value(self._oid)
        return round(max(0.0, (og - sg) * 131.25), 2) if og and sg and og > sg - 0.02 else None


class AlcoholFinal(CBPiEntity, SensorEntity):
    """Alcohol eind = (OG - FG) x 131,25, zodra beide zijn ingevuld."""
    _attr_name = "Alcohol (eind)"
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:glass-mug-variant"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "abv_final")

    @property
    def native_value(self):
        og, fg = _gl(self.coordinator, self._oid)
        return round(max(0.0, (og - fg) * 131.25), 2) if og and fg and og > fg else None


class Attenuation(CBPiEntity, SensorEntity):
    """Vergistingsgraad = (OG - SG nu) / (OG - 1)."""
    _attr_name = "Vergistingsgraad"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:percent"

    def __init__(self, c, oid):
        super().__init__(c, "fermenters", oid, "attenuation")

    @property
    def native_value(self):
        og, _ = _gl(self.coordinator, self._oid)
        sg = self.coordinator.sg_value(self._oid)
        return round(max(0.0, min(100.0, (og - sg) / (og - 1) * 100)), 1) if og and sg and og > 1.0 else None
