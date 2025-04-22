# archivo: generador_json_vuelo.py
import streamlit as st
import json
import requests
from datetime import date

url_api = "http://localhost:8000/buscar-vuelo/"  

st.title("Generador de configuración para búsqueda de vuelos")

with st.form("formulario_configuracion"):
    st.write("Responde a las siguientes preguntas:")
    
    ciudad_origen = st.text_input("¿Desde qué ciudad sales?", "valencia")
    ciudad_destino = st.text_input("¿A qué ciudad viajas?", "Barcelona")
    
    fecha_salida = st.date_input("¿Cuál es la fecha de salida?", date(2025, 4, 20))
    fecha_vuelta = st.date_input("¿Cuál es la fecha de vuelta?", date(2025, 4, 24))  # <- siempre obligatoria
    
    stops = st.selectbox("¿Cuántas escalas como máximo estás dispuesto a hacer?", ["none", "0", "1", "2"])
    
    adults = st.number_input("¿Cuántos adultos viajan?", min_value=1, step=1, value=1)
    
    children = st.text_input("¿Edades de los niños separados por coma? (Ej: 3,7 o 0 si no hay)", "1")
    
    cabin_class = st.selectbox("¿En qué clase quieres volar?", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
    
    currency = st.selectbox("¿En qué moneda quieres los precios?", ["EUR", "USD", "GBP"])
    
    submitted = st.form_submit_button("Generar JSON")

    if submitted:
        config = {
            "ciudad_origen": ciudad_origen,
            "ciudad_destino": ciudad_destino,
            "fecha_salida": str(fecha_salida),
            "fecha_vuelta": str(fecha_vuelta),
            "stops": stops,
            "adults": adults,
            "children": children,
            "cabin_class": cabin_class,
            "currency": currency
        }

        st.subheader("Configuración generada:")
        st.json(config)

        with open("config_vuelo.json", "w") as f:
            json.dump(config, f, indent=4)
        st.success("JSON guardado como 'config_vuelo.json'")

        response = requests.post(url_api, json=config)
        if response.status_code == 200:
            st.subheader("Resultados encontrados:")
            st.json(response.json())
        else:
            st.error(f"Error al buscar vuelos: {response.status_code}")
