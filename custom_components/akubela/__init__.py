"""Integración Akubela HyPanel para Home Assistant."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN, PLATFORMS, WS_RECONNECT_DELAY
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

    # BUG FIX #8: usar hass.async_create_background_task() en vez del
    # deprecado hass.loop.create_task(), y guardar referencia al task
    # para poder cancelarlo en async_unload_entry.
    async def _reconnect_loop():
        while True:
            await asyncio.sleep(WS_RECONNECT_DELAY)
            if not client.is_connected:
                _LOGGER.warning("Akubela HyPanel desconectado — reconectando...")
                try:
                    await client.connect()
                except Exception as exc:
                    _LOGGER.error("Error al reconectar con Akubela: %s", exc)

    reconnect_task = hass.async_create_background_task(
        _reconnect_loop(), name="akubela_reconnect"
    )
    # Guardar el task junto al cliente para cancelarlo al descargar
    hass.data[DOMAIN][f"{entry.entry_id}_reconnect"] = reconnect_task

    _LOGGER.info("Akubela HyPanel integrado correctamente en Home Assistant")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar la integración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Cancelar el loop de reconexión
        reconnect_task: asyncio.Task = hass.data[DOMAIN].pop(
            f"{entry.entry_id}_reconnect", None
        )
        if reconnect_task and not reconnect_task.done():
            reconnect_task.cancel()

        client: AkubelaWebSocketClient = hass.data[DOMAIN].pop(entry.entry_id)
        await client.disconnect()

    return unload_ok
