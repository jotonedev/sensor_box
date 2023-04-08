__all__ = ["WIFI_COUNTRY", "WIFI_SSID", "WIFI_BSID", "WIFI_PASS", "MQTT_NAME", "MQTT_HOST", "MQTT_PORT"]

# If you don't want to use the BSSID, just comment set it to None

WIFI_COUNTRY = "IT"  # Wi-Fi country
WIFI_SSID = ""  # Wi-Fi SSID
WIFI_BSID = b""  # Wi-Fi BSSID (optional, but recommended for security)
WIFI_PASS = ""  # Wi-Fi password
MQTT_NAME = "box01"  # MQTT client name
MQTT_HOST = ""  # MQTT server address
MQTT_PORT = 1883  # MQTT server port
