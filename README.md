# Akubela HyPanel — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Control nativo de paneles **Akubela HyPanel** desde Home Assistant mediante WebSocket local — sin nube, sin intermediarios.

> Desarrollado por [@jaaneo](https://github.com/jaaneo) · [DMT Smart Home](https://dmtsmarthome.cl)

---

## ¿Cómo funciona?

El HyPanel expone internamente el **protocolo WebSocket nativo de Home Assistant** (`ha_version 4.0.1`). Esta integración aprovecha ese protocolo para conectarse directamente al panel vía LAN, suscribirse a cambios de estado en tiempo real y enviar comandos de control.

```
Home Assistant ←──WebSocket local──→ Akubela HyPanel
```

**Sin cloud. Sin latencia. Control en milisegundos.**

---

## Dispositivos compatibles

| Modelo | Testado |
|---|---|
| HyPanel KeyPlus (KS53) | ✅ |
| HyPanel Pro | ✅ (reportado) |
| HyPanel Plus | ⚠️ Sin confirmar |
| HyPanel Lux | ⚠️ Sin confirmar |
| HyPanel Supreme | ⚠️ Sin confirmar |

---

## Entidades soportadas

| Plataforma | Descripción |
|---|---|
| `light` | Luces Zigbee/KNX con brillo y temperatura de color |
| `cover` | Cortinas y stores con control de posición |
| `switch` | Relés del panel y módulos de conmutación |
| `scene` | Escenas de iluminación (Relax, Lectura, Descanso, etc.) |

---

## Requisitos previos

- Home Assistant 2024.1 o superior
- Akubela HyPanel en la misma red local que HA
- **Control de API habilitado** en el panel (ver configuración más abajo)
- Token de acceso del panel

---

## Configurar el HyPanel

### 1. Habilitar Control de API

1. Abre el portal web del HyPanel: `http://<IP_HYPANEL>`
2. Ve a **Configuración → Control de API**
3. Activa **Control de API** → selecciona **Modo servidor**
4. Activa **Lista blanca** → ingresa la IP de tu servidor HA
5. Haz clic en **Enviar**

### 2. Obtener el token de acceso

1. Abre el portal web del HyPanel en Chrome
2. Inicia sesión con tu cuenta de administrador
3. Abre DevTools (`F12`) → pestaña **Application** → **Local Storage** → `http://<IP>`
4. En la consola ejecuta:

```javascript
console.log(localStorage.getItem("AKUBELA_USER-TOKEN"));
```

> ⚠️ El token tiene el formato `new_project-xxxxxxxxxxxxxxxx...`

---

## Instalación

### Opción A — Manual

```bash
# Desde tu servidor HA
mkdir -p /config/custom_components/akubela
cd /config/custom_components/akubela

# Clonar solo la carpeta de la integración
git clone https://github.com/jaaneo/akubela-homeassistant.git /tmp/akubela_tmp
cp -r /tmp/akubela_tmp/custom_components/akubela/* .

# Reiniciar HA
docker restart homeassistant
```

### Opción B — HACS (próximamente)

1. HACS → Integraciones → ⋮ → Repositorios personalizados
2. URL: `https://github.com/jaaneo/akubela-homeassistant`
3. Categoría: **Integration**
4. Instalar → Reiniciar HA

---

## Configuración en Home Assistant

1. **Configuración → Integraciones → + Añadir integración**
2. Buscar **"Akubela HyPanel"**
3. Completar el formulario:

| Campo | Valor |
|---|---|
| Host | IP del HyPanel (ej: `192.168.1.172`) |
| Puerto | `80` |
| Token de acceso | El token obtenido en el paso anterior |

4. Haz clic en **Enviar**

Si la conexión es exitosa, todas las entidades del HyPanel aparecerán en HA automáticamente.

---

## Uso en automatizaciones

### Encender luz

```yaml
service: light.turn_on
target:
  entity_id: light.akubela_pasillo
data:
  brightness: 200
```

### Activar escena

```yaml
service: scene.turn_on
target:
  entity_id: scene.akubela_living_relax
```

### Abrir cortina al 50%

```yaml
service: cover.set_cover_position
target:
  entity_id: cover.akubela_shade
data:
  position: 50
```

### Encender relé del HyPanel

```yaml
service: switch.turn_on
target:
  entity_id: switch.akubela_hypanel_keyplus_relay
```

---

## Arquitectura técnica

```
custom_components/akubela/
├── __init__.py           # Setup + reconexión automática
├── manifest.json         # Metadata de la integración
├── const.py              # Constantes
├── config_flow.py        # UI de configuración (Config Flow)
├── websocket_client.py   # Cliente WebSocket con auth y push de estados
├── light.py              # Plataforma luces
├── cover.py              # Plataforma cortinas
├── switch.py             # Plataforma switches/relés
├── scene.py              # Plataforma escenas
└── strings.json          # Textos de la UI
```

### Flujo WebSocket

```
HA conecta → ws://hypanel/api/websocket
           ← {"type":"auth_required","ha_version":"4.0.1"}
→ {"type":"auth","access_token":"TOKEN"}
           ← {"type":"auth_ok"}
→ {"id":1,"type":"get_states"}
           ← [lista de todas las entidades]
→ {"id":2,"type":"subscribe_events","event_type":"state_changed"}
           ← push automático de cambios en tiempo real
→ {"id":N,"type":"call_service","domain":"light","service":"turn_on",...}
           ← {"success":true}
```

---

## Solución de problemas

### La integración no aparece en HA

- Verifica que los archivos estén en `/config/custom_components/akubela/`
- Revisa los logs: **Configuración → Registros → filtrar "akubela"**
- Reinicia HA completamente

### Error de conexión

- Verifica que el **Control de API** esté habilitado en **Modo servidor**
- Confirma que la IP de HA esté en la **Lista blanca** del HyPanel
- Prueba la conexión manualmente:

```bash
TOKEN="tu_token_aqui"
(sleep 1; echo '{"type":"auth","access_token":"'$TOKEN'"}'; sleep 1; echo '{"id":1,"type":"get_states"}'; sleep 2) \
  | websocat ws://192.168.1.172/api/websocket
```

### El token expiró

Los tokens del HyPanel pueden cambiar al reiniciar el panel. Repite el proceso de obtención del token y actualiza la integración en **Configuración → Integraciones → Akubela → Configurar**.

---

## Contribuir

Pull requests bienvenidos. Para cambios grandes, abre un issue primero.

```bash
git clone https://github.com/jaaneo/akubela-homeassistant.git
cd akubela-homeassistant
# Tus cambios aquí
git checkout -b feature/mi-mejora
git commit -m "feat: descripción del cambio"
git push origin feature/mi-mejora
```

---

## Licencia

MIT © [@jaaneo](https://github.com/jaaneo)

---

## Agradecimientos

- Descubrimiento del protocolo WebSocket nativo del HyPanel realizado mediante ingeniería inversa del frontend web del panel
- Implementado y probado en producción con **HyPanel KeyPlus (KS53)** por [DMT Smart Home SpA](https://dmtsmarthome.cl), Valdivia, Chile
