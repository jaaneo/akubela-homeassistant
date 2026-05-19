"""Plataforma de luces Akubela HyPanel."""

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
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
        AkubelaLight(client, entity_id, state)
        for entity_id, state in client.cached_states.items()
        if entity_id.startswith("light.")
    ]
    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("Akubela: %d luces registradas", len(entities))


class AkubelaLight(LightEntity):
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
        self._apply_state(state)
        # BUG FIX: NO usar @callback en métodos async.
        # register_state_callback acepta coroutines correctamente.
        client.register_state_callback(self._on_state_change)

    def _apply_state(self, state):
        attrs = state.get("attributes", {})
        self._is_on = state.get("state") == "on"
        self._brightness = attrs.get("brightness")
        modes = attrs.get("supported_color_modes", [])
        if "color_temp" in modes or "xy" in modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_min_color_temp_kelvin = 2000
            self._attr_max_color_temp_kelvin = 6500
        else:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    async def _on_state_change(self, entity_id: str, new_state: dict) -> None:
        """Callback async — sin @callback decorator (son incompatibles)."""
        if entity_id == self._akubela_id:
            self._apply_state(new_state)
            self.async_write_ha_state()

    @property
    def is_on(self):
        return self._is_on

    @property
    def brightness(self):
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        data: dict[str, Any] = {"entity_id": self._akubela_id}
        if ATTR_BRIGHTNESS in kwargs:
            data["brightness"] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            data["color_temp"] = round(1000000 / kwargs[ATTR_COLOR_TEMP_KELVIN])
        await self._client.call_service("light", "turn_on", data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.call_service(
            "light", "turn_off", {"entity_id": self._akubela_id}
        )
