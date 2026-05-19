"""Plataforma de switches Akubela HyPanel."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AkubelaSwitch(client, entity_id, state)
        for entity_id, state in client.cached_states.items()
        if entity_id.startswith("switch.")
    ]
    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("Akubela: %d switches registrados", len(entities))


class AkubelaSwitch(SwitchEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, client, entity_id, state):
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
        self._is_on = state.get("state") == "on"
        client.register_state_callback(self._on_state_change)

    async def _on_state_change(self, entity_id: str, new_state: dict) -> None:
        if entity_id == self._akubela_id:
            self._is_on = new_state.get("state") == "on"
            self.async_write_ha_state()

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "switch", "turn_on", {"entity_id": self._akubela_id}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "switch", "turn_off", {"entity_id": self._akubela_id}
        )
