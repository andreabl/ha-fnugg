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
    UnitOfTemperature,
)

#{% set direction = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW','N'] %}
#{% set degree = states('sensor.wind_bearing')|float %}
#{{ direction[((degree+11.25)/22.5)|int] }}
#sensor:
#  - platform: template
#    sensors:
#      your_wind_sensor:
#        value_template: >
#          {% set direction = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW','N'] %}
#          {% set degree = states('sensor.wind_bearing')|float %}
#          {{ direction[((degree+11.25)/22.5)|int] }}



from .const import (
    LIFT_STATUS,
    SENSOR_TYPES,
    NUMERIC_SENSORS,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "fnugg"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Fnugg from a config entry."""
    resort_id = config_entry.data["resort_id"]
    resort_name = config_entry.data["name"]
    
    fnugg_data = FnuggData(
        async_get_clientsession(hass),
        resort_id,
        resort_name
    )

    if not await fnugg_data.update_data():
        _LOGGER.error("Failed to get data from Fnugg")
        return

    dev = []
    for sensor_id, sensor_data in fnugg_data.sensors.items():
        dev.append(Fnugg(sensor_id, sensor_data, fnugg_data))

    async_add_entities(dev)


class Fnugg(SensorEntity):
    """Representation of a Fnugg sensor."""

    def __init__(self, sensor_id, sensor, fnugg_data):
        """Initialize the sensor."""
        super().__init__()
        self._sensor_id = sensor_id
        self._sensor = sensor
        self._fnugg_data = fnugg_data
        self._attr_device_class = None
        
        # Get resort info for device info
        self._resort_id = fnugg_data._resort_id
        self._resort_name = fnugg_data._resort_name

        _LOGGER.debug("Creating SensorEntity: %s" % sensor_id)

        
        # Create friendly name for sensors
        if sensor_id.startswith("lift_"):
            lift_name = sensor_id.replace("lift_", "").replace("_", " ").title()
            if sensor_id.endswith("_numeric"):
                self._attr_name = f"{lift_name} Status Numeric"
            else:
                self._attr_name = f"{lift_name} Status"
        elif sensor_id.startswith("facility_"):
            facility_name = sensor_id.replace("facility_", "").replace("_", " ").title()
            self._attr_name = f"{facility_name}"
        else:
            self._attr_name = sensor_id.replace("_", " ").title()
            
        self._attr_unique_id = f"fnugg_{self._resort_id}_{sensor_id}"
        
        # Define text-based sensors
        TEXT_SENSORS = [
            "lifts_status_text",
            "slopes_status",
            "resort_status",
            "condition_description",
            "resort_opening_date",
            "resort_closing_date",
            "facility_status"
        ]
        
        # Modify the state class logic
        if (sensor_id in NUMERIC_SENSORS or 
            sensor_id.endswith("_numeric")):
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_id in TEXT_SENSORS or sensor_id.endswith("_text"):
            self._attr_state_class = None  # Explicitly set None for text sensors

        # Get the unit and device class from SENSOR_TYPES
        sensor_type = sensor[1]
        if sensor_type in SENSOR_TYPES:
            self._attr_native_unit_of_measurement = SENSOR_TYPES[sensor_type][0]
            if SENSOR_TYPES[sensor_type][1]:
                self._attr_device_class = SENSOR_TYPES[sensor_type][1]
                _LOGGER.debug(
                    "Setting device class for sensor %s to %s",
                    self._attr_name,
                    self._attr_device_class
                )

        # Set any additional attributes
        if len(sensor) > 2 and isinstance(sensor[2], dict):
            for key, value in sensor[2].items():
                if key != "device_class":
                    setattr(self, f"_attr_{key}", value)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._resort_id)},
            "name": self._resort_name,
            "manufacturer": "Fnugg",
            "model": "Ski Resort",
        }
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._sensor_id in self._fnugg_data.sensors:
            return self._fnugg_data.sensors[self._sensor_id][0]
        return None

    @property
    def device_class(self):
        """Return the device class."""
        return self._attr_device_class

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "timestamp": datetime.datetime.fromisoformat(
                self._fnugg_data.sensors[self._sensor_id][2].get("latestSample", "")
            )
        }

    async def async_update(self):
        """Get the latest data."""
        await self._fnugg_data.update()
        self._sensor = self._fnugg_data.sensors.get(self._sensor_id)


class FnuggData:
    def __init__(self, session, resort_id, resort_name):
        """Initialize the data object."""
        self._session = session
        self._resort_id = resort_id
        self._resort_name = resort_name
        self.sensors = {}
        self._timeout = 10
        self._updated_at = datetime.datetime.now()

    async def update(self, _=None, force_update=False):
        now = datetime.datetime.now()
        elapsed = now - self._updated_at
        if elapsed < datetime.timedelta(minutes=20) and not force_update:
            return
        self._updated_at = now
        await self.update_data()

    async def update_data(self):
        """Update data from Fnugg API."""
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    f"https://api.fnugg.no/get/resort/{self._resort_id}/",
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
            source = result.get("_source", {})
            conditions = source.get("conditions", {}).get("combined", {}).get("top", {})
            
            # Get lift data
            lifts = source.get("lifts", {})
            lifts_total = int(lifts.get("count", 0))
            lifts_open = int(lifts.get("open", 0))
            lifts_percentage = round((lifts_open / lifts_total * 100) if lifts_total > 0 else 0)
            
            # Get slope data
            slopes = source.get("slopes", {})
            slopes_total = int(slopes.get("count", 0))
            slopes_open = int(slopes.get("open", 0))
            slopes_percentage = round((slopes_open / slopes_total * 100) if slopes_total > 0 else 0)

            contact_info = source.get("contact", "")

            _LOGGER.debug("Resort opening date: %s", source.get("resort_opening_date"))

            resort_opening_date = source.get("resort_opening_date", "")
            resort_closing_date = source.get("resort_closing_date", "")
            last_updated = source.get("last_updated", "")

            opening_hours = source.get("opening_hours", "")
            resort_open = source.get("resort_open", "")

            
            self.sensors = {
                # Weather Conditions
                "temp": (
                    conditions.get("temperature", {}).get("value"),
                    "temp",
                    {"icon": "mdi:thermometer"}
                ),
                "wind_speed": (
                    conditions.get("wind", {}).get("mps"),
                    "wind_speed",
                    {"icon": "mdi:weather-windy"}
                ),
                "wind_direction": (
                    conditions.get("wind", {}).get("degree"),
                    "wind_direction",
                    {"icon": "mdi:compass"}
                ),
                "condition_text": (
                    conditions.get("condition_description"),
                    "condition_text",
                    {"icon": "mdi:weather-snowy"}
                ),
                
                # Snow Info
                "snow_depth": (
                    conditions.get("snow", {}).get("depth"),
                    "snow_depth",
                    {"icon": "mdi:ruler"}
                ),
                "new_snow": (
                    conditions.get("snow", {}).get("newsnow"),
                    "new_snow",
                    {"icon": "mdi:snowflake"}
                ),
                
                # Lift Status
                "lifts_total": (
                    lifts_total,
                    "lifts_total",
                    {"icon": "mdi:ski"}
                ),
                "lifts_open": (
                    lifts_open,
                    "lifts_open",
                    {"icon": "mdi:ski"}
                ),
                "lifts_percentage": (
                    lifts_percentage,
                    "lifts_percentage",
                    {"icon": "mdi:ski"}
                ),
                "lifts_status_text": (
                    f"{lifts_open} of {lifts_total} lifts open ({lifts_percentage}%)",
                    "text",
                    {"icon": "mdi:ski"}
                ),
                
                # Slope Status
                "slopes_total": (
                    slopes_total,
                    "slopes_total",
                    {"icon": "mdi:ski"}
                ),
                "slopes_open": (
                    slopes_open,
                    "slopes_open",
                    {"icon": "mdi:ski"}
                ),
                "slopes_percentage": (
                    slopes_percentage,
                    "slopes_percentage",
                    {"icon": "mdi:ski"}
                ),
                "slopes_status_text": (
                    f"{slopes_open} of {slopes_total} slopes open ({slopes_percentage}%)",
                    "slopes_status_text",
                    {"icon": "mdi:ski"}
                ),
                "resort_opening_date": (
                    resort_opening_date,
                    "date",
                    {
                        "icon": "mdi:calendar-month",
                        "device_class": SensorDeviceClass.TIMESTAMP
                    }
                ),
                "resort_closing_date": (
                    resort_closing_date,
                    "date",
                    {
                        "icon": "mdi:calendar-month",
                        "device_class": SensorDeviceClass.TIMESTAMP
                    }
                ),
                "last_updated": (
                    last_updated,
                    "date",
                    {
                        "icon": "mdi:clock",
                        "device_class": SensorDeviceClass.TIMESTAMP
                    }
                ),

                "opening_hours": (
                    "%s - %s" % (opening_hours[datetime.datetime.now().strftime("%A").lower()]["from"], 
                                opening_hours[datetime.datetime.now().strftime("%A").lower()]["to"]),
                    "hours",
                    {
                        "icon": "mdi:information",
                        "extra_state_attributes": opening_hours,
                    }       
                ),
                "resort_open": (
                    resort_open,
                    "boolean",
                    {
                        "icon": "mdi:information",
                    }
                ),
            }



            # Add individual lift statuses
            lifts_detail = source.get("lifts", {}).get("list", [])
            for lift in lifts_detail:
                lift_name = lift.get("name", "").strip()
                if lift_name:
                    # Create a safe sensor ID from the lift name
                    lift_id = f"lift_{lift_name.lower().replace(' ', '_')}"
                    
                    # Get status
                    status_value = lift.get("status")
                    status = LIFT_STATUS.get(int(status_value), "Unknown")
                    
                    # Get additional info
                    slope_difficulty = lift.get("slope_difficulty")
                    
                    # Create attribute dictionary
                    attributes = {
                        "icon": "mdi:ski",
                    }
                    
                    if slope_difficulty:
                        attributes["slope_difficulty"] = slope_difficulty
                    
                    # Add to sensors dictionary
                    self.sensors[lift_id] = (
                        status,
                        "lift_status",
                        attributes
                    )

            return True
            
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Fnugg: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False

