"""Ricerca località su 3bMeteo (method=ricerca_elastic_search).

A differenza di ilMeteo, 3bMeteo non richiede un database locale scaricato:
la ricerca avviene live ad ogni richiesta tramite l'endpoint elastic search,
che restituisce già id (loc_id) e id_settore (sec_id) necessari per le
chiamate successive.
"""
from __future__ import annotations

import logging

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_KEY, BASE_URL

_LOGGER = logging.getLogger(__name__)


async def async_search_localita(hass: HomeAssistant, query: str) -> list[dict]:
    """Cerca località per nome, restituisce lista di risultati normalizzati."""
    session = async_get_clientsession(hass)
    url = f"{BASE_URL}api_localita/ricerca_elastic_search/{query}"
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
        _LOGGER.warning("3bMeteo: errore ricerca località: %s", err)
        return []

    risultati = data.get("localita", []) if data else []

    results = []
    for r in risultati:
        try:
            loc_id = r["id"]
            sec_id = r["id_settore"]
            nome = r["localita"]
            prov = r.get("prov", "")
            regione = r.get("regione", "")
            results.append({
                "loc_id": loc_id,
                "sec_id": sec_id,
                "nome": nome,
                "prov": prov,
                "regione": regione,
                "label": f"{nome} ({prov}) — {regione}" if prov else f"{nome} — {regione}",
            })
        except (KeyError, TypeError):
            continue

    return results
