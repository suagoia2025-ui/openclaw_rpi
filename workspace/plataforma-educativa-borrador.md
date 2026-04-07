# Plataforma educativa para empresas — Borrador inicial

## 1. Objetivo general
Crear una plataforma multi-empresa que permita a cada organización capacitar a sus equipos internos y, en paralelo, ofrecer itinerarios de aprendizaje a sus clientes para acompañar la adopción de productos o servicios.

## 2. Usuarios y casos de uso
- **Administradores Suago**: configuran nuevas empresas, plantillas de contenido y reglas básicas.
- **Gestores de cada empresa**: suben cursos propios, asignan rutas a empleados/clientes, consultan métricas.
- **Empleados**: consumen formación obligatoria (onboarding, compliance, skills internas) y programas de mejora continua.
- **Clientes de la empresa**: acceden a academias de producto, certificaciones e itinerarios para maximizar el uso de la solución contratada.

## 3. Propuesta de valor
1. **Catálogo dual** (interno + externo) con experiencias diferenciadas.
2. **Automatizaciones**: asignación de rutas por rol, recordatorios y nudges de finalización.
3. **Analítica accionable**: tableros por empresa, cohortes y alertas de riesgo (quién no avanza, quién destaca).
4. **Experiencia marca blanca**: cada empresa personaliza branding, dominios y mensajes.

## 4. Funcionalidad núcleo
| Área | Funciones clave |
| --- | --- |
| Gestión multi-tenant | Alta/baja de empresas, plantillas de configuración, separación de datos. |
| Contenido | Editor de cursos (video, SCORM, quizzes), biblioteca compartida y duplicado de plantillas. |
| Rutas de aprendizaje | Agrupar cursos, definir prerrequisitos, fechas objetivo y certificaciones. |
| Evaluación | Quizzes, tareas prácticas, rúbricas, firmas digitales si aplica. |
| Social/soporte | Foros moderados, preguntas rápidas, sesiones en vivo opcionales. |
| Analítica | Paneles en tiempo real, exportaciones CSV, API para BI externo. |
| Integraciones | SSO (Google/M365), webhooks, LMS/LXP externos, CRMs (ej. HubSpot) para clientes. |

## 5. Contenido y metodología
- **Biblioteca base** producida por Suago (buenas prácticas, soft skills, customer success) reutilizable por todas las empresas.
- **Módulos propietarios** cargados por cada empresa (manuales, procesos, certificaciones).
- **Learning paths mixtos**: combinan piezas on-demand, talleres en vivo (Zoom/Meet) y evaluaciones.
- **Gamificación ligera**: insignias, puntos por avance, tableros amigables.

## 6. Opciones tecnológicas (exploración)
1. **Adaptar un LMS abierto** (ej. Moodle, Open edX) con capa multi-tenant y branding.
   - + Base robusta, comunidad grande.
   - – Personalización visual limitada sin esfuerzo extra; UX puede sentirse vieja.
2. **Construir sobre un LXP headless** (ej. Strapi + front Next.js, o Supabase + React).
   - + Control total de experiencia, APIs modernas.
   - – Mayor esfuerzo inicial en features “básicas” (tracking SCORM/xAPI, reportes).
3. **Modelo híbrido**: LMS existente + portal propio para clientes.
   - + Time-to-market rápido mientras se valida el modelo.
   - – Complejidad operativa (sincronizar datos entre sistemas).

_Acciones inmediatas_: evaluar requerimientos de compliance (ISO, SOC, LOPD), idiomas necesarios y dispositivos objetivo (desktop vs mobile first).

## 7. Roadmap sugerido
1. **Descubrimiento (2-3 semanas)**
   - Entrevistas con 3-5 empresas piloto (HR, Customer Success).
   - Definición de MVP (features imprescindibles) y métricas.
2. **MVP (8-10 semanas)**
   - Multi-tenant básico, catálogo interno, rutas simples, reportes esenciales.
   - Portal de clientes con 1–2 cursos de ejemplo.
3. **Pilotos cerrados (4 semanas)**
   - Implantar en 1 empresa (empleados) + 1 empresa (clientes) para validar workflows.
4. **Iteración y escalado**
   - Añadir integraciones prioritarias, gamificación, automatizaciones y marketplace de cursos.

## 8. Próximos pasos
- Confirmar industrias objetivo y número de empresas piloto.
- Decidir si partimos de LMS existente o build propio.
- Inventariar contenido disponible y brechas.
- Diseñar mockups de experiencia (panel admin, vista alumno interno, vista cliente).
- Estimar presupuesto (desarrollo, hosting, soporte) y modelo de negocio (suscripción por empresa, usuarios activos, etc.).

---
Este borrador es un punto de partida. Añadiré detalles a medida que tengamos más claridad sobre audiencias, stack y contenidos. 