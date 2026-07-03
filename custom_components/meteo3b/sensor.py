"""Sensori aggiuntivi per 3bMeteo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _giorni(data: dict) -> list[dict]:
    return (data or {}).get("previsione_giorno", [])


def _oggi(data: dict) -> dict:
    g = _giorni(data)
    return g[0] if g else {}


def _tempo_medio_oggi(data: dict) -> dict:
    return _oggi(data).get("tempo_medio", {})


def _ora_corrente(data: dict) -> dict:
    from datetime import datetime
    oraria = _oggi(data).get("previsione_oraria", [])
    if not oraria:
        return {}
    now_hour = datetime.now().hour
    best = oraria[0]
    for entry in oraria:
        if entry.get("ora") == now_hour:
            return entry
        if entry.get("ora", 0) <= now_hour:
            best = entry
    return best


def _effemeridi(data: dict) -> dict:
    return _oggi(data).get("effemeridi", {})


# ---------- sensor descriptions ----------

@dataclass
class Meteo3bSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] = None
    custom_unit: str | None = None
    custom_icon: str | None = None


SENSORS: list[Meteo3bSensorDescription] = [
    Meteo3bSensorDescription(
        key="temperatura",
        name="Temperatura",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        custom_unit=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: _float(_ora_corrente(d).get("temperatura", {}).get("gradi")),
    ),
    Meteo3bSensorDescription(
        key="percepita",
        name="Temperatura Percepita",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        custom_unit=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: _float(_ora_corrente(d).get("tpercepita")),
    ),
    Meteo3bSensorDescription(
        key="umidita",
        name="Umidità",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        custom_unit=PERCENTAGE,
        value_fn=lambda d: _float(_ora_corrente(d).get("hr")),
    ),
    Meteo3bSensorDescription(
        key="pressione",
        name="Pressione",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        custom_unit=UnitOfPressure.HPA,
        value_fn=lambda d: _float(_ora_corrente(d).get("pr")),
    ),
    Meteo3bSensorDescription(
        key="vento",
        name="Velocità Vento",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        custom_unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
        value_fn=lambda d: _float(_ora_corrente(d).get("vento", {}).get("intensita")),
    ),
    Meteo3bSensorDescription(
        key="condizione",
        name="Condizione Meteo",
        custom_icon="mdi:weather-partly-cloudy",
        value_fn=lambda d: _ora_corrente(d).get("desc_breve"),
    ),
    Meteo3bSensorDescription(
        key="max_oggi",
        name="Temperatura Massima Oggi",
        device_class=SensorDeviceClass.TEMPERATURE,
        custom_unit=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: _float(_tempo_medio_oggi(d).get("t_max")),
    ),
    Meteo3bSensorDescription(
        key="min_oggi",
        name="Temperatura Minima Oggi",
        device_class=SensorDeviceClass.TEMPERATURE,
        custom_unit=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: _float(_tempo_medio_oggi(d).get("t_min")),
    ),
    Meteo3bSensorDescription(
        key="uv",
        name="Indice UV",
        state_class=SensorStateClass.MEASUREMENT,
        custom_icon="mdi:weather-sunny-alert",
        value_fn=lambda d: _float(_ora_corrente(d).get("uv")),
    ),
    Meteo3bSensorDescription(
        key="attendibilita",
        name="Attendibilità Previsione",
        custom_icon="mdi:chart-line",
        value_fn=lambda d: _oggi(d).get("attendibilita"),
    ),
    Meteo3bSensorDescription(
        key="alba",
        name="Alba",
        custom_icon="mdi:weather-sunset-up",
        value_fn=lambda d: _effemeridi(d).get("alba"),
    ),
    Meteo3bSensorDescription(
        key="tramonto",
        name="Tramonto",
        custom_icon="mdi:weather-sunset-down",
        value_fn=lambda d: _effemeridi(d).get("tramonto"),
    ),
    Meteo3bSensorDescription(
        key="precipitazioni_oggi",
        name="Precipitazioni Oggi",
        custom_icon="mdi:weather-rainy",
        custom_unit="mm",
        value_fn=lambda d: _float(_tempo_medio_oggi(d).get("precipitazioni")),
    ),
]


# ---------- setup ----------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        Meteo3bSensor(coordinator, entry, desc) for desc in SENSORS
    ])


# ---------- entity ----------

class Meteo3bSensor(CoordinatorEntity, SensorEntity):
    """Sensore generico 3bMeteo."""

    def __init__(self, coordinator, entry: ConfigEntry, desc: Meteo3bSensorDescription) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"meteo3b_{entry.data['loc_id']}_{desc.key}"
        self._attr_name = f"{entry.data.get('name', '3bMeteo')} {desc.name}"
        if desc.custom_unit:
            self._attr_native_unit_of_measurement = desc.custom_unit
        if desc.device_class:
            self._attr_device_class = desc.device_class
        if desc.state_class:
            self._attr_state_class = desc.state_class
        if desc.custom_icon:
            self._attr_icon = desc.custom_icon

    @property
    def native_value(self) -> Any:
        if self.coordinator.data and self._desc.value_fn:
            return self._desc.value_fn(self.coordinator.data)
        return None
