-- Migración inicial. Ejecutar solamente en obsino local, tras revisión.
-- No crea ni modifica otros esquemas ni tablas.
-- El hash se calcula en Python sobre JSON serializado de forma determinista.
CREATE TABLE staging.clisueno_questionaries (
    id BIGINT PRIMARY KEY CHECK (id > 0),
    fecha DATE NOT NULL,
    tipo_documento TEXT,
    documento TEXT,
    sede TEXT,
    datos JSONB NOT NULL,
    hash_contenido CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT clisueno_questionaries_datos_objeto_chk
        CHECK (jsonb_typeof(datos) = 'object'),
    CONSTRAINT clisueno_questionaries_hash_chk
        CHECK (hash_contenido ~ '^[0-9a-f]{64}$')
);

COMMENT ON TABLE staging.clisueno_questionaries IS
    'Cuestionarios MediCloud: una fila por diligenciamiento; datos íntegros en JSONB.';
COMMENT ON COLUMN staging.clisueno_questionaries.id IS
    'Identificador de cuestionario provisto por MediCloud; unicidad global pendiente de confirmación.';
COMMENT ON COLUMN staging.clisueno_questionaries.hash_contenido IS
    'SHA-256 hexadecimal de la serialización JSON determinista; algoritmo a documentar en el loader.';
