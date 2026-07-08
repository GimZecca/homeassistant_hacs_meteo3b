"""Entità Weather per 3bMeteo — condizioni attuali, previsioni orarie e giornaliere."""
from __future__ import annotations

import logging
from datetime import datetime, date, time

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mappa descrizione testuale 3bMeteo -> condizione Home Assistant.
# 3bMeteo non espone un set stabile di ID simbolo nell'API pubblica; il
# testo "desc_breve" è invece coerente ed è la chiave più affidabile.
CONDITION_MAP: dict[str, str] = {
    "sereno":            "sunny",
    "poco nuvoloso":     "partlycloudy",
    "nubi sparse":       "partlycloudy",
    "parz nuvoloso":     "partlycloudy",
    "parzialmente nuvoloso": "partlycloudy",
    "velature":          "partlycloudy",
    "velature sparse":   "partlycloudy",
    "velature estese":   "cloudy",
    "molto nuvoloso":    "cloudy",
    "nuvoloso":          "cloudy",
    "coperto":           "cloudy",
    "variabile":         "partlycloudy",
    "pioviggine":        "rainy",
    "pioggia":           "rainy",
    "piogge":            "rainy",
    "piogge sparse":     "rainy",
    "possibili piogge":  "rainy",
    "rovesci":           "rainy",
    "rovesci sparsi":    "rainy",
    "temporale":         "lightning-rainy",
    "temporali":         "lightning-rainy",
    "temporali sparsi":  "lightning-rainy",
    "possibile temporale": "lightning-rainy",
    "neve":              "snowy",
    "nevischio":         "snowy",
    "pioggia mista neve":"snowy-rainy",
    "grandine":          "hail",
    "nebbia":            "fog",
    "foschia":           "fog",
    "vento forte":       "windy",
}

# Mappa direzione bussola (16 punti, italiano) -> gradi
COMPASS_DEGREES: dict[str, float] = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSO": 202.5, "SO": 225, "OSO": 247.5,
    "O": 270, "ONO": 292.5, "NO": 315, "NNO": 337.5,
}


def _condition(desc: str | None) -> str:
    if not desc:
        return "exceptional"
    return CONDITION_MAP.get(desc.strip().lower(), "exceptional")


def _wind_speed(vento: dict | None) -> float | None:
    if not vento:
        return None
    try:
        return float(vento.get("intensita"))
    except (TypeError, ValueError):
        return None


def _wind_bearing(vento: dict | None) -> float | None:
    if not vento:
        return None
    return COMPASS_DEGREES.get(vento.get("direzione", "").strip().upper())


def _float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------- setup ----------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Meteo3bWeather(coordinator, entry)])


# ---------- entity ----------

class Meteo3bWeather(CoordinatorEntity, WeatherEntity):
    """Rappresenta il meteo corrente con previsioni orarie e giornaliere."""

    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit  = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_pressure_unit    = UnitOfPressure.HPA

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"meteo3b_{entry.data['loc_id']}_weather"
        self._attr_name = entry.data.get("name", "3bMeteo")

    @property
    def _giorni(self) -> list[dict]:
        return (self.coordinator.data or {}).get("previsione_giorno", [])

    @property
    def _oggi(self) -> dict:
        giorni = self._giorni
        return giorni[0] if giorni else {}

    @property
    def _ora_corrente(self) -> dict:
        """Trova l'entry oraria più vicina all'ora attuale nel giorno odierno."""
        oraria = self._oggi.get("previsione_oraria", [])
        if not oraria:
            return {}
        now_hour = datetime.now().hour
        # cerca match esatto, altrimenti il più vicino per difetto
        best = oraria[0]
        for entry in oraria:
            if entry.get("ora") == now_hour:
                return entry
            if entry.get("ora", 0) <= now_hour:
                best = entry
        return best

    @property
    def native_temperature(self) -> float | None:
        t = self._ora_corrente.get("temperatura", {})
        return _float(t.get("gradi"))

    @property
    def humidity(self) -> float | None:
        return _float(self._ora_corrente.get("hr"))

    @property
    def native_pressure(self) -> float | None:
        return _float(self._ora_corrente.get("pr"))

    @property
    def native_wind_speed(self) -> float | None:
        return _wind_speed(self._ora_corrente.get("vento"))

    @property
    def wind_bearing(self) -> float | None:
        return _wind_bearing(self._ora_corrente.get("vento"))

    @property
    def condition(self) -> str | None:
        return _condition(self._ora_corrente.get("desc_breve"))

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return self._hourly()

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return self._daily()

    def _hourly(self) -> list[Forecast]:
        forecasts: list[Forecast] = []
        for giorno in self._giorni:
            data_str = giorno.get("data")
            if not data_str:
                continue
            try:
                day = date.fromisoformat(data_str)
            except ValueError:
                continue
            for r in giorno.get("previsione_oraria", []):
                ora = r.get("ora")
                if ora is None:
                    continue
                dt = datetime.combine(day, time(hour=ora)).isoformat()
                t = r.get("temperatura", {})
                forecasts.append(Forecast(
                    datetime=dt,
                    native_temperature=_float(t.get("gradi")),
                    condition=_condition(r.get("desc_breve")),
                    native_precipitation=_float(r.get("precipitazioni")),
                    precipitation_probability=_float(r.get("probabilita_prec")),
                    humidity=_float(r.get("hr")),
                    native_wind_speed=_wind_speed(r.get("vento")),
                    wind_bearing=_wind_bearing(r.get("vento")),
                ))
        return forecasts[:72]

    def _daily(self) -> list[Forecast]:
        forecasts: list[Forecast] = []
        for giorno in self._giorni:
            data_str = giorno.get("data")
            if not data_str:
                continue
            tm = giorno.get("tempo_medio", {})
            forecasts.append(Forecast(
                datetime=f"{data_str}T12:00:00",
                native_temperature=_float(tm.get("t_max")),
                native_templow=_float(tm.get("t_min")),
                condition=_condition(tm.get("desc_breve")),
                native_precipitation=_float(tm.get("precipitazioni")),
                precipitation_probability=_float(tm.get("probabilita_prec")),
                native_wind_speed=_wind_speed(tm.get("vento")),
                wind_bearing=_wind_bearing(tm.get("vento")),
            ))
        return forecasts
