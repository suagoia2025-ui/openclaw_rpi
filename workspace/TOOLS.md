# TOOLS.md - Notas locales

Las skills definen _cómo_ funcionan las herramientas. Este archivo es para _tus_ detalles — lo que es propio de tu entorno.

## Qué va aquí

Cosas como:

- Nombres y ubicación de cámaras
- Hosts SSH y alias
- Voces preferidas para TTS
- Nombres de altavoces/habitaciones
- Apodos de dispositivos
- Cualquier cosa específica del entorno

## Cámara Pi (CSI – Camera Module 3)

La Raspberry Pi tiene una cámara CSI conectada (sensor **imx708**, Camera Module 3). OpenClaw puede no reportarla como "detected" por libcamera, pero la cámara funciona. Usar **rpicam-still** para capturar fotos.

**Regla:** Siempre rotar la foto al capturar porque la cámara está montada de lado. Usar **`--rotation 270`** (equivale a 90° en sentido antihorario) para que la imagen quede en orientación correcta (no vertical/portrait incorrecto).

**Capturar una foto (con rotación correcta):**

```bash
rpicam-still -o /tmp/capture.jpg --rotation 270
```

- **Siempre** incluir `--rotation 270` para que la imagen quede en la orientación correcta.
- Si la imagen sigue saliendo mal, probar con `--rotation 90` (sentido horario).
- Salida por defecto: `/tmp/capture.jpg`. Puedes cambiar la ruta.
- Para resoluciones concretas: `rpicam-still -o foto.jpg --width 1920 --height 1080 --rotation 270`
- La cámara está en el host de la Pi; ejecutar estos comandos en la Raspberry Pi (donde corre el gateway).

Cuando el usuario pida "toma una foto" o "captura una imagen", usar `rpicam-still -o <ruta>.jpg --rotation 270` y luego enviar o analizar esa imagen según el flujo (p. ej. visión del modelo).

---

## Google Workspace — `gog` (Gmail y Calendar)

En el **host del gateway (Raspberry Pi)** está instalado el CLI **[gog](https://gogcli.sh/)** (skill OpenClaw `gog`). Sirve para Gmail, Calendar y otros productos Google vía OAuth. Ejecutar comandos en el gateway con la herramienta de shell/`exec`, no pedir “tokens de OpenClaw” aparte.

**Entorno (ya configurado en el servidor):** `GOG_ACCOUNT`, y para el servicio sin TTY: `GOG_KEYRING_BACKEND=file` y `GOG_KEYRING_PASSWORD` en `~/.openclaw/.env` (no volcar esos valores en el chat). Documentación de keyring: [gogcli README](https://github.com/steipete/gogcli/blob/main/README.md).

**Ayuda integrada (siempre disponible en la Pi):**

```bash
gog --help
gog auth --help
gog auth status
gog gmail --help
gog calendar --help
gog calendar create --help
gog calendar events --help
gog calendar calendars --help
gog calendar colors
```

### Gmail — notas útiles

- Listar ayuda del subcomando que vayas a usar: `gog gmail <subcomando> --help`.
- Búsqueda por hilos: `gog gmail search 'consulta' --max N` (sintaxis tipo Gmail).
- Cuenta por defecto: `GOG_ACCOUNT` o flag `-a` / `--account=`.
- Scripting: añade `--json` cuando haga falta parsear salida.
- **Confirmar antes** de enviar correo (`gog gmail send`, borradores, etc.); es acción sensible.

### Calendar — notas útiles

- **“Mis calendarios”** en la web de Google **no es** un `calendarId` en la API: es una agrupación de la UI. Los calendarios tienen **`id`** (el principal suele ser el correo del usuario) y **`summary`** (nombre visible).
- Listar calendarios e ids: `gog calendar calendars --max 50` o con `--json`.
- **Crear evento:** el **primer argumento** es `<calendarId>` (no un flag `--cal`):

  ```bash
  gog calendar create "CALENDAR_ID" \
    --summary="Título" \
    --from="2026-04-10T15:00:00-05:00" \
    --to="2026-04-10T16:00:00-05:00"
  ```

  Zona horaria ejemplo: `-05:00` (Colombia). Evento de día completo: `--all-day` con fechas solo fecha en `--from` / `--to`.
- Probar sin escribir: `gog calendar create ... --dry-run`.
- Colores de evento: `gog calendar colors` y `--event-color=ID` (1–11).
- **Confirmar antes** de crear, borrar o modificar eventos si el usuario no lo ha pedido explícitamente.

### Flujo recomendado para el agente

1. Si no conoces el `calendarId`: `gog calendar calendars --json` y elegir por `id` / `summary`.
2. Para dudas de flags: `gog calendar <comando> --help` o `gog gmail <comando> --help`.
3. Si falla un comando, mostrar stderr/salida del terminal al usuario (sin secretos).

---

## Ejemplos

```markdown
### Cámaras

- pi-csi → Cámara integrada en la Pi (Camera Module 3, imx708). Captura con rotación correcta: rpicam-still -o /tmp/capture.jpg --rotation 270
- living-room → Zona principal, 180° gran angular
- front-door → Entrada, activada por movimiento

### SSH

- home-server → 192.168.1.100, usuario: admin

### TTS

- Voz preferida: "Nova" (cálida, un poco británica)
- Altavoz por defecto: HomePod cocina
```

## ¿Por qué separado?

Las skills se comparten. Tu configuración es tuya. Mantenerlas separadas permite actualizar skills sin perder tus notas, y compartir skills sin filtrar tu infraestructura.

---

Añade lo que te ayude a hacer tu trabajo. Es tu chuleta.
