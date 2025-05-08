#!/usr/bin/env python3
"""
Script para obtener el JSON completo de resultados de búsqueda en Rome2Rio
usando Selenium para renderizar la página y extraer el blob de datos
incrustado en el script de Next.js (`__NEXT_DATA__`).

Se navega directamente a la URL de mapa con origen y destino en la ruta,
lo que evita tener que interactuar con los inputs de la página principal.

Uso:
  python api_renfe.py  # Usa valores predefinidos
  python api_renfe.py ["Origen"] ["Destino"]  # Opcionalmente se pueden pasar argumentos
"""
import json
import sys
import traceback
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Valores predeterminados para origen y destino
DEFAULT_ORIGEN = "Valencia, España"
DEFAULT_DESTINO = "Sídney, Australia"


def slugify_location(name: str) -> str:
    """
    Convierte el nombre de ubicación en slug para la URL de Rome2Rio:
    - Reemplaza comas y espacios por guiones
    - Codifica caracteres especiales con percent-encoding
    """
    # Solo tomamos hasta la primera coma para destinos (por ej. "Sídney, Australia" -> "Sídney")
    primary = name.split(',')[0]
    # Reemplazamos comas y espacios
    slug = primary.replace(', ', '-').replace(' ', '-')
    # Percent-encode sin tocar los guiones
    return quote(slug, safe='-')


def scrape_search_json(origin: str, destination: str) -> dict:
    """
    Navega directamente a la URL de mapa y extrae el JSON incrustado en __NEXT_DATA__.
    """
    # Construir slugs para la ruta
    origin_slug = slugify_location(origin)
    destination_slug = slugify_location(destination)
    url = f"https://rome2rio.com/es/map/{origin_slug}/{destination_slug}"

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        # Esperar a que el script __NEXT_DATA__ esté presente
        wait.until(EC.presence_of_element_located((By.ID, '__NEXT_DATA__')))
        # Extraer y parsear el JSON
        script = driver.find_element(By.ID, '__NEXT_DATA__').get_attribute('textContent')
        return json.loads(script)
    finally:
        driver.quit()


if __name__ == '__main__':
    # Determinar origen y destino (args o predeterminados)
    if len(sys.argv) == 3:
        origen, destino = sys.argv[1], sys.argv[2]
    else:
        origen, destino = DEFAULT_ORIGEN, DEFAULT_DESTINO
        print(
            f"Usando valores predeterminados: Origen='{origen}', Destino='{destino}'",
            file=sys.stderr
        )

    try:
        result = scrape_search_json(origen, destino)
        # Extraer solo la sección 'search' si existe
        search_data = (
            result.get('props', {})
                  .get('pageProps', {})
                  .get('search')
        )
        if search_data is not None:
            print(json.dumps(search_data, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        error = {
            'error': str(e),
            'traceback': traceback.format_exc().splitlines()
        }
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)
