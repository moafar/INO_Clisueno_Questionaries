# Clisueno — Extractor de cuestionarios MediCloud

## 1. Propósito

Aplicación Python para extraer automáticamente los cuestionarios de sueño
registrados en MediCloud y almacenarlos en PostgreSQL del Observatorio INO.

El sistema está diseñado desde el inicio para ejecutarse sin supervisión
en el servidor `mineriaino`.

## 2. Estado del proyecto

**Estado: en desarrollo. No desplegado en producción.**

### Funcionalidades implementadas

- Lectura y validación de configuración mediante variables de entorno.
- Autenticación contra la API MediCloud mediante Bearer Token.
- Extracción de cuestionarios por intervalo de fechas.
- Validación básica de las respuestas JSON.
- Reintentos HTTP ante fallos transitorios.
- Cálculo del día anterior en la zona horaria `America/Bogota`.
- Ejecución manual por fecha (`--date`) y por intervalo inclusivo (`--start-date`, `--end-date`).
- Persistencia idempotente en `staging.clisueno_questionaries` y auditoría compartida en `audit.load_control`.
- Transacción por fecha y rollback ante conflictos de contenido.
- Pruebas unitarias y de integración local.

### Validaciones realizadas

- Autenticación real desde Python: correcta.
- Extracción del 1 al 10 de octubre de 2026: 578 registros.
- Campos identificados en esa respuesta: 179.
- Extracción del 1 al 10 de septiembre de 2026: 599 registros.
- Suite automatizada: 92 pruebas superadas (16-oct-2026), antes de la incorporación del intervalo manual.
- Ruff: sin errores en dicha validación.
- Integración con PostgreSQL local: lote vacío, intentos fallidos repetidos, transacción conjunta y rollback validados; tablas vacías después de limpiar.

Estas cifras corresponden a las pruebas realizadas y no constituyen
garantías sobre el volumen o esquema de futuras respuestas.

## 3. API MediCloud

**Servidor:** `https://nm.medicloud.com.co`

### 3.1. Autenticación

**Endpoint:** `POST /auth/getToken`

Cabeceras:

- `App_Id`
- `App_Key`
- `Resource`
- `ApiVersion`

La respuesta contiene:

- `status`
- `token_type`
- `access_token`

### 3.2. Extracción de cuestionarios

**Endpoint:** `POST /apisueno/getCuestionarioSueno`

Autenticación:

```http
Authorization: Bearer <token>
```

Cuerpo de la petición: `application/x-www-form-urlencoded`.

Parámetros:

- `fechaInicial`: YYYY-MM-DD
- `fechaFinal`: YYYY-MM-DD

La documentación establece una diferencia máxima de 10 días.

La respuesta es un objeto JSON con los campos:

- `status`
- `datos`: arreglo de cuestionarios.

## 4. Arquitectura prevista

```text
API MediCloud
    |
    v
Autenticación automática
    |
    v
Extracción por fechas
    |
    v
Validación de registros
    |
    v
Persistencia PostgreSQL
    |
    v
Auditoría de ejecución
```

La persistencia y la auditoría están implementadas en la rama de desarrollo y probadas en PostgreSQL local con registros ficticios. No se ha desplegado en producción.

## 5. Módulos principales

- `src/config.py`: configuración y credenciales desde variables de entorno.
- `src/auth.py` y `src/client.py`: autenticación y consulta MediCloud.
- `src/dates.py`: calendario `America/Bogota`.
- `src/daily.py`: ejecución diaria, manual por fecha o intervalo.
- `src/validation.py` y `src/schema.py`: validación de respuestas y detección de cambios de esquema.
- `src/storage.py`: persistencia idempotente con control de conflictos.
- `src/audit.py`: auditoría y transacción compartida por día.
- `tests/`: pruebas automatizadas.
- `sql/`: definición de tablas de cuestionarios para el entorno local.
- `TODO.md`: estado verificable y prioridades actuales.

## 6. Entorno de desarrollo

**Sistema:** Ubuntu WSL.

**Directorio local:**

`/home/rom/obsino/clisueno_cuestionarios`

**Python:** 3.12.3.

**Control de versiones:** rama de desarrollo `feature/postgresql-storage`; `main` no incorpora todavía todos los cambios.

### 6.1. Instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 6.2. Configuración

Crear `.env` a partir de `.env.example`.

Variables de MediCloud:

- `MEDICLOUD_BASE_URL`
- `MEDICLOUD_APP_ID`
- `MEDICLOUD_APP_KEY`
- `MEDICLOUD_RESOURCE`
- `MEDICLOUD_API_VERSION`

Variable de persistencia requerida en ejecución normal:

- `DATABASE_URL` (PostgreSQL; no se utiliza durante `--dry-run`).

Las credenciales no deben incorporarse a Git, logs ni documentación.

### 6.3. Ejecutar pruebas

```bash
python -m pytest tests/ -v
python -m ruff check src tests
```

## 7. Ejecución manual y automática

### 7.1. Ejecutar desde WSL

```bash
# Simular el día anterior (sin acceso a PostgreSQL)
python -m src.daily --dry-run

# Simular una fecha concreta
python -m src.daily --date 2026-10-10 --dry-run

# Simular un intervalo inclusivo, día por día
python -m src.daily --start-date 2026-10-01 --end-date 2026-10-10 --dry-run

# Ejecución diaria con persistencia y auditoría (solo tras autorización operativa)
python -m src.daily
```

**Importante:** la modalidad por intervalos está implementada en la rama de desarrollo, pero todavía requiere validar Ruff, pytest y un intervalo real con `--dry-run` en WSL. No ejecutar cargas clínicas reales mientras persistan salvaguardas pendientes.

Las fechas se expresan como `YYYY-MM-DD`. No se admiten días posteriores a ayer en `America/Bogota`. Para intervalos, se requieren ambas fechas y `--date` no se puede combinar con ellas.

Cada fecha se consulta por separado, de modo que respeta el límite de la API de 10 días por petición. En modo normal, cada día confirma cuestionarios y auditoría en la misma transacción; los días con `success` anterior se omiten. Un fallo detiene el intervalo y no revierte las fechas ya confirmadas. En `--dry-run` no se consulta ni se modifica PostgreSQL.

### 7.2. Frecuencia automática prevista

- Frecuencia: diaria, a las 03:00, `America/Bogota`.
- Fecha por defecto: día calendario anterior.
- Programación futura mediante `systemd timer`.
- **Pendiente:** detección y recuperación automática de días sin `success`, a partir de una fecha inicial de operación configurable.

### 7.3. Requisitos operativos

- Ejecución sin intervención humana.
- Recuperación automática de días pendientes.
- Prevención de duplicados e idempotencia.
- Auditoría de ejecuciones y errores.
- Control de concurrencia y recuperación ante interrupciones.
- Logs estructurados sin datos identificables.

### 7.4. Inmutabilidad

Se adopta como supuesto funcional que los cuestionarios registrados no se modifican posteriormente. El `id` se asume globalmente único; un `id` ya almacenado con distinto hash provoca rollback. Este supuesto deberá revisarse si cambia MediCloud.

### 7.5. Carga histórica

La carga histórica automática sigue aplazada; un intervalo manual explícito no supone activar el reprocesamiento histórico desatendido.

## 8. Despliegue previsto

**Servidor:** `mineriaino`.

**Ubicación lógica:**

`/opt/apps/etl/obsino/Clisueno/cuestionarios`

Conforme a las políticas del servidor:

- Código desplegado bajo `/opt/apps`.
- Datos operativos bajo `/srv/data`.
- Backups bajo `/srv/backups`.
- Credenciales fuera del repositorio y protegidas por permisos.
- Cambios operativos documentados en el README y CHANGELOG del servidor.

El desarrollo se realiza localmente.

La aplicación todavía no se ha desplegado en `mineriaino`.

## 9. Seguridad

El proyecto procesa información clínica y datos identificativos.

Requisitos:

- No almacenar credenciales en Git.
- No registrar tokens ni datos personales en logs.
- Restringir el acceso a los datos extraídos.
- Mantener HTTPS para la comunicación con MediCloud.
- Gestionar errores sin exponer secretos.
- Utilizar privilegios mínimos en PostgreSQL.
- Rotar las credenciales utilizadas durante las pruebas antes
  del despliegue definitivo.

## 10. Limitaciones actuales

- No hay recuperación automática de fechas pendientes ni fecha inicial configurable de operación.
- No se ha configurado `systemd` ni desplegado el proyecto en `mineriaino`.
- La ejecución manual por intervalos aún requiere validación en WSL.
- Está pendiente el manejo integral de un token expirado durante una consulta y las alertas operativas.
- El significado y unicidad global del campo `id` son supuestos funcionales aún no contrastados externamente.
- La carga histórica automática no está implementada.

Consultar `TODO.md` para conocer las prioridades y las pruebas confirmadas.

## 11. Control de versiones

Repositorio independiente: `moafar/INO_Clisueno_Questionaries`.

Rama actual de desarrollo: `feature/postgresql-storage`. Los cambios aún no se han integrado en `main`.

