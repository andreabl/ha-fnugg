"""Support for Fnugg"""

import asyncio
import datetime
import json
import logging
import time

import aiohttp
import async_timeout
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA

from homeassistant.helpers import config_validation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity

from homeassistant.const import (
    TEMP_CELSIUS,
    DEVICE_CLASS_TEMPERATURE,
)

from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT

_LOGGER = logging.getLogger(__name__)

DOMAIN = "fnugg"


SENSOR_TYPES = {
    "temp": [TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE],
    "snow_depth": ["cm", None],
    "last_updated": [None, None],
}

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Fnugg."""

    fnugg_data = FnuggData(async_get_clientsession(hass))

    if not await fnugg_data.get_user_credentials():
        _LOGGER.error("Failed to connect to Fnugg")
    if not await fnugg_data.update_data():
        _LOGGER.error("Failed to get data from Fnugg")

    dev = []
    for sensor_id, sensor in fnugg_data.sensors.items():
        if sensor[1] in SENSOR_TYPES:
            dev.append(Fnugg(sensor_id, sensor, fnugg_data))

    async_add_entities(dev)


class Fnugg(Entity):
    """Representation of resort."""

    _attr_state_class = STATE_CLASS_MEASUREMENT

    def __init__(self, sensor_id, sensor, fnugg_data):
        """Initialize the sensor."""
        self._sensor_id = sensor_id
        self._sensor = sensor
        self.fnugg_data = fnugg_data
        self._unit_of_measurement = SENSOR_TYPES[sensor[1]][0]
        self._device_class = SENSOR_TYPES[sensor[1]][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'Fnugg {self._sensor[2].get("roomName", "")} {self._sensor[1]}'

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._sensor_id

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "timestamp": datetime.datetime.fromisoformat(
                self._sensor[2].get("latestSample", "")
            )
        }

    @property
    def state(self):
        """Return the state of the device."""
        return self._sensor[0]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    async def async_update(self):
        """Get the latest data."""
        await self._fnugg_data.update()
        self._sensor = self._fnugg_data.sensors.get(self._sensor_id)

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class


class FnuggData:
    def __init__(self, session):
        self._updated_at = datetime.datetime.utcnow()
        self.sensors = {}
        self._session = session
        self._timeout = 10

    async def update(self, _=None, force_update=False):
        now = datetime.datetime.utcnow()
        elapsed = now - self._updated_at
        if elapsed < datetime.timedelta(minutes=20) and not force_update:
            return
        self._updated_at = now
        await self.update_data()

    async def update_data(self):
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    "https://api.fnugg.no/get/resort/14/",
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Fnugg, resp code: %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Fnugg: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False

        source = result.get("_source", {})
        conditions = source.get("conditions", {})
        
        self.sensors = {
            "temperature": (
                conditions.get("temperature", {}).get("value"),
                "temp",
                {"roomName": "Temperature"}
            ),
            "snow_depth": (
                conditions.get("snow_depth", {}).get("value"),
                "snow_depth",
                {"roomName": "Snow Depth"}
            ),
            "last_updated": (
                conditions.get("last_updated"),
                "last_updated",
                {"roomName": "Last Updated"}
            )
        }

        return True
