# Setup del sistema e instalación de OpenClaw (después del OS)

Ejecuta estos pasos **ya conectado por SSH** a tu Raspberry Pi 4.

## Conectarse por SSH a la Pi

Desde tu Mac (en Terminal):

```bash
ssh serv_openclaw@hostopclaw.local
```

Si el hostname no resuelve, usa la IP de la Pi (ej. 192.168.1.16):

```bash
ssh serv_openclaw@192.168.1.16
```

Te pedirá la contraseña del usuario `serv_openclaw`. La primera vez puede preguntar si confías en el host: escribe `yes`.

---

## 1. Actualizar sistema e instalar paquetes básicos

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl build-essential
```

## 2. Zona horaria (Bogotá, Colombia)

```bash
sudo timedatectl set-timezone America/Bogota
```

## 3. Instalar Node.js 22 (ARM64)

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

Comprobar:

```bash
node --version   # Debe ser v22.x.x
npm --version
```

## 4. Instalar OpenClaw

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

## 5. Onboarding (configuración guiada)

```bash
openclaw onboard --install-daemon
```

Durante el asistente:

- **Daemon:** Sí (systemd).
- **Canales:** Telegram es el más sencillo para empezar.
- **Auth:** API keys recomendado.
- **Modo del Gateway:** Local.

## 6. Comprobar que todo está bien

```bash
openclaw status
systemctl --user status openclaw-gateway
```

Ver logs en tiempo real:

```bash
journalctl --user -u openclaw-gateway -f
```

## 7. Acceder al Dashboard (desde tu Mac)

En tu Mac, abre otra terminal y crea un túnel SSH:

```bash
ssh -L 18790:localhost:18789 serv_openclaw@hostopclaw.local
```

Luego en el navegador (usa el puerto local del túnel, ej. 18790):

```
http://localhost:18790
```

Si el hostname no resuelve: `ssh -L 18790:localhost:18789 serv_openclaw@192.168.1.16`

---

## Estado instalado y probado (referencia)

Resumen de lo que quedó **operativo** en esta Raspberry Pi con OpenClaw (usuario `serv_openclaw`, gateway con systemd). Los detalles de comandos del agente y `gog` están en el workspace: `~/.openclaw/workspace/TOOLS.md` y `AGENTS.md` (o copia local en `openclaw_rpi/workspace/`).

| Área | Qué hay | Notas |
|------|---------|--------|
| **Cámara** | Pi Camera Module 3 (CSI, imx708) | Captura con `rpicam-still` y rotación (ver `TOOLS.md`). Salida típica: `/tmp/capture.jpg`. |
| **Audio entrada** | ReSpeaker 2-Mics Pi HAT v2 | ALSA `card 3` (`seeed2micvoicec`); reproducción `plughw:3,0`. Voz hacia el bot por **Telegram** usa el micrófono del dispositivo donde está la app; grabación local en la Pi con `arecord` si hace falta. |
| **Canal** | **Telegram** | Bot configurado en `openclaw.json`; agente usable desde el chat. |
| **Gmail** | CLI **gog** + OAuth (Google Cloud) | Tokens y llavero en `~/.config/gogcli/`. Para el **daemon** sin prompts: keyring `file` y variables en `~/.openclaw/.env` (`GOG_ACCOUNT`, `GOG_KEYRING_*`). **No** guardar secretos en el repo. |
| **Google Calendar** | Mismo **gog** | Calendarios por `calendarId` (el principal suele ser el correo; “Mis calendarios” es solo etiqueta de la UI). Crear: `gog calendar create <calendarId> --summary=... --from=... --to=...`. Chuleta en `TOOLS.md`. |
| **Web** | Brave Search API | `web_search` en el gateway; config en `openclaw.json` (`tools.web.search`). |

**Comprobaciones rápidas en la Pi**

```bash
systemctl --user status openclaw-gateway
openclaw status
```

**Próximo paso opcional (no instalado aún):** correo entrante → agente al vuelo vía **Gmail Pub/Sub + hooks** ([documentación OpenClaw](https://docs.openclaw.ai/automation/gmail-pubsub)); el uso actual es **bajo demanda** con `gog` desde el agente.

---

## Opcional: swap (solo si quieres más margen con 4 GB)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Opcional: reducir uso de RAM (headless)

```bash
echo 'gpu_mem=16' | sudo tee -a /boot/config.txt
sudo systemctl disable bluetooth
```

*(Reiniciar después: `sudo reboot`)*

---

*Workspace en la Pi: `~/.openclaw/workspace/`. Sincronizar con la carpeta local: `./push-workspace.sh` / `./pull-workspace.sh` en este repo.*
