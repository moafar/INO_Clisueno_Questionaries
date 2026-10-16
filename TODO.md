# TODO — Clisueno Cuestionarios

## Estado general

**Proyecto:** extractor desatendido de cuestionarios de sueño MediCloud.

**Estado:** desarrollo local en WSL; persistencia y auditoría transaccional verificadas con datos ficticios en PostgreSQL local. No se han cargado cuestionarios clínicos.

**Rama Git:** `feature/postgresql-storage` (trabajo en curso, `main` sin integrar).

**Pruebas:** 84 superadas en WSL (5,24 s) y Ruff sin errores (16-oct-2026). Pruebas de integración PostgreSQL local superadas; limpieza verificada.

**Prioridad actual:** definir e implementar detección y recuperación automática de días pendientes, con una fecha inicial de operación configurable y sin activar todavía la carga histórica.

La extracción histórica queda aplazada.

---

## 1. Componentes implementados

- [x] Inicializar repositorio Git independiente.
- [x] Crear entorno virtual Python 3.12.
- [x] Configurar `.gitignore`.
- [x] Crear plantilla `.env.example`.
- [x] Implementar carga y validación de configuración.
- [x] Implementar autenticación mediante Bearer Token.
- [x] Implementar consulta de cuestionarios por fechas.
- [x] Validar estructura básica de respuestas JSON.
- [x] Implementar reintentos HTTP en autenticación.
- [x] Implementar reintentos HTTP en extracción.
- [x] Validar reintentos mediante servidores HTTP locales.
- [x] Implementar cálculo del día anterior en `America/Bogota`.
- [x] Ejecutar 24 pruebas automatizadas satisfactoriamente (hasta logging JSON).
- [x] Validar código mediante Ruff.
- [x] Crear documentación inicial en `README.md`.

## 2. Prioridad alta — Extracción diaria

### 2.1. Punto de entrada

- [x] Crear `src/daily.py`.
- [x] Integrar configuración, autenticación y extracción.
- [x] Integrar validación del lote en `src/daily.py` (pruebas locales superadas).
- [x] Ejecutar extracción real del día anterior en Colombia (2026-10-14: 59 cuestionarios recibidos y validados, sin persistencia).
- [x] Incorporar logging estructurado.
- [x] Devolver códigos de salida adecuados.
- [x] Evitar exposición de información sensible en logs.
- [x] Crear pruebas automatizadas del proceso diario.

**Criterio de aceptación:**

El proceso determina el día anterior en Colombia, solicita los
cuestionarios y gestiona correctamente los errores sin intervención
humana.

La ejecución no se considerará una carga exitosa hasta completar
la persistencia y las validaciones correspondientes.

### 2.2. Validación de datos

- [x] Implementar contrato mínimo de estructura de la API en `src/validation.py` (pruebas locales superadas).
- [x] Definir `id` y `fecha` como obligatorios en el contrato mínimo.
- [ ] Determinar el significado y alcance del campo `id`.
- [x] Validar unicidad por lote y ausencia de identificadores nulos.
- [x] Validar fechas de los cuestionarios dentro del intervalo solicitado.
- [x] Rechazar el lote completo si algún registro incumple el contrato mínimo.
- [x] Implementar detección y aviso de deriva de esquema en `src/schema.py` y `src/daily.py` (verificado en la ejecución local).
- [x] Crear `tests/test_validation.py` y validar el contrato mínimo.

**Criterio de aceptación:**

Los registros se validan antes de incorporarse a PostgreSQL.
Las respuestas incompletas o inconsistentes no se marcan
silenciosamente como cargas satisfactorias.

### 2.3. Persistencia PostgreSQL

- [x] Definir destino local `obsino.staging.clisueno_questionaries`.
- [x] Definir tipos de datos y restricciones; estructura verificada en PostgreSQL local.
- [x] Adoptar `id` como clave única global por decisión funcional; una colisión con hash diferente genera error y rollback.
- [x] Crear `sql/001_create_clisueno_questionaries.sql`; DDL de tabla ejecutado y restricciones verificadas en `obsino` local (los COMMENT de la migración no se han confirmado como ejecutados).
- [x] Comprobar conexión `psycopg` en WSL mediante `DATABASE_URL` a PostgreSQL local.
- [x] Implementar inserciones idempotentes y validar dos ejecuciones con datos ficticios en PostgreSQL local.
- [x] Incorporar transacciones y almacenamiento reutilizable dentro de transacción externa; validación conjunta con auditoría superada en PostgreSQL local.
- [x] Verificar rollback ante conflicto de hash con datos ficticios en PostgreSQL local.
- [x] Añadir pruebas de persistencia e integración; transacción conjunta y rollback confirmados en PostgreSQL local.

**Criterio de aceptación:**

Una misma extracción puede ejecutarse repetidamente sin producir
cuestionarios duplicados ni cargas parciales inconsistentes.

Se conservan múltiples cuestionarios del mismo paciente.

### 2.4. Control de ejecuciones y recuperación

- [x] Adoptar `audit.load_control` como control de fechas por `pipeline_name`, día y estado `success`; réplica de su DDL e índices creada en PostgreSQL local, sin alterar producción.
- [x] Registrar ejecuciones correctas y fallidas en `audit.load_control`; reintentos fallidos repetidos probados.
- [x] Registrar cantidades recibidas y persistidas (`rows_read`, `rows_loaded`).
- [ ] Implementar detección de días pendientes.
- [ ] Recuperar automáticamente días no procesados.
- [x] Impedir marcar un día como completado antes del commit; rollback conjunto comprobado.
- [x] Considerar `success` una respuesta válida sin cuestionarios (`rows_read = rows_loaded = 0`), igual que en Labfp; probado.
- [ ] Crear pruebas de interrupción y recuperación.

**Criterio de aceptación:**

Si el extractor permanece inactivo varios días, recupera los
períodos pendientes sin duplicar registros.

Los días sin datos pueden registrarse como procesados correctamente
cuando la API responde de manera válida.

## 3. Prioridad alta — Seguridad y resiliencia

- [ ] Gestionar expiración o rechazo del Bearer Token.
- [ ] Diferenciar errores recuperables y permanentes.
- [ ] Revisar los límites de reintentos y tiempos de espera.
- [ ] Evitar reintentos indefinidos.
- [ ] Impedir ejecuciones concurrentes.
- [ ] Garantizar que los logs no contienen datos clínicos.
- [ ] Garantizar que las excepciones no exponen credenciales.
- [ ] Revisar tratamiento de respuestas JSON inesperadas.
- [ ] Solicitar rotación de credenciales antes de producción.

**Criterio de aceptación:**

La aplicación puede recuperarse de fallos transitorios, termina
de forma controlada ante fallos persistentes y protege los secretos.

## 4. Prioridad media — Auditoría y observabilidad

- [x] Reutilizar la estructura de producción de `audit.load_control` (réplica local creada y cuatro índices confirmados).
- [x] Decidir integración de Clisueno con `audit.load_control`, sin alterar los flujos de Labfp.
- [x] Registrar `started_at` y `finished_at` de los intentos auditados (`success` y `failed`).
- [ ] Registrar duración y estado final.
- [x] Registrar cantidades leídas y cargadas en `audit.load_control`.
- [x] Incorporar `load_id` UUID por intento.
- [x] Diferenciar categorías de fallo para API, validación y PostgreSQL, sin volcar datos clínicos en la auditoría.
- [ ] Definir alertas ante fallos persistentes.
- [ ] Preparar integración con Metabase.

**Criterio de aceptación:**

Es posible determinar qué día se procesó, cuándo se procesó,
qué resultado obtuvo y si requiere recuperación.

## 5. Prioridad media — Despliegue en mineriaino

- [ ] Revisar la estructura definitiva de `Clisueno`.
- [ ] Preparar instalación reproducible.
- [ ] Separar dependencias de producción y desarrollo.
- [ ] Configurar credenciales fuera del repositorio.
- [ ] Definir permisos y usuario de ejecución.
- [ ] Configurar servicio `systemd`.
- [ ] Configurar temporizador diario a las 03:00.
- [ ] Utilizar zona horaria `America/Bogota`.
- [ ] Configurar recuperación de ejecuciones programadas perdidas.
- [ ] Definir política de logs.
- [ ] Verificar conectividad HTTPS con MediCloud.
- [ ] Probar ejecución manual controlada.
- [ ] Validar ejecución programada.
- [ ] Actualizar `README_server.md`.
- [ ] Actualizar `CHANGELOG_server.md`.

**Criterio de aceptación:**

El extractor se ejecuta automáticamente en `mineriaino`,
persiste los datos y se recupera correctamente de interrupciones.

No requiere sesiones SSH ni intervención de un operador
para su funcionamiento ordinario.

## 6. Prioridad posterior — Extracción histórica

- [ ] Definir fecha de inicio histórica.
- [ ] Implementar partición temporal de consultas.
- [ ] Respetar el límite de 10 días de la API.
- [ ] Incorporar controles de progreso.
- [ ] Permitir reanudación de cargas interrumpidas.
- [ ] Reutilizar validación y persistencia de la extracción diaria.
- [ ] Evitar duplicados entre cargas históricas y diarias.
- [ ] Incorporar pruebas de carga histórica.

La carga histórica no forma parte del alcance inmediato.

## 7. Decisiones arquitectónicas

| Decisión | Estado |
|---|---|
| Desarrollo local en Ubuntu WSL | Confirmada |
| Python 3.12 | Confirmada |
| Repositorio Git independiente | Confirmada |
| Desarrollo en rama `feature/postgresql-storage` | En curso, pendiente de integrar en `main` |
| Servidor de ejecución `mineriaino` | Confirmada |
| Ejecución sin supervisión | Confirmada |
| Frecuencia diaria | Confirmada |
| Horario 03:00 America/Bogota | Confirmada |
| Extracción del día anterior | Confirmada |
| PostgreSQL como destino | Confirmada |
| Cuestionarios inmutables | Supuesto funcional |
| Clave única de cuestionario | `id` asumido globalmente único; conflictos protegidos con SHA-256 |
| Tabla PostgreSQL de destino | Creada y verificada en `obsino` local |
| Control de días pendientes | `audit.load_control` definido; detección y recuperación histórica pendiente |
| Carga histórica | Aplazada |

## 8. Requisitos no negociables

1. No almacenar credenciales en Git.
2. No registrar información clínica identificable en logs.
3. No considerar una carga exitosa antes de confirmar la persistencia.
4. No generar cuestionarios duplicados al repetir ejecuciones.
5. No depender de intervención humana para recuperar fallos ordinarios.
6. No modificar otros proyectos del servidor durante el despliegue.
7. Mantener pruebas automatizadas para los componentes críticos.
8. Documentar cambios operativos realizados en producción.

## 9. Punto de control — 16-oct-2026

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
- Pendientes prioritarios: **fecha inicial configurable, identificación de días pendientes y recuperación automática**, pruebas de interrupción; posteriormente revisar otros aspectos de resiliencia y preparar despliegue autónomo.
- La unicidad global de `id` permanece como supuesto funcional; no se ha verificado externamente.
- No ejecutar carga clínica real ni despliegue en `mineriaino` hasta completar las salvaguardas y pruebas pendientes.
