"""Config flow for Fnugg integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def get_resorts(hass: HomeAssistant) -> list[dict[str, str]]:
    """Get list of available resorts from Fnugg API."""
    session = async_get_clientsession(hass)
    resorts = []
    
    try:
        _LOGGER.debug("Fetching resorts from Fnugg API")
        async with session.get("https://api.fnugg.no/search?size=150") as resp:
            if resp.status != 200:
                _LOGGER.error("Failed to get resorts. Status: %s", resp.status)
                raise CannotConnect
            
            data = await resp.json()
            _LOGGER.debug("Got response from Fnugg API")
            
            hits = data.get("hits", {}).get("hits", [])
            _LOGGER.debug("Found %d resorts", len(hits))
            
            for hit in hits:
                source = hit.get("_source", {})
                resort_id = hit.get("_id")
                name = source.get("name")
                if resort_id and name:
                    resorts.append({
                        "label": str(name),
                        "value": str(resort_id)
                    })
                    _LOGGER.debug("Added resort: %s (ID: %s)", name, resort_id)
            
            sorted_resorts = sorted(resorts, key=lambda x: x["label"])
            _LOGGER.debug("Returning %d sorted resorts", len(sorted_resorts))
            return sorted_resorts
            
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to Fnugg: %s", err)
        raise CannotConnect from err

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fnugg."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._resorts: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        try:
            if not self._resorts:
                self._resorts = await get_resorts(self.hass)
                _LOGGER.debug("Got %d resorts for config flow", len(self._resorts))
        except CannotConnect:
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                errors=errors,
            )

        if user_input is not None:
            resort_id = user_input["resort"]
            resort_name = next(
                (resort["label"] for resort in self._resorts if resort["value"] == resort_id),
                resort_id
            )

            await self.async_set_unique_id(resort_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=resort_name,
                data={"resort_id": resort_id, "name": resort_name}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("resort"): vol.In({
                    resort["value"]: resort["label"] 
                    for resort in self._resorts
                })
            }),
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""