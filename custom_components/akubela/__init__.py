"""Integración Akubela HyPanel para Home Assistant.

Conecta HA al HyPanel via WebSocket (protocolo nativo HA 4.0.1),
exponiendo luces, cortinas, switches y escenas como entidades locales.

DMT Smart Home SpA — dmtsmarthome.cl
"""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN, PLATFORMS
from .websocket_client import AkubelaWebSocketClient

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inicializar la integración desde una config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = AkubelaWebSocketClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        token=entry.data[CONF_TOKEN],
    )

    connected = await client.connect()
    if not connected:
        raise ConfigEntryNotReady(
            f"No se pudo conectar al HyPanel en {entry.data[CONF_HOST]}"
        )

    hass.data[DOMAIN][entry.entry_id] = client

    # Cargar plataformas (light, cover, switch, scene)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reconexión automática si se pierde el WebSocket
    async def _reconnect_loop():
        from .const import WS_RECONNECT_DELAY
        while True:
            await asyncio.sleep(WS_RECONNECT_DELAY)
            if not client.is_connected:
                _LOGGER.warning("Akubela HyPanel desconectado — reconectando...")
                await client.connect()

    hass.loop.create_task(_reconnect_loop())

    _LOGGER.info("Akubela HyPanel integrado correctamente en Home Assistant")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar la integración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: AkubelaWebSocketClient = hass.data[DOMAIN].pop(entry.entry_id)
        await client.disconnect()
    return unload_ok
