# Changelog

All notable changes to the Akubela HyPanel integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-05-19

### Added
- `binary_sensor` platform — sensor de movimiento PIR integrado del HyPanel y sensores Zigbee externos
- `sensor` platform — temperatura, humedad, luminosidad (lx), potencia (W) y energía (kWh) del panel y relés
- `media_player` platform — control de Sonos integrado vía HyPanel (play, pause, stop, volumen, siguiente/anterior)

### Changed
- `const.py` — agregadas plataformas `binary_sensor`, `sensor`, `media_player` a la lista `PLATFORMS`
- `manifest.json` — versión actualizada a 1.2.0

### Fixed
- `sensor.py` — reemplazado `UnitOfIlluminance` (no disponible en `homeassistant.const`) por literal `"lx"`

---

## [1.1.0] - 2026-05-19

### Fixed
- `websocket_client.py` — `asyncio.Event` no se reseteaba entre reconexiones, causando auth silenciosa fallida
- `websocket_client.py` — `aiohttp.ClientSession` anterior no se cerraba antes de crear una nueva (memory leak)
- `websocket_client.py` — listen task anterior no se cancelaba ni esperaba antes de crear uno nuevo (zombie tasks)
- `websocket_client.py` — `disconnect()` no esperaba el task cancelado (cleanup incompleto)
- `websocket_client.py` — reemplazado `asyncio.get_event_loop()` deprecado por `asyncio.get_running_loop()`
- `websocket_client.py` — future no se eliminaba de `_pending` al timeout (memory leak acumulativo)
- `websocket_client.py` — `unregister_state_callback()` tenía código muerto con `.discard()` en una lista
- `__init__.py` — reemplazado `hass.loop.create_task()` deprecado por `hass.async_create_background_task()`
- `__init__.py` — tarea de reconexión no tenía referencia guardada, imposibilitando cancelarla al descargar
- `light.py`, `cover.py`, `switch.py` — removido decorador `@callback` incompatible con métodos `async def`
- `light.py` — reemplazado `ATTR_COLOR_TEMP` removido en HA 2024+ por `ATTR_COLOR_TEMP_KELVIN`

### Changed
- `manifest.json` — versión actualizada a 1.1.0
- `manifest.json` — actualizado `codeowners` a `@jaaneo`
- `manifest.json` — agregado `issue_tracker` apuntando al repositorio GitHub

---

## [1.0.0] - 2026-05-19

### Added
- Conexión WebSocket local al HyPanel (protocolo nativo HA `ha_version 4.0.1`)
- Autenticación via token de acceso (`AKUBELA_USER-TOKEN` del Local Storage del portal web)
- Suscripción a cambios de estado en tiempo real (`state_changed` events)
- Reconexión automática al perder la conexión WebSocket
- `light` platform — luces Zigbee/KNX con control de brillo y temperatura de color
- `cover` platform — cortinas y stores con control de posición (0–100%)
- `switch` platform — relés del HyPanel y módulos de conmutación
- `scene` platform — escenas de iluminación (Relax, Lectura, Descanso, Pandemonium, etc.)
- Config Flow — configuración vía UI de HA (sin editar YAML)
- Validación de conexión durante el setup
- Logo oficial de Akubela en `images/logo.png`

### Technical
- Descubrimiento del protocolo WebSocket mediante ingeniería inversa del frontend web del HyPanel
- Probado en producción con **HyPanel KeyPlus (KS53)** firmware `ha_version 4.0.1`
- Dispositivo: Akubela HyPanel KeyPlus · MAC `04:A1:6F:42:23:0B`

---

## Roadmap

- [ ] Soporte para `camera` (proxying de cámaras del HyPanel)
- [ ] Control de volumen del panel via ADB (Android Debug Bridge)
- [ ] Renovación automática del token de acceso
- [ ] Registro en HA Brands repository para logo oficial en la UI
- [ ] Soporte HACS oficial
