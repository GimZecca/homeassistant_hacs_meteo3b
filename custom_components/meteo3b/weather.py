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

# Mappa ufficiale id_simbolo -> condizione HA, ricavata dalle risorse
# dell'app Android (res/xml-it/weather_symbols.xml). Molto più stabile
# del testo libero "desc_breve", che varia con suffissi come "debole",
# "forte", "e schiarite", "possibile" ecc.
SYMBOL_CONDITION_MAP: dict[str, str] = {
    # Sereno
    "1": "sunny", "2": "sunny", "3": "sunny", "14": "sunny", "50": "sunny",
    # Nubi sparse
    "4": "partlycloudy", "6": "partlycloudy", "7": "partlycloudy",
    "43": "partlycloudy", "46": "partlycloudy",
    # Nuvoloso / Coperto
    "12": "cloudy", "15": "cloudy",
    "16": "cloudy", "17": "cloudy", "39": "cloudy",
    # Pioviggine / Pioggia moderata
    "8": "rainy", "19": "rainy", "21": "rainy",
    "20": "rainy", "22": "rainy", "23": "rainy",
    "26": "rainy", "42": "rainy", "45": "rainy",
    # Pioggia forte -> "pouring" (pioggia intensa, condizione HA dedicata)
    "24": "pouring", "25": "pouring", "27": "pouring",
    # Temporale / Temporale forte
    "5": "lightning-rainy", "9": "lightning-rainy", "10": "lightning-rainy",
    "11": "lightning-rainy", "28": "lightning-rainy", "29": "lightning-rainy",
    # Nevischio / Neve moderata / Neve forte / Neve tonda
    "32": "snowy", "33": "snowy",
    "13": "snowy", "34": "snowy", "35": "snowy",
    "47": "snowy", "49": "snowy", "51": "snowy",
    "30": "snowy", "36": "snowy", "37": "snowy",
    # Nebbia / Foschia
    "38": "fog", "40": "fog", "41": "fog", "44": "fog",
    # Pioggia e neve
    "48": "snowy-rainy", "18": "snowy-rainy", "31": "snowy-rainy",
}

# Fallback per parole chiave su "desc_breve", usato solo quando id_simbolo
# non è tra quelli noti sopra (es. codici introdotti lato server dopo il
# rilascio della versione app da cui è stata estratta la mappa ufficiale).
_KEYWORD_FALLBACK: list[tuple[str, str]] = [
    ("temporale", "lightning-rainy"),
    ("grandine", "hail"),
    ("neve", "snowy"),
    ("nevischio", "snowy"),
    ("rovesci", "rainy"),
    ("pioggia", "rainy"),
    ("piogge", "rainy"),
    ("pioviggine", "rainy"),
    ("nebbia", "fog"),
    ("foschia", "fog"),
    ("sereno", "sunny"),
    ("coperto", "cloudy"),
    ("molto nuvoloso", "cloudy"),
    ("nuvol", "partlycloudy"),
    ("velatur", "partlycloudy"),
    ("variabile", "partlycloudy"),
    ("vento", "windy"),
]


def _condition_from_symbol(id_simbolo, desc_breve: str | None = None) -> str:
    """Determina la condizione HA da id_simbolo (primario) o desc_breve (fallback)."""
    key = str(id_simbolo).strip()
    if key in SYMBOL_CONDITION_MAP:
        return SYMBOL_CONDITION_MAP[key]

    if desc_breve:
        d = desc_breve.strip().lower()
        for keyword, condition in _KEYWORD_FALLBACK:
            if keyword in d:
                return condition

    return "exceptional"


def _wind_speed(vento: dict | None) -> float | None:
    if not vento:
        return None
    try:
        return float(vento.get("intensita"))
    except (TypeError, ValueError):
        return None


# Mappa direzione bussola (16 punti, italiano) -> gradi
COMPASS_DEGREES: dict[str, float] = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5,
    "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSO": 202.5, "SO": 225, "OSO": 247.5,
    "O": 270, "ONO": 292.5, "NO": 315, "NNO": 337.5,
}


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
        r = self._ora_corrente
        return _condition_from_symbol(r.get("id_simbolo", ""), r.get("desc_breve"))

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
                    condition=_condition_from_symbol(r.get("id_simbolo", ""), r.get("desc_breve")),
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
                condition=_condition_from_symbol(tm.get("id_simbolo", ""), tm.get("desc_breve")),
                native_precipitation=_float(tm.get("precipitazioni")),
                precipitation_probability=_float(tm.get("probabilita_prec")),
                native_wind_speed=_wind_speed(tm.get("vento")),
                wind_bearing=_wind_bearing(tm.get("vento")),
            ))
        return forecasts
