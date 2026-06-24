from __future__ import annotations

from pathlib import Path

import pandas as pd
import psycopg


TABLE_NAME = "viviendas_kyrenia"
CREATE_TABLE_SQL_PATH = Path(__file__).with_name("create_table.sql")

COLUMN_MAPPING = {
    "Superficie útil": "superficie_util",
    "Superficie util": "superficie_util",
    "Superficie construida": "superficie_construida",
    "Habitaciones": "habitaciones",
    "Precio": "precio",
    "Plano": "plano",
    "inserted_at": "inserted_at",
}

DB_COLUMNS = [
    "superficie_util",
    "superficie_construida",
    "habitaciones",
    "precio",
    "plano",
    "inserted_at",
]

INSERT_SQL = f"""
    INSERT INTO {TABLE_NAME} (
        superficie_util,
        superficie_construida,
        habitaciones,
        precio,
        plano,
        inserted_at
    )
    VALUES (
        %(superficie_util)s,
        %(superficie_construida)s,
        %(habitaciones)s,
        %(precio)s,
        %(plano)s,
        %(inserted_at)s
    )
"""


def crear_tabla_viviendas(connection_string: str) -> None:
    """Crea la tabla de viviendas si todavia no existe."""
    create_table_sql = CREATE_TABLE_SQL_PATH.read_text(encoding="utf-8")
    with psycopg.connect(connection_string) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)


def insertar_viviendas(
    df: pd.DataFrame,
    connection_string: str,
) -> int:
    """Inserta en PostgreSQL las filas devueltas por obtener_viviendas_kyrenia."""
    if df.empty:
        return 0

    datos = _preparar_dataframe_para_insert(df)
    registros = datos.to_dict(orient="records")

    with psycopg.connect(connection_string) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, registros)

    return len(registros)


def _preparar_dataframe_para_insert(df: pd.DataFrame) -> pd.DataFrame:
    datos = df.rename(columns=COLUMN_MAPPING).copy()

    for columna in DB_COLUMNS:
        if columna not in datos.columns:
            datos[columna] = None

    datos = datos[DB_COLUMNS]
    datos["habitaciones"] = pd.to_numeric(datos["habitaciones"], errors="coerce").astype(
        "Int64"
    )
    datos["inserted_at"] = pd.to_datetime(datos["inserted_at"], errors="coerce")
    datos = datos.astype(object).where(pd.notna(datos), None)

    return datos
