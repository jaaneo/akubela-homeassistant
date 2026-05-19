"""Constants for Akubela HyPanel integration."""

DOMAIN = "akubela"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "access_token"

DEFAULT_PORT = 80

PLATFORMS = ["light", "cover", "switch", "scene"]

WS_RECONNECT_DELAY = 5  # segundos entre intentos de reconexión
