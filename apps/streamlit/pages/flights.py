import streamlit as st
import json
import requests
import os
from datetime import date, timedelta

st.set_page_config(
    page_title="Encuesta de Datos de Vuelo",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Encuesta de Datos de Vuelo")

base_url = os.environ.get("DATA_API_URL")  # Asumo que necesitas esto para enviar los resultados
url_api = f"{base_url}/vuelos"  #  Ajusta la URL si es diferente

today = date.today()
default_departure = today + timedelta(days=7)
default_return = today + timedelta(days=14)

with st.form("flight_survey_form"):
    col1, col2 = st.columns(2)

    with col1:
        ciudad_origen = st.text_input("Ciudad de Origen (IATA)", "LHR")
        ciudad_destino = st.text_input("Ciudad de Destino (IATA)", "DEL")
        fecha_salida = st.text_input("Fecha de Salida", str(default_departure))
        fecha_vuelta = st.text_input("Fecha de Vuelta", str(default_return))

    with col2:
        adults = st.number_input("Número de Adultos", min_value=1, max_value=9, value=1)
        cabin_class = st.selectbox("Clase de Cabina", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"], index=0)
        tipo_de_viaje = st.selectbox("Tipo de Viaje", ["Ida y Vuelta", "Solo Ida"], index=0)

    submit_button = st.form_submit_button("Enviar Encuesta")

if submit_button:
    # Transformar la selección del tipo de viaje al formato numérico
    tipo_de_viaje_num = 1 if tipo_de_viaje == "Ida y Vuelta" else 2

    # Prepare the payload
    payload = {
        "ciudad_origen": ciudad_origen,
        "ciudad_destino": ciudad_destino,
        "fecha_salida": fecha_salida,
        "fecha_vuelta": fecha_vuelta,
        "adults": int(adults),  # Asegurar que 'adults' sea un entero
        "cabin_class": cabin_class,
        "tipo_de_viaje": tipo_de_viaje_num,
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        with st.spinner("Enviando datos de la encuesta..."):
            response = requests.post(
                url=url_api,
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                st.success("¡Encuesta enviada exitosamente!")
                st.json(response.json())  # Mostrar la respuesta del servidor (opcional)
            else:
                st.error(f"Error al enviar la encuesta: {response.status_code}")
                st.text(response.text)
    except Exception as e:
        st.error(f"Error al procesar la encuesta: {str(e)}")