"""Plataforma de cortinas/stores Akubela HyPanel."""

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
        AkubelaCover(client, entity_id, state)
        for entity_id, state in client.cached_states.items()
        if entity_id.startswith("cover.")
    ]

    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("Akubela: %d cortinas registradas", len(entities))


class AkubelaCover(CoverEntity):
    """Entidad de cortina/store del HyPanel de Akubela."""

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

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
        self._attr_device_class = CoverDeviceClass.SHADE
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "hypanel")},
            "name": "Akubela HyPanel",
            "manufacturer": "Akubela",
            "model": "HyPanel KeyPlus",
        }

        self._apply_state(state)
        client.register_state_callback(self._on_state_change)

    def _apply_state(self, state: dict) -> None:
        attrs = state.get("attributes", {})
        raw = state.get("state", "closed")
        self._is_closed = raw == "closed"
        self._position: int | None = attrs.get("current_position")

    @callback
    async def _on_state_change(self, entity_id: str, new_state: dict) -> None:
        if entity_id == self._akubela_id:
            self._apply_state(new_state)
            self.async_write_ha_state()

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    @property
    def current_cover_position(self) -> int | None:
        return self._position

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "cover", "open_cover", {"entity_id": self._akubela_id}
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "cover", "close_cover", {"entity_id": self._akubela_id}
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "cover", "stop_cover", {"entity_id": self._akubela_id}
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION, 50)
        await self._client.call_service(
            "cover",
            "set_cover_position",
            {"entity_id": self._akubela_id, "position": position},
        )
