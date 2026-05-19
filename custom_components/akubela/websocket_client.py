"""WebSocket client para Akubela HyPanel.

El HyPanel expone el protocolo WebSocket de Home Assistant (ha_version 4.0.1),
lo que permite control total de entidades via call_service y suscripción
a cambios de estado en tiempo real.
"""

import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AkubelaWebSocketClient:
    """Cliente WebSocket para comunicarse con el HyPanel de Akubela."""

    def __init__(self, host: str, port: int, token: str):
        self.host = host
        self.port = port
        self.token = token

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._listen_task: Optional[asyncio.Task] = None

        self._msg_id = 1
        self._pending: Dict[int, asyncio.Future] = {}
        self._state_callbacks: List[Callable] = []
        self._states: Dict[str, dict] = {}
        self._connected = False
        self._auth_ok = asyncio.Event()

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Conectar al WebSocket del HyPanel y autenticar."""

        # BUG FIX #1: Limpiar el evento auth_ok en cada reconexión.
        # Sin esto, en el segundo intento wait() retorna inmediatamente
        # porque el evento ya estaba seteado del intento anterior.
        self._auth_ok.clear()

        # BUG FIX #2: Cerrar sesión anterior antes de crear una nueva.
        # Sin esto cada reconexión filtra una aiohttp.ClientSession.
        if self._session and not self._session.closed:
            await self._session.close()

        url = f"ws://{self.host}:{self.port}/api/websocket"
        self._session = aiohttp.ClientSession()

        try:
            self._ws = await self._session.ws_connect(url, heartbeat=30)
        except Exception as exc:
            _LOGGER.error("No se pudo conectar a Akubela en %s: %s", url, exc)
            await self._session.close()
            return False

        # BUG FIX #3: Cancelar y esperar el task anterior antes de crear uno nuevo.
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        self._listen_task = asyncio.ensure_future(self._listen())

        # Esperar auth_ok (máx 10 seg)
        try:
            await asyncio.wait_for(self._auth_ok.wait(), timeout=10)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout esperando autenticación con Akubela HyPanel")
            return False

        # auth_invalid seteó el evento pero _connected sigue False
        if not self._connected:
            _LOGGER.error("Autenticación rechazada por Akubela HyPanel — token inválido")
            return False

        # Obtener estados iniciales
        await self._load_initial_states()

        # Suscribir a cambios de estado en tiempo real
        await self._subscribe_events()

        _LOGGER.info(
            "Akubela HyPanel conectado — %d entidades encontradas",
            len(self._states),
        )
        return True

    async def disconnect(self):
        """Cerrar la conexión WebSocket limpiamente."""
        self._connected = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                # BUG FIX #4: Esperar que el task termine después de cancelarlo.
                # Sin esto pueden quedar tareas zombie en el event loop.
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        # Limpiar futuros pendientes para no dejarlos bloqueados
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    # ------------------------------------------------------------------
    # Loop de escucha
    # ------------------------------------------------------------------

    async def _listen(self):
        """Procesar mensajes entrantes del WebSocket."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(data)
                    except json.JSONDecodeError:
                        _LOGGER.warning("Mensaje no JSON recibido: %s", msg.data[:200])
                elif msg.type in (
                    aiohttp.WSMsgType.ERROR,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    _LOGGER.warning("WebSocket Akubela cerrado: %s", msg.type)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            _LOGGER.error("Error en loop WebSocket Akubela: %s", exc)
        finally:
            self._connected = False

    async def _handle_message(self, data: dict):
        """Despachar mensajes por tipo."""
        msg_type = data.get("type")

        if msg_type == "auth_required":
            await self._send_raw({"type": "auth", "access_token": self.token})

        elif msg_type == "auth_ok":
            self._connected = True
            self._auth_ok.set()
            _LOGGER.debug("Auth OK con Akubela HyPanel v%s", data.get("ha_version"))

        elif msg_type == "auth_invalid":
            # _connected queda False — connect() lo detecta después del wait()
            _LOGGER.error("Token inválido para Akubela HyPanel")
            self._auth_ok.set()

        elif msg_type == "result":
            msg_id = data.get("id")
            fut = self._pending.pop(msg_id, None)
            if fut and not fut.done():
                if data.get("success"):
                    fut.set_result(data.get("result"))
                else:
                    fut.set_exception(
                        Exception(data.get("error", {}).get("message", "unknown error"))
                    )

        elif msg_type == "event":
            await self._handle_event(data.get("event", {}))

    async def _handle_event(self, event: dict):
        """Procesar eventos de cambio de estado."""
        if event.get("event_type") != "state_changed":
            return

        new_state = event.get("data", {}).get("new_state")
        if not new_state:
            return

        entity_id = new_state["entity_id"]
        self._states[entity_id] = new_state

        for cb in list(self._state_callbacks):  # copia para evitar mutación durante iteración
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(entity_id, new_state)
                else:
                    cb(entity_id, new_state)
            except Exception as exc:
                _LOGGER.error("Error en callback de estado %s: %s", entity_id, exc)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict,
    ) -> Optional[dict]:
        """Llamar a un servicio en el HyPanel (light.turn_on, cover.open_cover, etc.)."""
        if not self._connected:
            _LOGGER.warning("call_service ignorado — Akubela no conectado")
            return None

        msg_id = self._next_id()
        # BUG FIX #5: usar get_running_loop() en vez del deprecado get_event_loop()
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut

        await self._send_raw(
            {
                "id": msg_id,
                "type": "call_service",
                "domain": domain,
                "service": service,
                "service_data": service_data,
            }
        )

        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=10)
        except asyncio.TimeoutError:
            # BUG FIX #6: limpiar el future pendiente en timeout para no filtrarlo
            self._pending.pop(msg_id, None)
            if not fut.done():
                fut.cancel()
            _LOGGER.warning("Timeout llamando %s.%s en Akubela", domain, service)
            return None

    async def get_states(self) -> list:
        """Obtener todos los estados actuales del HyPanel."""
        msg_id = self._next_id()
        # BUG FIX #5: get_running_loop() en vez de get_event_loop()
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut
        await self._send_raw({"id": msg_id, "type": "get_states"})
        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=15)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            _LOGGER.error("Timeout obteniendo estados de Akubela")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _load_initial_states(self):
        states = await self.get_states()
        for state in states:
            self._states[state["entity_id"]] = state

    async def _subscribe_events(self):
        msg_id = self._next_id()
        await self._send_raw(
            {"id": msg_id, "type": "subscribe_events", "event_type": "state_changed"}
        )

    async def _send_raw(self, data: dict):
        if self._ws and not self._ws.closed:
            await self._ws.send_str(json.dumps(data))
        else:
            _LOGGER.warning("Intento de envío con WebSocket cerrado ignorado")

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def register_state_callback(self, callback: Callable):
        """Registrar callback que se llama cuando cambia el estado de una entidad."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def unregister_state_callback(self, callback: Callable):
        # BUG FIX #7: la versión anterior tenía código muerto con .discard()
        # List no tiene .discard() — lógica simplificada y correcta
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    @property
    def cached_states(self) -> Dict[str, dict]:
        return self._states

    @property
    def is_connected(self) -> bool:
        return self._connected
