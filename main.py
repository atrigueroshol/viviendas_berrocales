import os

from database import crear_tabla_viviendas, insertar_viviendas
from scraper import DEFAULT_URL, obtener_viviendas_kyrenia


def main() -> None:
    connection_string = _obtener_database_url()

    df = obtener_viviendas_kyrenia(DEFAULT_URL, headless=True)
    print(df)

    crear_tabla_viviendas(connection_string)
    filas_insertadas = insertar_viviendas(df, connection_string)
    print(f"Filas insertadas en PostgreSQL: {filas_insertadas}")


def _obtener_database_url() -> str:
    connection_string = os.getenv("DATABASE_URL", "").strip().strip("\"'")
    if not connection_string:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL.")

    connection_string = connection_string.replace("postgresql=//", "postgresql://", 1)
    connection_string = connection_string.replace("postgres=//", "postgres://", 1)

    if not connection_string.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            "DATABASE_URL no tiene formato valido. Debe empezar por "
            "'postgresql://' o 'postgres://'. Revisa el secret en GitHub Actions."
        )

    return connection_string


if __name__ == "__main__":
    main()
