import streamlit as st
import json
import requests
from datetime import date

# URL de la API
url_api = "http://localhost:8000"

st.title("Buscador de Viajes - Hoteles y Vuelos")

# Crear un único formulario para todos los parámetros
with st.form("formulario_unificado"):
    st.header("Datos de viaje")
    
    # Parámetros compartidos
    ciudad_destino = st.text_input("¿A qué ciudad viajas?", "Barcelona")
    fecha_salida = st.date_input("¿Cuál es la fecha de salida?", date(2025, 4, 20))
    fecha_vuelta = st.date_input("¿Cuál es la fecha de vuelta?", date(2025, 4, 24))
    adults = st.number_input("¿Cuántos adultos viajan?", min_value=1, step=1, value=1)
    currency = st.selectbox("¿En qué moneda quieres los precios?", ["EUR", "USD", "GBP"])
    
    # Columnas para separar visualmente los parámetros específicos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Parámetros para vuelos")
        ciudad_origen = st.text_input("¿Desde qué ciudad sales?", "Valencia")
        stops = st.selectbox("¿Cuántas escalas como máximo?", ["none", "0", "1", "2"])
        children = st.text_input("¿Edades de los niños? (Ej: 3,7 o 0 si no hay)", "0")
        cabin_class = st.selectbox("¿En qué clase quieres volar?", ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"])
        buscar_vuelos = st.checkbox("Buscar vuelos", value=True)
    
    with col2:
        st.subheader("Parámetros para hoteles")
        rooms = st.number_input("¿Cuántas habitaciones necesitas?", min_value=1, step=1, value=1)
        buscar_hoteles = st.checkbox("Buscar hoteles", value=True)
    
    # Botón de submit unificado
    submitted = st.form_submit_button("Buscar")

# Área de resultados
if submitted:
    st.markdown("---")
    
    # Crear un JSON unificado con los criterios de búsqueda
    info_viaje = {
        "destino": ciudad_destino,
        "fechas": {
            "salida": str(fecha_salida),
            "regreso": str(fecha_vuelta)
        },
        "viajeros": {
            "adultos": adults,
            "niños": children if children != "0" else "No hay niños"
        },
        "moneda": currency
    }
    
    # Información específica de cada búsqueda
    resultados_vuelos = None
    resultados_hoteles = None
    
    # Procesar la búsqueda de vuelos
    if buscar_vuelos:
        # Configurar estructura de datos para vuelos
        config_vuelos = {
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
        
        # Agregar info de vuelos al JSON general
        info_viaje["vuelos"] = {
            "origen": ciudad_origen,
            "escalas_max": stops,
            "clase": cabin_class
        }
        
        # Guardar configuración en JSON
        with open("config_vuelos.json", "w") as f:
            json.dump(config_vuelos, f, indent=4)
        
        # Hacer solicitud a la API
        try:
            response = requests.post(f"{url_api}/buscar-vuelo/", json=config_vuelos)
            
            if response.status_code == 200:
                resultados_vuelos = response.json()
            else:
                st.error(f"Error al buscar vuelos: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            st.error(f"Error de conexión en búsqueda de vuelos: {e}")
    
    # Procesar la búsqueda de hoteles
    if buscar_hoteles:
        # Configurar estructura de datos para hoteles
        config_hoteles = {
            "ciudad_destino": ciudad_destino,
            "fecha_entrada": str(fecha_salida),
            "fecha_salida": str(fecha_vuelta),
            "adults": adults,
            "rooms": rooms,
            "currency": currency
        }
        
        # Agregar info de hoteles al JSON general
        info_viaje["hoteles"] = {
            "habitaciones": rooms
        }
        
        # Guardar configuración en JSON
        with open("config_hoteles.json", "w") as f:
            json.dump(config_hoteles, f, indent=4)
        
        # Hacer solicitud a la API
        try:
            response = requests.post(f"{url_api}/buscar-hotel/", json=config_hoteles)
            
            if response.status_code == 200:
                resultados_hoteles = response.json()
            else:
                st.error(f"Error al buscar hoteles: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            st.error(f"Error de conexión en búsqueda de hoteles: {e}")
    
    # Mostrar resumen del viaje
    st.header("Resumen de tu búsqueda")
    st.json(info_viaje)
    
    # Guardar información general del viaje
    with open("info_viaje.json", "w") as f:
        json.dump(info_viaje, f, indent=4)
    st.success("Información guardada como 'info_viaje.json'")
    
    # Mostrar resultados de vuelos
    if resultados_vuelos:
        st.header("Opciones de Vuelos")
        
        # Vuelos de ida
        st.subheader("Vuelos de Ida")
        if resultados_vuelos.get("ida") and isinstance(resultados_vuelos.get("ida"), list):
            for i, vuelo in enumerate(resultados_vuelos.get("ida", [])):
                with st.container():
                    cols = st.columns([3, 2, 2])
                    if isinstance(vuelo, dict):
                        with cols[0]:
                            st.write(f"**Opción {i+1}**")
                        with cols[1]:
                            st.write(f"**Aerolínea:** {vuelo.get('airline', 'N/A')}")
                        with cols[2]:
                            st.write(f"**Precio:** {vuelo.get('price', 'N/A')}")
                    else:
                        st.write(f"**Vuelo:** {vuelo}")
                    st.markdown("---")
        else:
            st.info("No se encontraron vuelos de ida")
        
        # Vuelos de vuelta
        if resultados_vuelos.get("vuelta") and isinstance(resultados_vuelos.get("vuelta"), list):
            st.subheader("Vuelos de Vuelta")
            for i, vuelo in enumerate(resultados_vuelos.get("vuelta", [])):
                with st.container():
                    cols = st.columns([3, 2, 2])
                    if isinstance(vuelo, dict):
                        with cols[0]:
                            st.write(f"**Opción {i+1}**")
                        with cols[1]:
                            st.write(f"**Aerolínea:** {vuelo.get('airline', 'N/A')}")
                        with cols[2]:
                            st.write(f"**Precio:** {vuelo.get('price', 'N/A')}")
                    else:
                        st.write(f"**Vuelo:** {vuelo}")
                    st.markdown("---")
    
    # Mostrar resultados de hoteles
    if resultados_hoteles:
        st.header("Opciones de Hoteles")
        hoteles = resultados_hoteles.get('data', {}).get('hotels', [])
        
        if hoteles and isinstance(hoteles, list):
            for i, hotel in enumerate(hoteles):
                with st.container():
                    if isinstance(hotel, dict):
                        cols = st.columns([3, 2, 2])
                        with cols[0]:
                            st.write(f"**{i+1}. {hotel.get('nombre', 'Hotel sin nombre')}**")
                        
                        precio = hotel.get('precio', {})
                        with cols[1]:
                            if isinstance(precio, dict):
                                st.write(f"**Precio:** {precio.get('valor', 'N/A')} {precio.get('moneda', '')}")
                            else:
                                st.write(f"**Precio:** {precio}")
                        
                        puntuacion = hotel.get('puntuacion', {})
                        with cols[2]:
                            if isinstance(puntuacion, dict):
                                st.write(f"**Puntuación:** {puntuacion.get('nota', 'N/A')}")
                            else:
                                st.write(f"**Puntuación:** {puntuacion}")
                    else:
                        st.write(f"**Hotel:** {hotel}")
                    st.markdown("---")
        else:
            st.info("No se encontraron hoteles para los criterios seleccionados")
    
    # Mostrar datos completos en expanders
    with st.expander("Ver datos completos de la búsqueda"):
        if resultados_vuelos:
            st.subheader("Datos completos de vuelos")
            st.json(resultados_vuelos)
        
        if resultados_hoteles:
            st.subheader("Datos completos de hoteles")
            st.json(resultados_hoteles)