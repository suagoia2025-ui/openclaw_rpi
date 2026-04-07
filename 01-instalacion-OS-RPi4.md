# Instalación del OS en Raspberry Pi 4 (64 GB microSD)

Guía paso a paso para flashear Raspberry Pi OS y dejarlo listo para OpenClaw.

---

## Antes de empezar

- [ ] Raspberry Pi Imager descargado: https://www.raspberrypi.com/software/
- [ ] MicroSD de 64 GB insertada en el lector (contenido se borrará)
- [ ] Datos de tu WiFi (nombre y contraseña) si vas a usar WiFi

---

## Paso 1: Abrir Raspberry Pi Imager

1. Abre **Raspberry Pi Imager** en tu Mac/PC.
2. Si te pregunta, permite acceso a dispositivos de almacenamiento.

---

## Paso 2: Elegir el sistema operativo

1. Pulsa **"Elegir OS"** (o "Choose OS").
2. En **"Raspberry Pi OS (other)"** selecciona:
   - **Raspberry Pi OS Lite (64-bit)**  
     *(sin escritorio, ideal para servidor/OpenClaw)*

---

## Paso 3: Configuración previa (⚙️ importante)

1. Pulsa el **icono de engranaje** (⚙️) **antes** de grabar.
2. Marca **"Editar configuración al escribir"** (o "Set hostname and password...").
3. Rellena:

| Campo | Ejemplo | Notas |
|-------|---------|--------|
| **Hostname** | `hostopclaw` | Nombre de la Pi en la red |
| **Activar SSH** | ✅ Con contraseña | Para conectarte por `ssh` |
| **Usuario** | `serv_openclaw` (o el que quieras) | Usuario de la Pi |
| **Contraseña** | (la que elijas) | Guárdala bien |
| **WiFi** | SSID + contraseña | Solo si usas WiFi |
| **Zona horaria** | `America/Bogota` | Bogotá, Colombia |
| **Teclado** | Según tu país | Opcional |

4. Pulsa **"Guardar"** (Save).

---

## Paso 4: Elegir almacenamiento y grabar

1. Pulsa **"Elegir almacenamiento"** (Choose storage).
2. Selecciona tu **microSD de 64 GB** (revisa bien el nombre y tamaño).
3. Pulsa **"Siguiente"** (Next).
4. Confirma que quieres borrar todo en la tarjeta.
5. Espera a que termine (puede tardar 5–10 minutos).
6. Cuando diga "Éxito" o "Success", **expulsa la microSD con seguridad** y sácala.

---

## Paso 5: Arrancar la Raspberry Pi

1. Inserta la microSD en la Raspberry Pi 4.
2. Conecta:
   - Cable Ethernet (recomendado la primera vez) **o** deja que use WiFi si lo configuraste.
   - Fuente de alimentación (cargador oficial recomendado).
3. Espera **1–2 minutos** a que arranque y obtenga IP.

---

## Paso 6: Conectarte por SSH

Desde **Terminal** en tu Mac:

```bash
# Por nombre (hostname: hostopclaw)
ssh serv_openclaw@hostopclaw.local
```

Si no resuelve el nombre, busca la IP de la Pi en el router o usa:

```bash
ssh serv_openclaw@192.168.1.XXX
```

La primera vez preguntará si confías en el host: escribe `yes` y tu contraseña.

---

## Paso 7: Siguiente documento

Cuando ya estés dentro por SSH, sigue la guía:

**`02-setup-sistema-openclaw.md`**

(Actualizar sistema, Node.js 22, instalar OpenClaw, onboarding.)

---

## Resumen rápido

| Paso | Acción |
|------|--------|
| 1 | Abrir Raspberry Pi Imager |
| 2 | OS: **Raspberry Pi OS Lite (64-bit)** |
| 3 | Engranaje: hostname, SSH, usuario, contraseña, WiFi, zona horaria |
| 4 | Storage: microSD 64 GB → Siguiente → esperar |
| 5 | MicroSD en la Pi → alimentación → esperar 1–2 min |
| 6 | `ssh serv_openclaw@hostopclaw.local` (o por IP) |

---

*OpenClaw on Raspberry Pi 4 — Documentación: https://docs.openclaw.ai/platforms/raspberry-pi*
