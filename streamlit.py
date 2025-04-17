import http.client
import urllib.parse
import json
import streamlit as st
from datetime import date

# === CONFIGURACIÓN DE ACCESO A LA API ===
RAPIDAPI_KEY = "9630d11b3dmshc21bd0426b9a53cp153093jsn46cfb50160a1"
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

headers = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': RAPIDAPI_HOST
}

def obtener_id_ciudad(nombre_ciudad):
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    query = urllib.parse.quote(nombre_ciudad)
    conn.request("GET", f"/api/v1/flights/searchDestination?query={query}", headers=headers)
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    
    for destino in data.get("data", []):
        if "AIRPORT" in destino["type"]:
            return destino["id"]
    return None

def buscar_vuelos(from_city, to_city, depart_date, return_date, stops, adults, children, cabin_class, currency):
    # Obtener los IDs de los aeropuertos
    from_id = obtener_id_ciudad(from_city)
    to_id = obtener_id_ciudad(to_city)
    
    if not from_id or not to_id:
        st.error("❌ No se encontró el ID de aeropuerto para alguna de las ciudades.")
        return None

    # Construir los parámetros para la consulta
    params = {
        "fromId": from_id,
        "toId": to_id,
        "departDate": depart_date,
        "stops": stops,
        "pageNo": "1",
        "adults": str(adults),
        "children": children,
        "cabinClass": cabin_class,
        "currency_code": currency
    }
    if return_date:
        params["returnDate"] = return_date

    query_string = urllib.parse.urlencode(params)
    endpoint = f"/api/v1/flights/searchFlights?{query_string}"

    # Realizar la petición a la API
    conn = http.client.HTTPSConnection(RAPIDAPI_HOST)
    conn.request("GET", endpoint, headers=headers)
    respuesta = conn.getresponse().read().decode("utf-8")
    vuelos = json.loads(respuesta)
    
    return vuelos

# --- Interfaz de Streamlit ---
st.title("Buscador de Vuelos")

with st.form("flight_search_form"):
    # Entradas para las ciudades y fechas
    ciudad_origen = st.text_input("Ciudad de origen", "Valencia")
    ciudad_destino = st.text_input("Ciudad de destino", "London")
    fecha_salida = st.date_input("Fecha de salida", date.today())
    fecha_vuelta = st.date_input("Fecha de vuelta (opcional)", date.today(), help="Si es viaje de ida y vuelta, selecciona la fecha. Si no, ignora este campo.")

    # Otras opciones
    stops = st.selectbox("Paradas", options=["none", "0", "1", "2"], index=0)
    adults = st.number_input("Número de adultos", min_value=1, value=1)
    children = st.text_input("Niños (edades separadas por comas o '0' si ninguno)", "0")
    cabin_class = st.selectbox("Clase", options=["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"], index=0)
    currency = st.text_input("Moneda", "EUR")

    submitted = st.form_submit_button("Buscar vuelos")

if submitted:
    # Convertir las fechas a cadena con formato YYYY-MM-DD
    depart_date_str = fecha_salida.strftime("%Y-%m-%d")
    # Se puede interpretar la fecha de vuelta como opcional
    return_date_str = fecha_vuelta.strftime("%Y-%m-%d") if fecha_vuelta and fecha_vuelta != fecha_salida else None

    st.info("Consultando vuelos...")
    vuelos = buscar_vuelos(ciudad_origen, ciudad_destino, depart_date_str, return_date_str, stops, adults, children, cabin_class, currency)
    
    if vuelos:
        st.success("Resultados obtenidos:")
        st.json(vuelos)
    else:
        st.error("No se pudieron obtener resultados. Verifica que los datos ingresados sean correctos.")
