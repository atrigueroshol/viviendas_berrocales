CREATE TABLE IF NOT EXISTS viviendas_kyrenia (
    id BIGSERIAL PRIMARY KEY,
    superficie_util TEXT,
    superficie_construida TEXT,
    habitaciones INTEGER,
    precio TEXT,
    plano TEXT,
    inserted_at TIMESTAMP
);
