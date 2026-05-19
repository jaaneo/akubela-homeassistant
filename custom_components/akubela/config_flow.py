"""Config Flow para Akubela HyPanel — UI de configuración en HA."""

import asyncio
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DEFAULT_PORT, DOMAIN
from .websocket_client import AkubelaWebSocketClient

_LOGGER = logging.getLogger(__name__)


class AkubelaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow para configurar la integración Akubela HyPanel."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Validar conexión antes de guardar
            client = AkubelaWebSocketClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                token=user_input[CONF_TOKEN],
            )
            try:
                connected = await asyncio.wait_for(client.connect(), timeout=10)
                await client.disconnect()

                if not connected:
                    errors["base"] = "cannot_connect"
                else:
                    # Evitar duplicados
                    await self.async_set_unique_id(
                        f"akubela_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Akubela HyPanel ({user_input[CONF_HOST]})",
                        data=user_input,
                    )
            except asyncio.TimeoutError:
                errors["base"] = "timeout"
            except Exception as exc:
                _LOGGER.error("Error al conectar con Akubela: %s", exc)
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.1.172"): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "url": "http://192.168.1.172 → DevTools → Local Storage → AKUBELA_USER-TOKEN"
            },
        )
