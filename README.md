# Home Assistant Fnugg Integration

This custom integration allows you to add Fnugg Ski Resort data  (https://fnugg.no/) into your Home Assistant setup. This code is experimental, but it Works for me(tm). 

## Installation via HACS

To install this integration using Home Assistant Community Store (HACS), follow these steps:

1. **Open Home Assistant:**
   - Ensure that you have Home Assistant up and running.

2. **Install HACS:**
   - If you haven't already, install HACS by following the official [HACS installation guide](https://hacs.xyz/docs/setup/download).

3. **Add Custom Repository:**
   - Go to HACS in your Home Assistant interface.
   - Click on the three dots in the top right corner and select "Custom repositories".

4. **Enter Repository URL:**
   - In the "Repository" field, enter the following URL: `https://github.com/andreabl/ha-fnugg`
   - In the "Category" field, select `Integration`.

5. **Install Integration:**
   - Find the "Fnugg" integration in HACS and click "Install".
   - After installation, restart Home Assistant.

6. **Configure Integration:**
   - Go to Configuration -> Integrations.
   - Click on "Add Integration" and search for "Fnugg".
   - Follow the on-screen instructions to configure the integration.

## Usage

After installation and configuration, you can use the Fnugg integration to access Ski resort information from Fnugg in your Home Assistant setup, such as weather information, ski lifts availability and resort opening times. 

## Support

For issues or support, please open an issue on the [GitHub repository](https://github.com/andreabl/ha-fnugg/issues).
