"""Integrazione 3bMeteo per Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URL, API_KEY, DOMAIN, FORECAST_DAYS, LANGUAGE, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.WEATHER, Platform.SENSOR]


async def async_fetch_data(hass: HomeAssistant, loc_id: int, sec_id: int) -> dict:
    """Scarica e restituisce le previsioni orarie/giornaliere da 3bMeteo.

    Usa l'endpoint api_previsioni/orario che include sia il dettaglio orario
    sia il riepilogo giornaliero (tempo_medio) per ogni giorno.
    """
    session = async_get_clientsession(hass)
    url = f"{BASE_URL}api_previsioni/orario/{loc_id}/{sec_id}/0/{FORECAST_DAYS}/{LANGUAGE}"
    params = {
        "format": "json2",
        "X-API-KEY": API_KEY,
    }
    try:
        async with async_timeout.timeout(15):
            resp = await session.get(url, params=params)
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    except Exception as err:
        raise UpdateFailed(f"Errore di rete: {err}") from err

    if not data or "localita" not in data:
        raise UpdateFailed("3bMeteo: risposta non valida")

    return data["localita"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura l'integrazione da un config entry."""
    loc_id = entry.data["loc_id"]
    sec_id = entry.data["sec_id"]

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"3bMeteo {entry.data.get('name', loc_id)}",
        update_method=lambda: async_fetch_data(hass, loc_id, sec_id),
        update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Rimuove il config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
