# TODO — Clisueno Cuestionarios

## Estado general

**Proyecto:** extractor desatendido de cuestionarios de sueño MediCloud.

**Estado:** desarrollo local en WSL.

**Rama Git:** `main`.

**Pruebas:** último resultado confirmado en WSL: 56 superadas y Ruff sin errores (15-oct-2026).

**Prioridad actual:** completar la extracción diaria y su persistencia
segura en PostgreSQL.

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
- [x] Integrar validación del lote en `src/daily.py` (49 pruebas superadas en WSL).
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

- [x] Implementar contrato mínimo de estructura de la API en `src/validation.py` (22 pruebas superadas en WSL).
- [x] Definir `id` y `fecha` como obligatorios en el contrato mínimo.
- [ ] Determinar el significado y alcance del campo `id`.
- [x] Validar unicidad por lote y ausencia de identificadores nulos.
- [x] Validar fechas de los cuestionarios dentro del intervalo solicitado.
- [x] Rechazar el lote completo si algún registro incumple el contrato mínimo.
- [x] Implementar detección y aviso de deriva de esquema en `src/schema.py` y `src/daily.py` (pendiente de pruebas locales).
- [x] Crear `tests/test_validation.py` (22 pruebas superadas en WSL).

**Criterio de aceptación:**

Los registros se validan antes de incorporarse a PostgreSQL.
Las respuestas incompletas o inconsistentes no se marcan
silenciosamente como cargas satisfactorias.

### 2.3. Persistencia PostgreSQL

- [x] Definir destino local `obsino.staging.clisueno_questionaries`.
- [x] Definir tipos de datos y restricciones; estructura verificada en PostgreSQL local.
- [ ] Determinar la clave única de cada cuestionario.
- [x] Crear `sql/001_create_clisueno_questionaries.sql`; DDL de tabla ejecutado y restricciones verificadas en `obsino` local (los COMMENT de la migración no se han confirmado como ejecutados).
- [ ] Implementar conexión mediante `psycopg`.
- [ ] Implementar inserciones idempotentes.
- [ ] Incorporar transacciones.
- [ ] Implementar rollback ante errores.
- [ ] Crear pruebas de persistencia.

**Criterio de aceptación:**

Una misma extracción puede ejecutarse repetidamente sin producir
cuestionarios duplicados ni cargas parciales inconsistentes.

Se conservan múltiples cuestionarios del mismo paciente.

### 2.4. Control de ejecuciones y recuperación

- [ ] Definir tabla de control de fechas procesadas.
- [ ] Registrar ejecuciones correctas y fallidas.
- [ ] Registrar cantidad de registros recibidos y persistidos.
- [ ] Implementar detección de días pendientes.
- [ ] Recuperar automáticamente días no procesados.
- [ ] Impedir marcar un día como completado antes del commit.
- [ ] Definir tratamiento de días sin cuestionarios.
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

- [ ] Definir estructura de auditoría.
- [ ] Evaluar integración con `audit.load_control`.
- [ ] Registrar inicio y finalización de cada ejecución.
- [ ] Registrar duración y estado final.
- [ ] Registrar cantidades de registros procesados.
- [ ] Incorporar identificadores de ejecución.
- [ ] Diferenciar errores de API, validación y PostgreSQL.
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
| Desarrollo en rama `main` | Confirmada |
| Servidor de ejecución `mineriaino` | Confirmada |
| Ejecución sin supervisión | Confirmada |
| Frecuencia diaria | Confirmada |
| Horario 03:00 America/Bogota | Confirmada |
| Extracción del día anterior | Confirmada |
| PostgreSQL como destino | Confirmada |
| Cuestionarios inmutables | Supuesto funcional |
| Clave única de cuestionario | Pendiente de validar |
| Tabla PostgreSQL de destino | Creada y verificada en `obsino` local |
| Control de días pendientes | Pendiente |
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

## 9. Próxima tarea

**Probar detector de deriva de esquema y preparar persistencia PostgreSQL.**

Verificado el 15-oct-2026 en WSL:
- 49 pruebas automatizadas superadas y Ruff sin errores.
- Ejecución real `python -m src.daily`: 59 cuestionarios de 2026-10-14
  extraídos y validados; no almacenados en PostgreSQL.

Pendientes inmediatos:
- [ ] Ejecutar Ruff y suite completa en WSL tras incorporar `src/schema.py`.
- [ ] Verificar avisos de esquema en una extracción real.
- [x] Implementar comparación con los 179 nombres de referencia, sin rechazar automáticamente el lote (pendiente de pruebas locales).
- [ ] Confirmar semántica y unicidad global de `id` (solo se ha observado
      unicidad por lote y estabilidad entre consultas).
- [x] Preparar migración SQL y crear/verificar tabla en PostgreSQL local.
- [ ] Implementar carga transaccional idempotente, control de hash y auditoría.
- [ ] No considerar procesado un día antes del commit de persistencia.

La estructura `CREATE TABLE` ya se ejecutó en PostgreSQL local. Los `COMMENT ON` de la migración no se han confirmado como ejecutados. La semántica global de `id` sigue pendiente de confirmación.\n\nLa ejecución actual con código de salida 0 significa **extracción y validación**,
no carga persistida ni día definitivamente procesado.

## Punto seguro de suspensión — 15-oct-2026

- Código remoto `main`: extracción, validación y detección de deriva funcionales; persistencia **no implementada**.
- Conexión local comprobada desde Python mediante `DATABASE_URL` en `.env` (no versionar secretos).
- `obsino.staging.clisueno_questionaries`: ocho columnas, cuatro restricciones verificadas; cero filas antes de cualquier carga.
- Nombres originales confirmados en `schemas/cuestionarios_v1.json`: `tipoDocumento` -> `tipo_documento`, `Documento` -> `documento`, `Sede` -> `sede`; `id` y `fecha` conservan nombre.
- La referencia versionada contiene nombres de 179 campos; no determina por sí sola los tipos ni la nulabilidad observados para estos tres campos. Revisar mapeo y reglas de null/vacío antes de insertar.
- Siguiente tarea: diseñar e implementar `src/storage.py` con SHA-256 determinista, transacciones, idempotencia y rechazo seguro de conflictos; añadir pruebas y luego integrar en `src/daily.py`.
- No ejecutar carga de datos reales ni dar por procesado un día hasta superar pruebas y validar rollback/commit.
