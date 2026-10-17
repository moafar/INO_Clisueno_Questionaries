# TODO — Clisueno Cuestionarios

**Repositorio:** `moafar/INO_Clisueno_Questionaries` · **Rama de desarrollo:** `feature/postgresql-storage` (`main` aún sin integrar).

**Plan actualizado:** 17-oct-2026. El objetivo inmediato es **implantar un MVP operativo, autónomo y seguro en `mineriaino`**. Todo lo que no sea imprescindible para ponerlo en servicio pasa a la fase de evoluciones.

**Situación verificada hasta el 16-oct:** 141 pruebas superadas en WSL y Ruff sin errores; persistencia, transacciones, auditoría, rollback, recuperación y concurrencia probadas con datos ficticios en PostgreSQL local. **No hay carga clínica confirmada ni despliegue realizado en `mineriaino`.**

**Decisión de alcance:** mantener el tratamiento genérico de errores HTTP y los reintentos limitados ya existentes. No introducir por ahora una nueva taxonomía de errores. La extracción histórica y las mejoras avanzadas se aplazan.

---

## FASE 1 — MVP: desarrollo mínimo e implantación

### 1.1. Desarrollo requerido para el MVP — ya implementado y validado localmente

- [x] Repositorio independiente, entorno Python 3.12, configuración por variables de entorno y `.gitignore`.
- [x] Autenticación MediCloud y extracción por fecha; cálculo del día anterior con `America/Bogota`.
- [x] Ejecución diaria mediante `src/daily.py`, opciones `--date`, `--start-date`, `--end-date` y `--dry-run`.
- [x] Validación mínima de datos (`id`, `fecha`, estructura, unicidad por lote, intervalo); rechazo completo del lote inválido.
- [x] Detección no bloqueante de cambios de nombres de campos respecto de la referencia de 179 campos.
- [x] Persistencia idempotente en `staging.clisueno_questionaries`, con SHA-256, transacciones y rollback; validada **solo en PostgreSQL local**.
- [x] Integración transaccional con `audit.load_control`; resultados `success` y `failed`, cantidades y fechas de ejecución.
- [x] Recuperación explícita `--recover` de días sin éxito, en orden y con máximo de siete fechas por ejecución.
- [x] Bloqueos por día y para la recuperación, con liberación ante interrupciones; pruebas concurrentes con PostgreSQL local.
- [x] Reintentos HTTP acotados, tratamiento genérico de fallos y renovación única del token ante 401; 403 sin renovación.
- [x] Logging JSON con mensajes de error controlados y pruebas de no exposición de detalles sensibles.
- [x] Pruebas de componentes e integración locales: **141 passed** y Ruff correcto (16-oct-2026).

**Decisión funcional vigente:** se utiliza `id` como identificador global de cuestionario, aunque su unicidad global no está confirmada externamente. Una colisión con contenido diferente causa error y rollback, en vez de sobrescribir información. Mantener esa salvaguarda para el MVP.

### 1.2. Implantación del MVP en `mineriaino` — secuencia obligatoria

**La primera actividad de implantación es crear y verificar la persistencia en `mineriaino`. No iniciar por `systemd`, cron ni una carga real.**

- [ ] **1.** **Crear la persistencia en `mineriaino`:** verificar la base `obsino` y el esquema `staging`; revisar/adaptar `sql/001_create_clisueno_questionaries.sql` (actualmente indica ejecución solo local), crear `staging.clisueno_questionaries` con sus columnas y restricciones y comprobar la compatibilidad de la tabla compartida `audit.load_control` y sus índices **sin modificar Labfp**. Verificar estructura y tabla vacía; registrar qué DDL se aplicó.
- [ ] **2.** Preparar una identidad de ejecución y permisos mínimos para lectura/escritura en las tablas de Clisueno y los campos de auditoría necesarios, sin ampliar permisos de otros proyectos.
- [ ] **3.** Instalar el repositorio y dependencias en el área `/opt/apps/etl/obsino/clisueno/`, sin reutilizar `medicloud_extract` ni intervenir Labfp/Investigaciones.
- [ ] **4.** Configurar fuera de Git `DATABASE_URL`, credenciales MediCloud y `CLISUENO_START_DATE` (fecha inicial autorizada); restringir permisos de acceso a secretos y comprobar HTTPS y ausencia de información clínica en logs. Resolver únicamente fallos de seguridad que impidan operar.
- [ ] **5.** Ejecutar en `mineriaino` una prueba manual `--dry-run` de una fecha cerrada: autenticar, extraer y validar **sin escribir cuestionarios ni auditoría**.
- [ ] **6.** **Con autorización explícita para la primera carga clínica**, ejecutar una única fecha controlada en modo normal. Verificar filas, restricciones, hash, commit y `audit.load_control`; comprobar que no se imprimen credenciales ni datos identificables en logs.
- [ ] **7.** Repetir esa fecha para verificar que no duplica cuestionarios; comprobar una recuperación controlada y que los días `success` se omiten. Detener el despliegue si falla la consistencia.
- [ ] **8.** Configurar servicio y temporizador `systemd` para ejecución autónoma diaria a las **03:00 `America/Bogota`**. Usar la recuperación ya implementada (`--recover`), inicio histórico autorizado y ejecución compensatoria de temporizadores perdidos; evitar procesos simultáneos.
- [ ] **9.** Verificar la primera ejecución programada, la auditoría, los logs y la capacidad de recuperar una interrupción sin intervención humana.
- [ ] **10.** Documentar instalación, configuración, operación y reversión mínima en `README_server.md` y cambios efectivos en `CHANGELOG_server.md`; tras la aceptación, integrar la rama de desarrollo en `main`.

**Condiciones de aceptación del MVP:** ejecución autónoma diaria; datos persistidos íntegramente sin duplicados; día `success` solo después del commit; días fallidos recuperables; secretos fuera del repositorio; logs sin información clínica identificable; otros proyectos de `mineriaino` intactos. No activar el temporizador hasta superar las comprobaciones anteriores.

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
| Área de instalación | `/opt/apps/etl/obsino/clisueno/` |
| Base y tabla destino | `obsino.staging.clisueno_questionaries` |
| Auditoría | Reutilizar `audit.load_control` sin alterar Labfp |
| Ejecución | Diaria, 03:00 `America/Bogota`, autónoma |
| Fechas | Día anterior y recuperación desde fecha de inicio autorizada |
| Identidad de cuestionario | `id` global asumido; conflicto de hash protegido |
| Tratamiento HTTP | Genérico, reintentos acotados, renovación única ante 401 |
| Persistencia clínica | Todavía no realizada |
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
