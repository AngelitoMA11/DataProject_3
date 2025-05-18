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

base_url = os.environ.get("DATA_API_URL")
url_api = f"{base_url}/coches"  # Ajusta si el endpoint es otro

today = date.today()
default_departure = today + timedelta(days=7)
default_return = today + timedelta(days=14)

with st.form("flight_survey_form"):
    ciudad_origen = st.text_input("Ciudad de Origen (IATA)", "LHR")
    ciudad_destino = st.text_input("Ciudad de Destino (IATA)", "DEL")
    fecha_salida = st.date_input("Fecha de Salida", value=default_departure)
    fecha_vuelta = st.date_input("Fecha de Vuelta", value=default_return)

    submit_button = st.form_submit_button("Enviar Encuesta")

if submit_button:
    fecha_salida_str = fecha_salida.strftime("%-d-%-m-%Y")
    fecha_vuelta_str = fecha_vuelta.strftime("%-d-%-m-%Y")

    payload = {
        "ciudad_origen": ciudad_origen,
        "ciudad_destino": ciudad_destino,
        "fecha_salida": fecha_salida_str,
        "fecha_vuelta": fecha_vuelta_str,
    }

    st.subheader("📦 JSON enviado")
    st.code(json.dumps(payload, indent=2), language="json")

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
                st.json(response.json())
            else:
                st.error(f"Error al enviar la encuesta: {response.status_code}")
                st.text(response.text)
    except Exception as e:
        st.error(f"Error al procesar la encuesta: {str(e)}")
