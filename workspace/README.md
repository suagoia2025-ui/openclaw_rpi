# Workspace OpenClaw (edición local)

Archivos de personalidad y comportamiento del agente. Se editan aquí y se suben a la Raspberry Pi con el script de la raíz del repo.

**Resumen del proyecto y arquitectura:** ver [`../README.md`](../README.md).

## Traer archivos desde la Pi (pull)

Desde la raíz del clon del repositorio (en tu Mac o PC):

```bash
cd /ruta/al/clon/openclaw_rpi
./pull-workspace.sh
```

Equivalente manual:

```bash
scp -r serv_openclaw@hostopclaw.local:~/.openclaw/workspace/* ./workspace/
```

Si `hostopclaw.local` no resuelve, usa la IP:

```bash
scp -r serv_openclaw@192.168.1.16:~/.openclaw/workspace/* ./workspace/
```

## Enviar archivos a la Pi (push) después de editar

```bash
cd /ruta/al/clon/openclaw_rpi
./push-workspace.sh
```

(Te pedirá la contraseña SSH de `serv_openclaw` si no usas clave.)

Reiniciar el gateway en la Pi para cargar cambios (opcional):

```bash
ssh serv_openclaw@hostopclaw.local "systemctl --user restart openclaw-gateway"
```

## Archivos del workspace

| Archivo | Uso |
|---------|-----|
| **SOUL.md** | Personalidad, tono y valores del agente. |
| **AGENTS.md** | Reglas de trabajo: qué debe / no debe hacer; herramientas (cámara, Brave, `gog`). |
| **USER.md** | Información sobre ti (preferencias, contexto). |
| **TOOLS.md** | Notas locales: cámara CSI, ReSpeaker, **Gmail/Calendar con `gog`**, convenciones. |
| **IDENTITY.md** | Nombre del agente, “vibe”, descripción. |
| **HEARTBEAT.md** | Comportamiento ante heartbeats. |
| **MEMORY.md** | Memoria a largo plazo (en la Pi: `~/.openclaw/workspace/`). Lo crea/actualiza el agente. |
| **memory/** | Un archivo por día `memory/YYYY-MM-DD.md`. |
| Otros `.md` | Borradores o notas (ej. plataforma educativa). |

**¿Existen en la Pi?** Pueden no existir hasta que el agente los cree. Comprobar en la Pi:

```bash
ls -la ~/.openclaw/workspace/
ls ~/.openclaw/workspace/memory/
```

Documentación OpenClaw: [Agent Workspace](https://docs.openclaw.ai/concepts/agent-workspace).
