from __future__ import annotations

from typing import Iterable

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_URL = (
    "https://www.aedashomes.com/"
    "pisos-en-venta-en-berrocales-obra-nueva-kyrenia"
)

EXPECTED_COLUMNS = [
    "Superficie útil",
    "Superficie construida",
    "Habitaciones",
    "Precio",
    "Plano",
    "inserted_at",
]


def obtener_viviendas_kyrenia(
    url: str = DEFAULT_URL,
    headless: bool = True,
    timeout: int = 30,
    driver: WebDriver | None = None,
) -> pd.DataFrame:
    """Extrae la tabla 'Elige la casa que quieres' y la devuelve como DataFrame."""
    inserted_at = pd.Timestamp.now()
    own_driver = driver is None
    if driver is None:
        driver = _crear_driver(headless=headless)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, timeout)
        _aceptar_cookies(driver, timeout=8)
        _esperar_seccion_viviendas(driver, wait)

        seccion = _obtener_seccion_viviendas(driver)
        filas = _extraer_filas_desde_tabla(seccion)
        if not filas:
            filas = _extraer_filas_desde_bloques(seccion)

        df = pd.DataFrame(filas)
        if df.empty:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

        df = _normalizar_columnas(df)
        df["inserted_at"] = inserted_at
        return df.reindex(columns=EXPECTED_COLUMNS)
    finally:
        if own_driver:
            driver.quit()


def _crear_driver(headless: bool = True) -> WebDriver:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


def _aceptar_cookies(driver: WebDriver, timeout: int = 8) -> None:
    textos = ("Aceptar", "Acepto", "Aceptar todas", "Accept", "Allow all")
    xpath = " | ".join(
        f"//button[contains(normalize-space(.), '{texto}')]"
        for texto in textos
    )
    try:
        boton = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        try:
            boton.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", boton)
    except TimeoutException:
        pass


def _esperar_seccion_viviendas(driver: WebDriver, wait: WebDriverWait) -> None:
    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(.), 'Elige la casa que quieres')]",
            )
        )
    )
    driver.execute_script(
        """
        const node = [...document.querySelectorAll('h1,h2,h3,h4,[role="heading"],div,span')]
          .find(el => (el.innerText || '').includes('Elige la casa que quieres'));
        if (node) node.scrollIntoView({block: 'center'});
        """
    )
    wait.until(
        lambda d: "Superficie" in _obtener_seccion_viviendas(d).text
        and "Precio" in _obtener_seccion_viviendas(d).text
    )


def _obtener_seccion_viviendas(driver: WebDriver):
    return driver.execute_script(
        """
        const heading = [...document.querySelectorAll('h1,h2,h3,h4,[role="heading"],div,span')]
          .find(el => (el.innerText || '').includes('Elige la casa que quieres'));

        if (!heading) {
          throw new Error('No se encontro el apartado "Elige la casa que quieres".');
        }

        let node = heading;
        while (node && node !== document.body) {
          const text = node.innerText || '';
          if (text.includes('Superficie') && text.includes('Precio')) {
            return node;
          }
          node = node.parentElement;
        }
        return heading.parentElement;
        """
    )


def _extraer_filas_desde_tabla(seccion) -> list[dict[str, str]]:
    tablas = seccion.find_elements(By.TAG_NAME, "table")
    for tabla in tablas:
        cabeceras = [
            celda.text.strip()
            for celda in tabla.find_elements(By.CSS_SELECTOR, "thead th, thead td")
            if celda.text.strip()
        ]
        filas = []
        for tr in tabla.find_elements(By.CSS_SELECTOR, "tbody tr, tr"):
            celdas = tr.find_elements(By.CSS_SELECTOR, "th, td")
            if len(celdas) < 2:
                continue

            valores = [_texto_o_enlace(celda) for celda in celdas]
            if cabeceras and valores == cabeceras:
                continue

            if cabeceras and len(cabeceras) == len(valores):
                filas.append(dict(zip(cabeceras, valores)))
            else:
                filas.append(_fila_por_posicion(valores))

        if filas:
            return filas
    return []


def _extraer_filas_desde_bloques(seccion) -> list[dict[str, str]]:
    candidatos = seccion.find_elements(
        By.XPATH,
        ".//*[contains(., 'Superficie') and contains(., 'Precio') and "
        "(contains(., 'Habitaciones') or contains(., 'Habitacion'))]",
    )
    filas = []
    textos_vistos = set()

    for candidato in candidatos:
        texto = " ".join(candidato.text.split())
        if not texto or texto in textos_vistos:
            continue
        textos_vistos.add(texto)

        partes = _valores_por_etiqueta(
            texto,
            [
                "Superficie útil",
                "Superficie construida",
                "Habitaciones",
                "Precio",
                "Plano",
            ],
        )
        if partes:
            filas.append(partes)

    return filas


def _texto_o_enlace(celda) -> str:
    enlaces = celda.find_elements(By.TAG_NAME, "a")
    if enlaces:
        href = enlaces[0].get_attribute("href")
        if href:
            return href.strip()
    return " ".join(celda.text.split())


def _fila_por_posicion(valores: Iterable[str]) -> dict[str, str]:
    return {
        columna: valor
        for columna, valor in zip(EXPECTED_COLUMNS, valores)
    }


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    renombrado = {
        columna: _normalizar_nombre_columna(str(columna))
        for columna in df.columns
    }
    df = df.rename(columns=renombrado)

    for columna in EXPECTED_COLUMNS:
        if columna not in df.columns:
            df[columna] = None

    return df


def _normalizar_nombre_columna(nombre: str) -> str:
    nombre_limpio = " ".join(nombre.replace("\n", " ").split()).strip(": ")
    equivalencias = {
        "Superficie útil": "Superficie útil",
        "Superficie util": "Superficie útil",
        "Sup. util": "Superficie útil",
        "Superficie construida": "Superficie construida",
        "Sup. construida": "Superficie construida",
        "Habitaciones": "Habitaciones",
        "Dormitorios": "Habitaciones",
        "Precio": "Precio",
        "Plano": "Plano",
    }
    return equivalencias.get(nombre_limpio, nombre_limpio)


def _valores_por_etiqueta(texto: str, etiquetas: list[str]) -> dict[str, str]:
    texto_normalizado = (
        texto.replace("Superficie util", "Superficie útil")
        .replace("Sup. útil", "Superficie útil")
        .replace("Sup. util", "Superficie útil")
        .replace("Sup. construida", "Superficie construida")
        .replace("Dormitorios", "Habitaciones")
    )

    indices = []
    for etiqueta in etiquetas:
        posicion = texto_normalizado.find(etiqueta)
        if posicion >= 0:
            indices.append((posicion, etiqueta))
    indices.sort()

    if len(indices) < 3:
        return {}

    resultado = {}
    for i, (posicion, etiqueta) in enumerate(indices):
        inicio = posicion + len(etiqueta)
        fin = indices[i + 1][0] if i + 1 < len(indices) else len(texto_normalizado)
        valor = texto_normalizado[inicio:fin].strip(" :")
        if valor:
            resultado[etiqueta] = valor

    return resultado
