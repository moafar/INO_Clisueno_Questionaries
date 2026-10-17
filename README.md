# Clisueno — Extractor de cuestionarios de sueño MediCloud

**Versión desplegada:** `v1.0.0` · **Actualizado:** 17 de octubre de 2026  
**Estado:** MVP instalado y funcionando en `mineriaino` (carga manual y recuperación verificadas). **Pendiente verificar la primera ejecución automática del temporizador, prevista para el 18 de octubre de 2026 a las 03:00, hora de Colombia.**

La versión actual se identifica mediante un **archivo vacío y sin extensión en la raíz del repositorio llamado `v1.0.0`**. El archivo es un marcador visible, no un ejecutable ni una etiqueta Git: al publicar una versión posterior se sustituirá el marcador anterior, se actualizarán este README y `CHANGELOG.md`, y se coordinará el despliegue.

## 1. Propósito y funcionamiento

Extraer cuestionarios de sueño desde MediCloud y almacenarlos en PostgreSQL del Observatorio INO, con validación, idempotencia, auditoría y recuperación automática de días pendientes.

```text
MediCloud API (HTTPS)
    -> autenticación Bearer Token
    -> extracción de un día por petición
    -> validación del lote y alerta de deriva de esquema
    -> PostgreSQL: cuestionarios + auditoría en una transacción
    -> reanudación de días sin éxito
```

- **Servidor:** `mineriaino`.
- **Código:** `/opt/apps/etl/obsino/clisueno/cuestionarios`.
- **Python:** 3.12.3; dependencias aisladas en `.venv`.
- **Repositorio:** `moafar/INO_Clisueno_Questionaries`.
- **Rama implantada:** `feature/postgresql-storage`; aún no integrada en `main`.
- **Programación:** `clisueno_questionaries.timer`, diaria a las **03:00 `America/Bogota`**.
- **Servicio:** `clisueno_questionaries.service`, ejecuta `python -m src.daily --recover`.
- **Fecha inicial autorizada de recuperación:** `2026-10-01`.

## 2. Estado verificable en producción (17-oct-2026)

| Verificación | Resultado |
|---|---|
| Pruebas automáticas en `mineriaino` | **141 passed in 6.25s** |
| Conexión API real (`--dry-run` del 10-oct) | 57 registros validados, sin escritura |
| Primera carga controlada (01-oct) | 58 recibidos, 58 persistidos |
| Repetición del 01-oct | Omitida por día ya procesado |
| Recuperación `--recover` | 02–16 oct, en lotes de hasta 7 días |
| Total en `staging.clisueno_questionaries` | **925 cuestionarios** (01–16 oct) |
| Auditoría de Clisueno en `audit.load_control` | **16 `success`**, **0 `failed`** |
| Prueba manual del servicio `systemd` | Correcta: «No hay días pendientes de recuperación» |
| Temporizador | `enabled` y `active (waiting)` |
| Primera ejecución programada | **Pendiente comprobar: 18-oct, 03:00 Colombia** |

Las pruebas de rollback, liberación de bloqueos por interrupción y contención concurrente se realizaron previamente con datos ficticios en PostgreSQL local. **No se ha simulado una interrupción deliberada del servidor de producción.** Las cifras anteriores corresponden al momento de verificación y cambiarán con nuevas extracciones.

## 3. API MediCloud

- **Servidor:** `https://nm.medicloud.com.co`.
- **Autenticación:** `POST /auth/getToken`; encabezados `App_Id`, `App_Key`, `Resource` y `ApiVersion`. La respuesta aporta el token.
- **Extracción:** `POST /apisueno/getCuestionarioSueno`, autenticación `Authorization: Bearer <token>`, cuerpo `application/x-www-form-urlencoded` con `fechaInicial` y `fechaFinal` (`YYYY-MM-DD`).
- **Respuesta:** objeto JSON `status=success` con `datos` (lista de cuestionarios).
- La API permite un intervalo de hasta 10 días de diferencia; la ejecución diaria y la recuperación consultan **una sola fecha por solicitud**.
- HTTP 401 en extracción: renovar token y repetir la petición una vez. HTTP 403: detener sin renovar. HTTP 429 y 5xx incluidos en los reintentos limitados actuales; otros errores se gestionan de forma genérica.

## 4. Persistencia y auditoría

**Base:** `obsino` · **Esquema y tabla:** `staging.clisueno_questionaries`.

Columnas: `id` (PK `BIGINT`), `fecha` (`DATE`), `tipo_documento`, `documento`, `sede` (`TEXT`), `datos` (`JSONB`), `hash_contenido` (`CHAR(64)`) y `created_at` (`TIMESTAMPTZ`). Se verificaron restricciones sobre `id`, JSONB y hash.

**Auditoría:** `audit.load_control`, tabla compartida ya existente. No se modificó su estructura ni la de otros proyectos. Cada fecha exitosa registra el volumen leído/cargado y se confirma en la **misma transacción** que los cuestionarios. Los fallos se registran por intento cuando es posible.

La clave `id` se **asume globalmente única**, sin confirmación externa de MediCloud. Si un `id` existente presenta contenido distinto, el proceso rechaza la colisión con rollback; no sobrescribe datos. Un día con auditoría `success` no vuelve a extraerse; una respuesta válida con cero registros puede considerarse éxito.

**Implantación del esquema:** primero se creó manualmente la tabla de cuestionarios en `mineriaino` con el DDL revisado de `sql/001_create_clisueno_questionaries.sql` y sus `COMMENT`; después se verificó que `audit.load_control` existente cumplía el contrato. El archivo SQL conserva un comentario de ejecución limitada al entorno local: **no ejecutarlo indiscriminadamente en producción**.

## 5. Configuración y seguridad

El archivo `.env` **no se versiona**. En el servidor está protegido con permisos `600`, propietario `rom`. Su exclusión está comprobada con `git check-ignore -v .env`.

Variables necesarias:

| Variable | Uso |
|---|---|
| `MEDICLOUD_BASE_URL` | URL HTTPS base de MediCloud |
| `MEDICLOUD_APP_ID`, `MEDICLOUD_APP_KEY` | Identificación y secreto de aplicación |
| `MEDICLOUD_RESOURCE`, `MEDICLOUD_API_VERSION` | Parámetros de autenticación |
| `DATABASE_URL` | Conexión PostgreSQL; en `mineriaino`, `postgresql:///obsino` |
| `CLISUENO_START_DATE` | Fecha inicial de `--recover`; en producción, `2026-10-01` |

El proceso se ejecuta como `rom` con grupo `ops`, y se verificó acceso `SELECT`/`INSERT` sobre ambas tablas. La conexión local a PostgreSQL emplea socket Unix sin contraseña en `.env`.

No pegar tokens, claves ni el contenido completo de `.env` en incidencias, commits o logs. El proyecto trata datos clínicos identificables; los logs previstos incluyen información operativa y conteos, **no el contenido de los cuestionarios**. Profundizar la revisión de seguridad y políticas de permisos/rotación es una posible evolución posterior.

## 6. Ejecución

Desde `/opt/apps/etl/obsino/clisueno/cuestionarios`:

```bash
# Validar una fecha sin ninguna escritura en PostgreSQL
.venv/bin/python -m src.daily --date 2026-10-10 --dry-run

# Ejecutar una fecha con persistencia y auditoría
.venv/bin/python -m src.daily --date AAAA-MM-DD

# Ejecutar un intervalo inclusivo (una fecha por petición)
.venv/bin/python -m src.daily --start-date AAAA-MM-DD --end-date AAAA-MM-DD

# Procesar hasta 7 fechas pendientes desde CLISUENO_START_DATE
.venv/bin/python -m src.daily --recover

# Ejecutar la suite local
.venv/bin/python -m pytest tests/ -q
```

**Atención:** los comandos que no incluyen `--dry-run` escriben datos clínicos en PostgreSQL; su uso debe ser autorizado. `--recover` no acepta `--dry-run` ni otras opciones de selección de fecha. No se pueden procesar fechas posteriores a ayer según `America/Bogota`.

La recuperación selecciona cronológicamente los días que **no tienen `success`**, con un **máximo de 7 fechas por invocación**. Los éxitos anteriores se conservan ante un fallo posterior. Los bloqueos PostgreSQL evitan dos recuperaciones simultáneas y dos ejecuciones de una misma fecha. Tras un período de inactividad superior a siete días, pueden hacer falta varias invocaciones para ponerse al día.

## 7. Operación autónoma con systemd

Las unidades están instaladas directamente en `/etc/systemd/system/` del servidor:

- `clisueno_questionaries.service`: `Type=oneshot`, `User=rom`, `Group=ops`, `WorkingDirectory=/opt/apps/etl/obsino/clisueno/cuestionarios`, `ExecStart=/opt/apps/etl/obsino/clisueno/cuestionarios/.venv/bin/python -m src.daily --recover`, `TimeoutStartSec=30min`, `UMask=0077`, `NoNewPrivileges=true`; tras `network-online.target`.
- `clisueno_questionaries.timer`: `OnCalendar=*-*-* 03:00:00 America/Bogota`, `Persistent=true`, `Unit=clisueno_questionaries.service`; habilitado para arrancar con el servidor.

**Comprobaciones operativas sin nueva carga:**

```bash
systemctl status clisueno_questionaries.timer --no-pager -l
systemctl status clisueno_questionaries.service --no-pager -l
journalctl -u clisueno_questionaries.service --since today --no-pager
systemctl list-timers clisueno_questionaries.timer --no-pager
```

Un servicio `oneshot` terminado correctamente puede aparecer como `inactive (dead)`; revisar el resultado de ejecución y los registros, no solo el estado `Active`.

**Control básico posterior a la próxima ejecución:**

```sql
SELECT source_start_date, status, rows_read, rows_loaded, finished_at
FROM audit.load_control
WHERE pipeline_name = 'clisueno_questionaries_daily'
ORDER BY source_start_date DESC
LIMIT 5;
```

Si falla, conservar la evidencia de `systemd` y auditoría **sin copiar datos clínicos**; no marcar días como completados a mano ni eliminar registros clínicos para forzar un reintento. La recuperación usa la auditoría para retomar fechas no completadas.

## 8. Código y documentación

- `src/config.py`: lectura y validación de variables de entorno.
- `src/auth.py` / `src/client.py`: autenticación y consumo de MediCloud.
- `src/dates.py`: fechas en `America/Bogota`.
- `src/daily.py`: CLI diario, fechas manuales, `--dry-run` y `--recover`.
- `src/validation.py` / `src/schema.py`: contrato del lote y detección de deriva.
- `src/storage.py` / `src/audit.py`: almacenamiento, idempotencia, bloqueos y auditoría.
- `schemas/cuestionarios_v1.json`: referencia versionada de campos.
- `sql/001_create_clisueno_questionaries.sql`: DDL inicial de la tabla.
- `tests/`: suite de pruebas.
- `TODO.md`: tareas de aceptación del MVP y evoluciones posteriores.
- `CHANGELOG.md`: historial de cambios de versiones y despliegues.
- `v1.0.0`: marcador de versión, archivo **vacío y sin extensión**.

## 9. Pendientes y límites del MVP

- **Pendiente para aceptación final:** comprobar la primera ejecución diaria real del temporizador el **18-oct-2026, 03:00 `America/Bogota`** y confirmar fecha nueva, auditoría y ausencia de errores.
- Integrar `feature/postgresql-storage` en `main` cuando se cierre la aceptación; después sincronizar el clon del servidor.
- La semántica global de `id` es un supuesto protegido contra colisiones, no una garantía de la API.
- Alertas avanzadas, paneles Metabase, refactorización detallada de fallos HTTP y extracción histórica específica quedan en **Fase 2**.

Consultar el `TODO.md` actualizado para el detalle de cierre y evoluciones.
