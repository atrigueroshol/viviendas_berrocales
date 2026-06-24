import os

from database import DEFAULT_DATABASE_URL, crear_tabla_viviendas, insertar_viviendas
from scraper import DEFAULT_URL, obtener_viviendas_kyrenia


def main() -> None:
    connection_string = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    df = obtener_viviendas_kyrenia(DEFAULT_URL, headless=True)
    print(df)

    crear_tabla_viviendas(connection_string)
    filas_insertadas = insertar_viviendas(df, connection_string)
    print(f"Filas insertadas en PostgreSQL: {filas_insertadas}")


if __name__ == "__main__":
    main()
