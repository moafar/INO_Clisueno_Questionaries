# CHANGELOG — Clisueno Cuestionarios

Registro de versiones y cambios operativos del extractor de cuestionarios de sueño MediCloud.

**Convención de versiones:** un único archivo **vacío y sin extensión** en la raíz del repositorio identifica visualmente la versión vigente, por ejemplo `v1.0.0`. El historial y las verificaciones se documentan aquí; el marcador no sustituye una etiqueta Git ni los commits.

## [v1.0.0] — 2026-10-17 — MVP implantado, pendiente de aceptación final

### Incorporado

- Extractor Python 3.12 para autenticación y consultas a MediCloud por fecha, validación de cuestionarios y detección no bloqueante de deriva del esquema.
- CLI con `--date`, `--start-date`, `--end-date`, `--dry-run` y `--recover`.
- Persistencia PostgreSQL idempotente con JSONB, hash SHA-256 y protección frente a colisiones de `id` con contenido distinto.
- Auditoría en `audit.load_control`, con commit conjunto de datos y `success`; registro de intentos fallidos.
- Recuperación de fechas sin éxito desde `CLISUENO_START_DATE`, con un máximo de siete días por ejecución y bloqueos contra ejecución concurrente.
- Reintentos HTTP acotados y renovación única de token ante HTTP 401; errores restantes tratados de forma genérica.
- Logs estructurados JSON sin volcado intencional de registros clínicos.
- 141 pruebas automáticas superadas en WSL y en `mineriaino`.

### Implantación en `mineriaino` (2026-10-17)

- **Primer paso:** creación manual y verificación de `obsino.staging.clisueno_questionaries` (8 columnas, PK, restricciones y comentarios).
- Comprobación de compatibilidad de `audit.load_control` existente, sin cambios en esa tabla ni en proyectos de Labfp o Investigaciones.
- Instalación del código en `/opt/apps/etl/obsino/clisueno/cuestionarios` desde la rama `feature/postgresql-storage`, con entorno virtual Python 3.12.3.
- Configuración de MediCloud y PostgreSQL local por `.env` excluido de Git; permisos `600 rom:ops`; conexión PostgreSQL por socket Unix (`postgresql:///obsino`).
- Prueba API `--dry-run` del 10 de octubre: **57 registros validados**, sin escritura.
- Primera persistencia real autorizada del 1 de octubre: **58 cuestionarios**, 58 identificadores distintos y una auditoría `success`; segunda ejecución omitida por idempotencia.
- Recuperación real del 2 al 16 de octubre en tres invocaciones `--recover`, cronológicas y limitadas a siete fechas.
- **Verificación final:** **925 cuestionarios** persistidos entre el 01 y el 16 de octubre de 2026, **16 auditorías `success`**, **0 `failed`**.
- Creación en el servidor de `/etc/systemd/system/clisueno_questionaries.service` y `clisueno_questionaries.timer`. La ejecución manual del servicio informó «No hay días pendientes de recuperación».
- Temporizador `enabled` y `active (waiting)`; calendario diario `03:00 America/Bogota` y `Persistent=true`. Próxima ejecución programada al verificar: **18 de octubre de 2026**.
- Documentación centralizada en `README.md`, prioridades en `TODO.md` y marcador vacío `v1.0.0`.

### Pendiente para dar por aceptada la operación automática

- Verificar **después de las 03:00 del 18-oct-2026 (Colombia)** la primera ejecución activada por el temporizador, su salida, una auditoría `success` para el 17-oct y la integridad de la carga.
- Tras ese control, decidir la integración de `feature/postgresql-storage` en `main` y la sincronización del servidor.

### Limitaciones y decisiones

- Se mantiene el tratamiento genérico de errores HTTP. Su clasificación detallada, alertas avanzadas y monitorización adicional quedan para la Fase 2.
- La unicidad global de `id` no está confirmada por MediCloud; se aplica la regla conservadora de rechazo y rollback ante un conflicto de hash.
- No se han ejecutado pruebas destructivas de interrupción en el servidor de producción; tales pruebas se realizaron anteriormente con datos ficticios en PostgreSQL local.
- La extracción histórica específica y la integración con Metabase quedan fuera del MVP.
- Los archivos `systemd` están instalados en el servidor y sus parámetros están documentados en `README.md`; no se incluyen como archivos de unidad versionados en este commit.

---
