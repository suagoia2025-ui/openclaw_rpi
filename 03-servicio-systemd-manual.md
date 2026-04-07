# Servicio OpenClaw (systemd, usuario)

OpenClaw instala un **servicio de usuario** (no de sistema): el unit está en `~/.config/systemd/user/openclaw-gateway.service`. Se gestiona con `systemctl --user` (sin `sudo`).

---

## 1. Instalar el servicio con el CLI (recomendado)

En la Pi, como usuario `serv_openclaw`:

```bash
openclaw gateway install
```

O con opciones:

```bash
openclaw gateway install --port 18789
openclaw gateway install --force   # reinstalar si ya existe
```

El servicio se crea en:

```
/home/serv_openclaw/.config/systemd/user/openclaw-gateway.service
```

---

## 2. Gestionar el servicio (usuario)

Usa **systemctl --user** (no `sudo systemctl`). El nombre del unit es **openclaw-gateway**:

```bash
# Recargar systemd (tras editar el .service)
systemctl --user daemon-reload

# Activar al arranque
systemctl --user enable openclaw-gateway

# Iniciar ahora
systemctl --user start openclaw-gateway

# Estado
systemctl --user status openclaw-gateway

# Reiniciar
systemctl --user restart openclaw-gateway

# Parar
systemctl --user stop openclaw-gateway
```

Ver logs:

```bash
journalctl --user -u openclaw-gateway -f
```

Comprobar desde OpenClaw:

```bash
openclaw status
```

---

## 3. Arranque al encender la Pi (sin sesión abierta)

Por defecto los servicios de usuario solo corren si hay una sesión abierta. Para que el gateway arranque al boot aunque nadie haga login, activa **lingering**:

```bash
sudo loginctl enable-linger serv_openclaw
```

Comprueba:

```bash
loginctl show-user serv_openclaw | grep Linger
# Debe mostrar: Linger=yes
```

---

## 4. Crear o editar el servicio a mano (solo si hace falta)

Si el CLI no instaló el servicio o quieres cambiar algo, crea/edita el unit de usuario.

### 4.1 Crear el directorio y el archivo

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/openclaw-gateway.service
```

### 4.2 Contenido del unit (servicio de usuario)

Ajusta la ruta de `openclaw` si en tu sistema está en otro sitio (ej. `which openclaw`):

```ini
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="PATH=%h/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=%h/.npm-global/bin/openclaw gateway --port 18789
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openclaw-gateway

[Install]
WantedBy=default.target
```

`%h` es la home del usuario (ej. `/home/serv_openclaw`). Guarda (Ctrl+O, Enter) y cierra (Ctrl+X).

### 4.3 Activar e iniciar

```bash
systemctl --user daemon-reload
systemctl --user enable openclaw-gateway
systemctl --user start openclaw-gateway
systemctl --user status openclaw-gateway
```

No olvides `sudo loginctl enable-linger serv_openclaw` si quieres que arranque al boot sin sesión.

---

## 5. Alternativa: servicio de sistema (avanzado)

Si prefieres un servicio de **sistema** (gestionado con `sudo systemctl`), créalo así. Requiere sudo.

```bash
sudo nano /etc/systemd/system/openclaw.service
```

```ini
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=serv_openclaw
Group=serv_openclaw
Environment="PATH=/home/serv_openclaw/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOME=/home/serv_openclaw"
ExecStart=/home/serv_openclaw/.npm-global/bin/openclaw gateway --port 18789
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openclaw

[Install]
WantedBy=multi-user.target
```

Luego:

```bash
sudo systemctl daemon-reload
sudo systemctl enable openclaw
sudo systemctl start openclaw
sudo systemctl status openclaw
journalctl -u openclaw -f
```

El método por defecto de OpenClaw es el **servicio de usuario** (sección 1–4); este es opcional.

---

*Resumen: servicio de usuario → `openclaw gateway install` → `systemctl --user` + `openclaw-gateway` + `enable-linger`.*
