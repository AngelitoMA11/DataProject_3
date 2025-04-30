import streamlit as st
import json
import requests
from datetime import date

st.set_page_config(
    page_title="Búsqueda de Vuelos - Travel Planner",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Búsqueda de Vuelos y Hoteles")

url_api = "http://api_data:8001/buscar/"  # URL del servicio de datos

with st.form("formulario_configuracion"):
    st.write("Responde a las siguientes preguntas:")

    col1, col2 = st.columns(2)
    
    with col1:
        ciudad_origen = st.text_input("¿Desde qué ciudad sales?", "Valencia")
        ciudad_destino_aeropuerto = st.text_input("¿Ciudad a la que viajas (aeropuerto)?", "Alicante")
        ciudad_destino_vacaciones = st.text_input("¿Ciudad a la que vas de vacaciones?", "Denia")
        
        fecha_salida = st.date_input("¿Cuál es la fecha de salida?", date(2025, 5, 5))
        fecha_vuelta = st.date_input("¿Cuál es la fecha de vuelta?", date(2025, 5, 13))
        
        rooms = st.number_input("¿Cuántas habitaciones quieres?", min_value=1, step=1, value=1)

    with col2:
        stops = st.selectbox("¿Cuántas escalas como máximo estás dispuesto a hacer?", ["none", "0", "1", "2"])
        adults = st.number_input("¿Cuántos adultos viajan?", min_value=1, step=1, value=1)
        children = st.text_input("¿Edades de los niños separados por coma? (Ej: 3,7 o 0 si no hay)", "1")
        cabin_class = st.selectbox("¿En qué clase quieres volar?", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
        currency = st.selectbox("¿En qué moneda quieres los precios?", ["EUR", "USD", "GBP"])

    submitted = st.form_submit_button("Buscar Vuelos y Hoteles")

    if submitted:
        fecha_salida_str = fecha_salida.strftime("%d-%m-%Y")
        fecha_vuelta_str = fecha_vuelta.strftime("%d-%m-%Y")

        config = {
            "ciudad_origen": ciudad_origen,
            "ciudad_destino_aeropuerto": ciudad_destino_aeropuerto,
            "ciudad_destino_vacaciones": ciudad_destino_vacaciones,
            "fecha_salida": fecha_salida_str,
            "fecha_vuelta": fecha_vuelta_str,
            "stops": stops,
            "adults": adults,
            "children": children,
            "cabin_class": cabin_class,
            "currency": currency,
            "rooms": rooms
        }

        st.subheader("Configuración de búsqueda:")
        st.json(config)

        with st.spinner("Buscando vuelos y hoteles..."):
            try:
                response = requests.post(url_api, json=config)
                if response.status_code == 200:
                    st.subheader("Resultados encontrados:")
                    st.json(response.json())
                else:
                    st.error(f"Error al buscar vuelos y hoteles: {response.status_code}")
            except Exception as e:
                st.error(f"Error de conexión: {str(e)}") 