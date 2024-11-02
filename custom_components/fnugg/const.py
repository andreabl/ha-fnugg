"""Constants for the Fnugg integration."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.const import (
    DEGREE,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    PERCENTAGE,
)

DOMAIN = "fnugg"

# Define which sensors are numeric (will have state_class = measurement)
NUMERIC_SENSORS = [
    "temp", "wind_speed", "snow_depth", "new_snow",
    "lifts_open", "lifts_total", "slopes_open", "slopes_total",
    "lifts_percentage", "slopes_percentage"
]

# Add lift status enum
LIFT_STATUS = {
    0: "Closed",
    1: "Open",
    None: "Unknown"
}



SENSOR_TYPES = {
    # Basic Info (non-numeric)
    "resort_status": ["", None, False],
    "resort_opening_date": ["", None, False],
    "resort_closing_date": ["", None, False],
    
    # Weather Conditions (numeric)
    "temp": [UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, True],
    "wind_speed": [UnitOfSpeed.METERS_PER_SECOND, SensorDeviceClass.WIND_SPEED, True],
    "wind_direction": [DEGREE, None, True],
    "condition_description": ["", None, False],
    
    # Snow Info
    "snow_depth": [UnitOfLength.CENTIMETERS, None, True],
    "new_snow": [UnitOfLength.CENTIMETERS, None, True],
    
    # Lift Status
    "lifts_total": ["lifts", None, True],
    "lifts_open": ["lifts", None, True],
    "lifts_percentage": [PERCENTAGE, None, True],
    "lifts_status_text": ["", None, False],  # Text status of lifts
    
    # Slope Status
    "slopes_total": ["slopes", None, True],
    "slopes_open": ["slopes", None, True],
    "slopes_percentage": [PERCENTAGE, None, True],
    "slopes_status": ["", None, False],  # Text status of slopes
    

    # Facility Status
    "facility_status": ["", None, False],

} 