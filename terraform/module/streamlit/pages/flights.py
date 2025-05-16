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
        ciudad = st.text_input("Ciudad de destino (Nombre en inglés y país)", "Manchester, United Kingdom")
        fecha_entrada = st.text_input("Fecha de entrada", str(default_departure))
        fecha_vuelta = st.text_input("Fecha de vuelta", str(default_return))

    with col2:
        adults = st.number_input("Número de adultos", min_value=1, max_value=9, value=1)
        valoracion_numerica = st.slider("Valoración esperada (1 a 5)", min_value=1, max_value=5, value=4)

    submit_button = st.form_submit_button("Generar Payload")

if submit_button:
    # Mapear la valoración: 3 → 6, 4 → 8, 5 → 10
    valoracion_map = {1: "2", 2: "4", 3: "6", 4: "8", 5: "10"}
    valoracion = valoracion_map.get(valoracion_numerica, "8")  # Por defecto 8

    payload = {
        "ciudad": ciudad,
        "fecha_entrada": fecha_entrada,
        "fecha_vuelta": fecha_vuelta,
        "adults": adults,
        "valoración": valoracion
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