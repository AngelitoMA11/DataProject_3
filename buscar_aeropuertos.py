# archivo: buscar_aeropuertos.py
import httpx
import urllib.parse
import os

RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

def buscar_aeropuertos(ciudad: str):
    query = urllib.parse.quote(ciudad)
    url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchDestination?query={query}"

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json().get("data", [])

            print(f"\nAeropuertos encontrados para '{ciudad}':\n")
            encontrados = False
            for item in data:
                if "AIRPORT" in item.get("type", ""):
                    print(f"Nombre: {item.get('name')}")
                    print(f"ID:     {item.get('id')}")
                    print(f"IATA:   {item.get('iataCode')}")
                    print("-" * 40)
                    encontrados = True
            if not encontrados:
                print("No se encontraron aeropuertos.")
    except Exception as e:
        print(f"Error al buscar aeropuertos: {e}")

if __name__ == "__main__":
    ciudad = input("Introduce el nombre de la ciudad: ")
    buscar_aeropuertos(ciudad)

# archivo: buscar_aeropuertos.py
import httpx
import urllib.parse
import os

RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

def buscar_aeropuerto_principal(ciudad: str):
    query = urllib.parse.quote(ciudad)
    url = f"https://{RAPIDAPI_HOST}/api/v1/flights/searchDestination?query={query}"

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json().get("data", [])

            for item in data:
                if item.get("type") == "AIRPORT" and item.get("cityName", "").lower() == ciudad.lower():
                    print(f"\nAeropuerto principal para '{ciudad}':")
                    print(f"Nombre: {item.get('name')}")
                    print(f"ID:     {item.get('id')}")
                    print(f"IATA:   {item.get('iataCode')}")
                    return

            print(f"\n⚠️ No se encontró un aeropuerto principal para '{ciudad}' con coincidencia exacta.")
            print("Mostrando otros resultados relacionados:\n")
            for item in data:
                if "AIRPORT" in item.get("type", ""):
                    print(f"Nombre: {item.get('name')}")
                    print(f"ID:     {item.get('id')}")
                    print(f"IATA:   {item.get('iataCode')}")
                    print("-" * 40)

    except Exception as e:
        print(f"Error al buscar aeropuertos: {e}")

if __name__ == "__main__":
    ciudad = input("Introduce el nombre de la ciudad: ")
    buscar_aeropuerto_principal(ciudad)
