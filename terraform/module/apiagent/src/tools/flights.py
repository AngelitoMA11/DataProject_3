import streamlit as st
import requests
import json
from src.config import DATA_API_URL
from datetime import datetime, timedelta

url = f"{DATA_API_URL}/vuelos"

st.set_page_config(
    page_title="Búsqueda de Vuelos",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Búsqueda de Vuelos")

# Default values
default_departure = (datetime.now() + timedelta(days=30)).strftime("%d-%m-%Y")
default_return = (datetime.now() + timedelta(days=37)).strftime("%d-%m-%Y")

# Form
with st.form("flight_search_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        ciudad_origen = st.text_input("Ciudad de Origen", "Valencia")
        ciudad_destino_aeropuerto = st.text_input("Aeropuerto de Destino", "Alicante")
        ciudad_destino_vacaciones = st.text_input("Ciudad de Vacaciones", "Denia")
        fecha_salida = st.text_input("Fecha de Salida", default_departure)
        fecha_vuelta = st.text_input("Fecha de Vuelta", default_return)
    
    with col2:
        stops = st.selectbox("Escalas", ["none", "1", "2"], index=0)
        adults = st.number_input("Adultos", min_value=1, max_value=9, value=1)
        children = st.number_input("Niños", min_value=0, max_value=9, value=1)
        cabin_class = st.selectbox("Clase", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"], index=0)
        currency = st.selectbox("Moneda", ["EUR", "USD", "GBP"], index=0)
        rooms = st.number_input("Habitaciones", min_value=1, max_value=5, value=1)

    submit_button = st.form_submit_button("Buscar Vuelos")

if submit_button:
    # Prepare the payload
    payload = {
        "ciudad_origen": ciudad_origen,
        "ciudad_destino_aeropuerto": ciudad_destino_aeropuerto,
        "ciudad_destino_vacaciones": ciudad_destino_vacaciones,
        "fecha_salida": fecha_salida,
        "fecha_vuelta": fecha_vuelta,
        "stops": stops,
        "adults": adults,
        "children": str(children),
        "cabin_class": cabin_class,
        "currency": currency,
        "rooms": rooms
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        with st.spinner("Buscando vuelos..."):
            response = requests.get(
                url=url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                st.success("¡Búsqueda completada!")
                st.json(result)
            else:
                st.error(f"Error en la búsqueda: {response.status_code}")
                st.text(response.text)
    except Exception as e:
        st.error(f"Error al realizar la búsqueda: {str(e)}") 