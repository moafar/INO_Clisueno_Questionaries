# TODO — Clisueno Cuestionarios

**Repositorio:** `moafar/INO_Clisueno_Questionaries` · **Rama principal:** `main`, con `v1.0.0` integrado mediante fast-forward el 17-oct-2026. Clon de `mineriaino` aún situado en `feature/postgresql-storage` (mismo código del MVP).

**Plan actualizado:** 17-oct-2026. **Versión del MVP desplegada: `v1.0.0`** (marcador vacío en la raíz del repositorio). Se conserva una Fase 1 de implantación mínima y una Fase 2 de evoluciones.

**Situación al 17-oct:** repositorio instalado en `/opt/apps/etl/obsino/clisueno/cuestionarios`, Python 3.12.3, 141 pruebas superadas en `mineriaino` (6,25 s). PostgreSQL `obsino`: **925 cuestionarios** del **01 al 16-oct-2026**, **16 auditorías `success`**, **0 `failed`** y validación explícita de idempotencia. Servicio manual `clisueno_questionaries.service` verificado; `clisueno_questionaries.timer` **enabled / active (waiting)** para las **03:00 `America/Bogota`**. **Pendiente comprobar la primera ejecución automática prevista para el 18-oct-2026 y cerrar la aceptación operativa.**

**Decisión de alcance:** mantener el tratamiento genérico de errores HTTP y los reintentos limitados ya existentes. No introducir por ahora una nueva taxonomía de errores. La extracción histórica y las mejoras avanzadas se aplazan.

---

## FASE 1 — MVP: desarrollo mínimo e implantación

### 1.1. Desarrollo requerido para el MVP — ya implementado y validado localmente

- [x] Repositorio independiente, entorno Python 3.12, configuración por variables de entorno y `.gitignore`.
- [x] Autenticación MediCloud y extracción por fecha; cálculo del día anterior con `America/Bogota`.
- [x] Ejecución diaria mediante `src/daily.py`, opciones `--date`, `--start-date`, `--end-date` y `--dry-run`.
- [x] Validación mínima de datos (`id`, `fecha`, estructura, unicidad por lote, intervalo); rechazo completo del lote inválido.
- [x] Detección no bloqueante de cambios de nombres de campos respecto de la referencia de 179 campos.
- [x] Persistencia idempotente en `staging.clisueno_questionaries`, con SHA-256, transacciones y rollback: probada con datos ficticios localmente y con cargas reales en `mineriaino`.
- [x] Integración transaccional con `audit.load_control`; resultados `success` y `failed`, cantidades y fechas de ejecución.
- [x] Recuperación explícita `--recover` de días sin éxito, en orden y con máximo de siete fechas por ejecución.
- [x] Bloqueos por día y para la recuperación, con liberación ante interrupciones; pruebas concurrentes con PostgreSQL local.
- [x] Reintentos HTTP acotados, tratamiento genérico de fallos y renovación única del token ante 401; 403 sin renovación.
- [x] Logging JSON con mensajes de error controlados y pruebas de no exposición de detalles sensibles.
- [x] Pruebas de componentes e integración: **141 passed** y Ruff correcto en WSL (16-oct); **141 passed in 6.25s** en `mineriaino` (17-oct).

**Decisión funcional vigente:** se utiliza `id` como identificador global de cuestionario, aunque su unicidad global no está confirmada externamente. Una colisión con contenido diferente causa error y rollback, en vez de sobrescribir información. Mantener esa salvaguarda para el MVP.

### 1.2. Implantación del MVP en `mineriaino` — estado al 17-oct-2026

La **primera actividad de implantación fue la creación y verificación de la persistencia PostgreSQL en `mineriaino`**, antes de instalar o ejecutar el servicio. No se alteraron las tablas existentes de Labfp.

- [x] **1. Persistencia:** en `obsino` se comprobó `staging` y se creó `staging.clisueno_questionaries` mediante DDL revisado de `sql/001_create_clisueno_questionaries.sql`, con 8 columnas, PK, tres restricciones CHECK y comentarios; se verificó vacía inicialmente. `audit.load_control` ya existía: se verificaron columnas e índices y se confirmó compatibilidad sin modificarla. El SQL del repositorio conserva un comentario inicial que limita su ejecución al entorno local; el DDL equivalente se aplicó manualmente en el servidor.
- [x] **2. Usuario y permisos:** servicio configurado con `User=rom` y `Group=ops`; comprobados `SELECT`/`INSERT` para las dos tablas. Se usa PostgreSQL local con `DATABASE_URL=postgresql:///obsino`. No se creó un rol exclusivo: evaluar endurecimiento de privilegios tras el MVP si procede.
- [x] **3. Instalación:** código clonado en `/opt/apps/etl/obsino/clisueno/cuestionarios`, rama `feature/postgresql-storage`; Python 3.12.3, `.venv`, dependencias instaladas y 141 pruebas satisfactorias. No se modificaron proyectos de Labfp ni de Investigaciones.
- [x] **4. Configuración:** credenciales MediCloud en `.env` del servidor (sin secretos en Git), permisos `600 rom:ops`, exclusión confirmada por `.gitignore`; `CLISUENO_START_DATE=2026-10-01`. Conectividad real con MediCloud y PostgreSQL verificada. No incluir valores de secretos en la documentación.
- [x] **5. Simulación real:** `--date 2026-10-10 --dry-run`: 57 registros, validación correcta, sin persistencia.
- [x] **6. Primera carga clínica autorizada:** `--date 2026-10-01`: 58 recibidos y 58 persistidos; 58 identificadores distintos; una auditoría `success`, `rows_read=rows_loaded=58`.
- [x] **7. Idempotencia y recuperación:** segunda ejecución del 1-oct omitida (`Fecha ya procesada`), manteniendo 58 registros y una sola auditoría; tres ejecuciones explícitas `--recover` procesaron del 2 al 16-oct (máximo siete días por ejecución). Comprobación final: **925 cuestionarios**, **16 `success`**, **0 `failed`**.
- [x] **8. Servicio y temporizador:** creados en `/etc/systemd/system/` los archivos `clisueno_questionaries.service` (`Type=oneshot`, usuario `rom`, `ExecStart` con `--recover`) y `clisueno_questionaries.timer` (`OnCalendar=*-*-* 03:00:00 America/Bogota`, `Persistent=true`). `systemd-analyze verify` sin errores; prueba manual del servicio informó «No hay días pendientes de recuperación». Timer `enabled` y `active (waiting)`.
- [ ] **9. Primera ejecución automática:** verificar el **18-oct-2026** después de las 03:00 Colombia: estado de la unidad, `journalctl`, fecha 17-oct con `success`, conteos coherentes y ausencia de datos clínicos en los logs. El comportamiento ante fallo e interrupción se ha probado localmente, **no mediante una interrupción deliberada en producción**.
- [x] **10. Documentación/versionado:** actualizar `README.md` y crear `CHANGELOG.md` y archivo vacío `v1.0.0` en la rama de desarrollo (17-oct). Los archivos de unidad `systemd` están instalados en el servidor, no versionados como plantillas.
- [ ] **11. Cierre de implantación:** la integración de `feature/postgresql-storage` en `main` ya se completó el 17-oct-2026. Cambiar el checkout de `mineriaino` a `main` sin alterar la versión instalada; tras la primera ejecución automática satisfactoria, confirmar aceptación operativa.

**Criterios de aceptación:** extracción autónoma diaria; persistencia y auditoría transaccionales sin duplicados; recuperación de días pendientes; credenciales fuera de Git; ausencia de datos identificables en logs; ningún impacto sobre otros proyectos. Las pruebas manuales y las cargas iniciales están superadas; la **aceptación final requiere la primera ejecución programada**.

### 1.3. Deliberadamente fuera del MVP

No bloquear la implantación por refactorización de errores HTTP, métricas sofisticadas, alertas avanzadas, dashboards, estudio histórico completo ni optimizaciones no exigidas por fallos reales. Corregir solo defectos que comprometan integridad, seguridad o funcionamiento autónomo básico.

---

## FASE 2 — Evoluciones posteriores al MVP

### 2.1. Resiliencia y seguridad ampliadas

- [ ] Valorar clasificación explícita de errores HTTP recuperables y permanentes **solo si la experiencia operativa lo justifica**.
- [ ] Revisar y optimizar límites de reintentos, `Retry-After`, tiempos máximos de espera y tratamiento de redirecciones.
- [ ] Ampliar pruebas de respuestas JSON inesperadas, fallos de red y recuperación prolongada.
- [ ] Profundizar en auditoría de secretos y logs, política de rotación de credenciales y endurecimiento de configuración.

### 2.2. Observabilidad y explotación

- [ ] Incorporar indicadores de duración, latencia, volumen y tendencias operativas.
- [ ] Definir alertas automáticas ante fallos persistentes o retrasos de extracción.
- [ ] Preparar integración con Metabase u otra herramienta de seguimiento.
- [ ] Evaluar controles adicionales de deriva de esquema y calidad de datos.

### 2.3. Evolución funcional y mantenimiento

- [ ] Confirmar con MediCloud el significado y la unicidad global del campo `id`; adaptar modelo solo si la evidencia lo exige.
- [ ] Evaluar separación de dependencias de desarrollo y producción y automatización de despliegues.
- [ ] Definir el alcance y fecha inicial de una **extracción histórica** específica.
- [ ] Implementar la carga histórica en intervalos permitidos por la API (máximo de 10 días), con seguimiento, reanudación, validación, idempotencia y convivencia con la extracción diaria.
- [ ] Revisar escalabilidad, retención y requisitos adicionales según el volumen real.

---

## Decisiones y restricciones transversales

| Decisión | Estado |
|---|---|
| Desarrollo local | WSL Ubuntu + Python 3.12 |
| Servidor objetivo | `mineriaino` |
| Área de instalación | `/opt/apps/etl/obsino/clisueno/cuestionarios/` |
| Base y tabla destino | `obsino.staging.clisueno_questionaries` |
| Auditoría | Reutilizar `audit.load_control` sin alterar Labfp |
| Ejecución | Diaria, 03:00 `America/Bogota`, autónoma |
| Fechas | Día anterior y recuperación desde fecha de inicio autorizada |
| Identidad de cuestionario | `id` global asumido; conflicto de hash protegido |
| Tratamiento HTTP | Genérico, reintentos acotados, renovación única ante 401 |
| Persistencia clínica | 925 cuestionarios y 16 días auditados (01–16 oct 2026) en `mineriaino` |
| Extracción histórica específica | Fase 2 |

**Restricciones:** nunca versionar credenciales; nunca escribir información clínica identificable en logs; no confirmar éxitos antes del commit; no permitir cargas parciales inconsistentes ni duplicados; no alterar proyectos ajenos; conservar pruebas de los componentes críticos y documentar cambios de producción.

## Anexo — Registro de validaciones previo a la replanificación

Este registro es **histórico**, no una lista vigente de trabajo. Los pasos y prioridades actuales son los de la **FASE 1** anterior.

### Bitácora de pruebas locales — 16-oct-2026 (histórico)

- Rama de desarrollo: `feature/postgresql-storage` (`main` sin integrar); no se ha tocado producción.
- **Validación WSL:** 84 pruebas superadas en 5,24 s; Ruff sin errores.
- **PostgreSQL local:** `obsino` en `127.0.0.1`; `staging.clisueno_questionaries` y réplica local de `audit.load_control` con clave primaria y tres índices verificados.
- **Integraciones reales con datos ficticios, todas superadas:**
  1. Lote vacío: auditoría `success` con `rows_read=0` y `rows_loaded=0`.
  2. Dos intentos `failed` sobre el mismo día: ambos registrados sin conflicto de unicidad.
  3. Inserción de cuestionario ficticio y auditoría `success` en una misma transacción.
  4. Conflicto de `id` con contenido cambiado: rollback completo, sin inserción parcial ni `success` espurio.
- **Limpieza final verificada:** `staging.clisueno_questionaries = 0` registros; `audit.load_control = 0` registros.
- `source_file_hash`: en `success`, SHA-256 del lote JSON ordenado por `id`; en `failed`, `failed:<load_id>:<SHA-256|not_available>` para permitir reintentos sin cambiar el índice único compartido.
- `--dry-run` real anterior: 2026-10-15, 59 registros validados, sin escritura en PostgreSQL.
- Ejecución manual `--date 2026-10-10 --dry-run` probada contra MediCloud: 57 cuestionarios; tablas locales verificadas vacías.
- **Intervalo manual validado:** `--start-date`/`--end-date` procesa día a día en orden cronológico y detiene la secuencia ante el primer error; 103 pruebas superadas (5,29 s), Ruff sin errores y consulta real `--dry-run` de 2026-10-09 (58) y 2026-10-10 (57), total 115 cuestionarios.
- **Comprobación posterior a `--dry-run`:** ambas tablas locales `staging.clisueno_questionaries` y `audit.load_control` con 0 registros.
- **Recuperación implementada sin activación:** `CLISUENO_START_DATE` obligatoria solo con `--recover`; selección sin `success`, máximo 7 días por ejecución y parada al primer fallo. `--recover --dry-run` se rechaza porque el `--dry-run` no debe acceder a PostgreSQL.
- **Pruebas de recuperación confirmadas en WSL:** 120 passed (5,47 s); Ruff corregido y sin errores. Commit local de estilo `9e3a4d6`, publicado en GitHub.
- **Integración PostgreSQL local:** selección del 1 y 2 de enero de 2000 con límite 2; un día `success` (0 filas) se excluye y los `failed` o sin registro quedan pendientes; simulación de recuperación de 3 días, con fallo en el segundo, reanudación en el segundo intento y sin duplicar el primero.
- **Limpieza posterior confirmada:** `staging.clisueno_questionaries = 0` y `audit.load_control = 0`.
- **Bloqueo de recuperación validado:** `exclusive_recovery()` obtiene `pg_try_advisory_lock` de sesión con clave reservada `(LOCK_NAMESPACE, 0)` y mantiene su conexión durante la selección y procesamiento de todos los días. En PostgreSQL local, una segunda recuperación simultánea fue rechazada y, tras cerrar la primera, se pudo adquirir el bloqueo nuevamente. La conexión se cierra al finalizar o fallar; sigue existiendo bloqueo transaccional por día para otras modalidades.
- **Validación más reciente:** 127 pruebas aprobadas en 5,43 s, Ruff sin errores y prueba de bloqueo de sesión sobre PostgreSQL local superada. Ajustes de estilo en `tests/test_audit.py` guardados y publicados en commit `7b5f9dc`.
- **Interrupción abrupta probada:** un proceso auxiliar adquirió `exclusive_recovery()`, la segunda conexión fue rechazada, el proceso auxiliar terminó con `SIGKILL` y un nuevo intento adquirió el bloqueo liberado. Prueba sin consultas MediCloud ni escrituras SQL. Esto verifica liberación de bloqueo, no rollback de una transacción de persistencia interrumpida.
- **Concurrencia mixta identificada:** el bloqueo global `(LOCK_NAMESPACE, 0)` y el transaccional diario `(LOCK_NAMESPACE, ordinal)` pueden coexistir; no bastan para evitar dos consultas MediCloud antes de la escritura. Implementado `exclusive_day()` con bloqueo de sesión `(LOCK_NAMESPACE, -ordinal)` adquirido antes de `is_processed` y la autenticación y mantenido durante extracción, persistencia y auditoría del fallo. Si la fecha está ocupada, se rechaza sin consulta API ni registro `failed`. Validado con 134 pruebas anteriores y comprobación posterior de dos procesos independientes con API simulada.
- **Última validación completada:** 134 pruebas en 5,53 s y Ruff sin errores. En PostgreSQL local, `exclusive_day()` rechaza una segunda conexión para la misma fecha y permite otra fecha; `exclusive_recovery()` y `exclusive_day()` coexisten y la fecha vuelve a estar disponible tras liberación. Sin consultas MediCloud ni escrituras.
- **Rollback y reanudación transaccional confirmados:** un proceso auxiliar insertó un cuestionario ficticio y un `success` de auditoría en la misma transacción sin `COMMIT`; tras `SIGKILL` ambas inserciones se revirtieron (0 filas) y se liberó el bloqueo. `persist_day()` confirmó después el mismo día (1 cuestionario y 1 auditoría); al repetir, devolvió `already_processed` y 0 nuevos. Se eliminaron ambos registros de prueba. Esto verifica la capa transaccional; no constituye una prueba extremo a extremo del CLI ni de MediCloud.
- **Prueba de concurrencia con dos procesos reales completada:** `main()` del primer proceso mantuvo `exclusive_day()` durante una API simulada pausada; el segundo `main()` devolvió 1 sin entrar en la API. El primero terminó con 0; ambas tablas permanecieron vacías. Se usó PostgreSQL local real con mocks de MediCloud y persistencia. Sin escrituras ni acceso a producción.
- **Renovación controlada validada en WSL:** `src.client` distingue HTTP 401 mediante `MedicloudUnauthorizedError`. `src.daily.main()` adquiere un nuevo token y repite una única vez la solicitud, sin bucles; registra `AUTH_ERROR` si falla la renovación o persiste el 401. HTTP 403 y otros errores API no renuevan token. Pruebas unitarias y con servidor HTTP local aprobadas sin PostgreSQL ni MediCloud.
- **Última validación WSL (16-oct-2026):** Ruff sin errores tras corrección `UP031` en `tests/test_daily.py`; `python -m pytest tests/ -q`: **141 passed in 5.87s**. Corrección de estilo publicada en GitHub, commit `d7a3c66`, rama `feature/postgresql-storage`.
- La unicidad global de `id` permanece como supuesto funcional; no se ha verificado externamente.
