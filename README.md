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
- Pruebas unitarias y de integración local.

### Validaciones realizadas

- Autenticación real desde Python: correcta.
- Extracción del 1 al 10 de octubre de 2026: 578 registros.
- Campos identificados en esa respuesta: 179.
- Extracción del 1 al 10 de septiembre de 2026: 599 registros.
- Suite automatizada: 12 pruebas superadas.
- Ruff: sin errores después de las correcciones.

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

La persistencia y la auditoría todavía no están implementadas.

## 5. Estructura del proyecto

```text
clisueno_cuestionarios/
├── src/
│   ├── __init__.py
│   ├── auth.py
│   ├── client.py
│   ├── config.py
│   └── dates.py
├── tests/
│   ├── test_auth.py
│   ├── test_client.py
│   └── test_dates.py
├── sql/
├── docs/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── TODO.md
```

Funciones de los módulos:

- `src/config.py`: lectura y validación de configuración.
- `src/auth.py`: autenticación y reintentos HTTP.
- `src/client.py`: extracción de cuestionarios.
- `src/dates.py`: cálculo de fechas en zona horaria de Colombia.
- `tests/`: pruebas automatizadas.
- `sql/`: reservado para estructuras PostgreSQL.
- `docs/`: reservado para documentación técnica.

El punto de entrada `src/daily.py` está previsto, pero todavía
no se considera implementado ni validado.

## 6. Entorno de desarrollo

**Sistema:** Ubuntu WSL.

**Directorio local:**

`/home/rom/obsino/clisueno_cuestionarios`

**Python:** 3.12.3.

**Control de versiones:** Git, rama `main`.

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

Variables adicionales previstas:

- `DATABASE_URL`
- `LOG_LEVEL`

Las credenciales no deben incorporarse a Git, logs ni documentación.

### 6.3. Ejecutar pruebas

```bash
python -m pytest tests/ -v
python -m ruff check src tests
```

## 7. Ejecución diaria prevista

### 7.1. Frecuencia

- Ejecución diaria.
- Horario: 03:00, `America/Bogota`.
- Fecha de extracción: día calendario anterior.
- Programación futura mediante `systemd timer`.

### 7.2. Requisitos operativos

- Ejecución sin intervención humana.
- Recuperación automática de días pendientes.
- Prevención de registros duplicados.
- Persistencia idempotente.
- Auditoría de ejecuciones.
- Control de concurrencia.
- Registro estructurado de errores.
- Recuperación ante interrupciones.

### 7.3. Inmutabilidad

Se adopta como requisito funcional que los cuestionarios registrados
no se modifican posteriormente.

Este supuesto deberá revisarse si cambia el comportamiento de MediCloud.

### 7.4. Carga histórica

La carga histórica se implementará en una fase posterior.

La prioridad actual es completar la extracción diaria.

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

- No existe persistencia en PostgreSQL.
- No existe control persistente de días procesados.
- No existe auditoría de ejecuciones.
- No hay recuperación implementada de días pendientes.
- No existe temporizador systemd.
- No hay tratamiento automático de un token expirado durante una consulta.
- No se ha definido todavía el contrato completo de datos y sus tipos.
- No se ha implementado la carga histórica.

Consultar `TODO.md` para conocer las prioridades de desarrollo.

## 11. Control de versiones

Repositorio Git independiente.

Rama de trabajo: `main`.

Commits registrados:

- `b6d4b6c`: implementación inicial del extractor API.
- `c442daa`: incorporación de reintentos HTTP y pruebas de integración.

Los cambios posteriores a estos commits todavía deben incorporarse
al control de versiones.

