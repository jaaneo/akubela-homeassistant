"""Plataforma de escenas Akubela HyPanel (Relax, Lectura, Descanso, etc.)."""

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .websocket_client import AkubelaWebSocketClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: AkubelaWebSocketClient = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AkubelaScene(client, entity_id, state)
        for entity_id, state in client.cached_states.items()
        if entity_id.startswith("scene.")
    ]

    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("Akubela: %d escenas registradas", len(entities))


class AkubelaScene(Scene):
    """Escena del HyPanel de Akubela (iluminación por ambiente)."""

    _attr_has_entity_name = False

    def __init__(
        self,
        client: AkubelaWebSocketClient,
        entity_id: str,
        state: dict,
    ) -> None:
        self._client = client
        self._akubela_id = entity_id
        attrs = state.get("attributes", {})

        self._attr_unique_id = f"akubela_{entity_id}"
        self._attr_name = f"Akubela {attrs.get('friendly_name', entity_id)}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "hypanel")},
            "name": "Akubela HyPanel",
            "manufacturer": "Akubela",
            "model": "HyPanel KeyPlus",
        }

    async def async_activate(self, **kwargs: Any) -> None:
        """Activar la escena en el HyPanel."""
        await self._client.call_service(
            "scene", "turn_on", {"entity_id": self._akubela_id}
        )
        _LOGGER.debug("Akubela escena activada: %s", self._akubela_id)
