"""Config flow per 3bMeteo con ricerca live della località."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import DOMAIN, async_fetch_data
from .comuni_api import async_search_localita

_LOGGER = logging.getLogger(__name__)


class Meteo3bConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow a più passi: cerca → seleziona → conferma."""

    VERSION = 1

    def __init__(self):
        self._search_results: list[dict] = []

    async def async_step_user(self, user_input=None):
        """Passo 1: campo di ricerca per nome località."""
        errors = {}

        if user_input is not None:
            query = user_input.get("search", "").strip()
            if len(query) < 2:
                errors["search"] = "too_short"
            else:
                self._search_results = await async_search_localita(self.hass, query)
                if not self._search_results:
                    errors["search"] = "no_results"
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("search"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
            }),
            errors=errors,
            description_placeholders={
                "example": "es. Milano, Roma, Torino...",
            },
        )

    async def async_step_select(self, user_input=None):
        """Passo 2: lista dropdown con i risultati della ricerca."""
        errors = {}

        if user_input is not None:
            chosen_label = user_input.get("location", "")

            if chosen_label == "__manual__":
                return await self.async_step_manual()

            chosen = next(
                (r for r in self._search_results if r["label"] == chosen_label),
                None,
            )
            if not chosen:
                errors["location"] = "invalid_selection"
            else:
                try:
                    await self._validate(chosen["loc_id"], chosen["sec_id"])
                    return self.async_create_entry(
                        title=chosen["nome"],
                        data={
                            "loc_id": chosen["loc_id"],
                            "sec_id": chosen["sec_id"],
                            "name": chosen["nome"],
                        },
                    )
                except CannotConnect:
                    errors["location"] = "cannot_connect"

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({
                vol.Required("location"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": r["label"], "label": r["label"]}
                            for r in self._search_results
                        ] + [{"value": "__manual__", "label": "✏️ Inserisci ID manualmente..."}],
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "count": str(len(self._search_results)),
            },
        )

    async def async_step_manual(self, user_input=None):
        """Passo alternativo: inserisci loc_id e sec_id direttamente."""
        errors = {}

        if user_input is not None:
            try:
                loc_id = int(user_input["loc_id"])
                sec_id = int(user_input["sec_id"])
                await self._validate(loc_id, sec_id)
                return self.async_create_entry(
                    title=f"3bMeteo {loc_id}",
                    data={
                        "loc_id": loc_id,
                        "sec_id": sec_id,
                        "name": f"Località {loc_id}",
                    },
                )
            except (ValueError, TypeError):
                errors["loc_id"] = "invalid_id"
            except CannotConnect:
                errors["loc_id"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required("loc_id"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.NUMBER)
                ),
                vol.Required("sec_id"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.NUMBER)
                ),
            }),
            errors=errors,
        )

    async def _validate(self, loc_id: int, sec_id: int) -> None:
        """Verifica che la combinazione loc_id/sec_id restituisca dati validi."""
        try:
            await async_fetch_data(self.hass, loc_id, sec_id)
        except Exception as err:
            raise CannotConnect(str(err)) from err


class CannotConnect(HomeAssistantError):
    """Errore di connessione."""
