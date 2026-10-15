# TODO — Clisueno Cuestionarios

## Estado general

**Proyecto:** extractor desatendido de cuestionarios de sueño MediCloud.

**Estado:** desarrollo local en WSL.

**Rama Git:** `main`.

**Pruebas:** 24 superadas antes de incorporar la validación; pruebas nuevas pendientes de ejecutar.

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

- [x] Implementar contrato mínimo de estructura de la API en `src/validation.py` (pendiente de pruebas locales).
- [x] Definir `id` y `fecha` como obligatorios en el contrato mínimo.
- [ ] Determinar el significado y alcance del campo `id`.
- [x] Validar unicidad por lote y ausencia de identificadores nulos.
- [x] Validar fechas de los cuestionarios dentro del intervalo solicitado.
- [x] Rechazar el lote completo si algún registro incumple el contrato mínimo.
- [ ] Detectar cambios inesperados de esquema.
- [x] Crear `tests/test_validation.py` (pendientes de ejecución local).

**Criterio de aceptación:**

Los registros se validan antes de incorporarse a PostgreSQL.
Las respuestas incompletas o inconsistentes no se marcan
silenciosamente como cargas satisfactorias.

### 2.3. Persistencia PostgreSQL

- [ ] Definir esquema y tabla de destino.
- [ ] Definir tipos de datos y restricciones.
- [ ] Determinar la clave única de cada cuestionario.
- [ ] Crear migración SQL inicial.
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
| Tabla PostgreSQL de destino | Pendiente |
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

**Ejecutar y revisar localmente las pruebas de `src/validation.py`.**

El contrato mínimo valida `id`, `fecha`, unicidad por lote y estructura
de listas de medicamentos; conserva intactas las respuestas originales.
Pendiente verificar las pruebas en WSL y Ruff, monitorizar deriva de esquema,
y conectar la validación al flujo diario antes de persistir.

La persistencia PostgreSQL continúa pendiente.
