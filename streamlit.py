import streamlit as st
from datetime import date
import sys
import os
import json

# Añadir el directorio actual al path para importar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hotel_raul import buscar_destino_hotel, buscar_hoteles, guardar_json

# --- Interfaz de Streamlit ---
st.title("Buscador de Hoteles")

with st.form("hotel_search_form"):
    # Entradas para la búsqueda de hoteles
    ciudad_destino = st.text_input("Ciudad", "London")
    fecha_entrada = st.date_input("Fecha de llegada", date.today())
    fecha_salida = st.date_input("Fecha de salida", date.today())
    
    # Otras opciones
    adultos = st.number_input("Número de adultos", min_value=1, value=1)
    habitaciones = st.number_input("Número de habitaciones", min_value=1, value=1)
    
    submitted = st.form_submit_button("Buscar hoteles")

if submitted:
    # Convertir fechas a cadena con formato YYYY-MM-DD
    fecha_entrada_str = fecha_entrada.strftime("%Y-%m-%d")
    fecha_salida_str = fecha_salida.strftime("%Y-%m-%d")
    
    # Modificar variables globales en hotel_raul.py
    import hotel_raul
    hotel_raul.ciudad_destino = ciudad_destino
    hotel_raul.fecha_entrada = fecha_entrada_str
    hotel_raul.fecha_salida = fecha_salida_str
    hotel_raul.adults = adultos
    hotel_raul.rooms = habitaciones
    
    # Primero buscar el ID del destino
    st.info("Buscando destino...")
    dest_id, search_type = buscar_destino_hotel(ciudad_destino)
    
    if dest_id:
        st.info("Consultando hoteles...")
        
        # Buscar hoteles
        hoteles = buscar_hoteles(dest_id, search_type)
        
        if hoteles:
            # Guardar JSON
            guardar_json(hoteles, "hoteles_resultados.json")
            
            # Mostrar resultados
            st.success("Hoteles encontrados:")
            
            # Depuración: imprimir estructura completa de hoteles
            st.write("Estructura de datos completa:")
            st.json(hoteles)
            
            # Extraer hoteles de manera más robusta
            hoteles_info = []
            
            # Intentar diferentes formas de acceder a los hoteles
            try:
                # Método 1: Acceso directo
                lista_hoteles = hoteles.get('data', {}).get('hotels', [])
                
                # Si lista_hoteles está vacía, intentar otros métodos
                if not lista_hoteles:
                    # Método 2: Acceso a través de 'property'
                    lista_hoteles = [h.get('property', {}) for h in hoteles.get('data', {}).get('hotels', [])]
            
            except Exception as e:
                st.error(f"Error al procesar hoteles: {e}")
                lista_hoteles = []
            
            # Procesar lista de hoteles
            for hotel in lista_hoteles:
                try:
                    # Intentar diferentes formas de extraer información
                    nombre = hotel.get('name') or hotel.get('hotel_name', 'N/A')
                    
                    # Extraer precio
                    precio_info = hotel.get('priceBreakdown', {}).get('grossPrice', {})
                    precio = f"{precio_info.get('value', 'N/A')} {precio_info.get('currency', '')}"
                    
                    # Extraer puntuación
                    puntuacion = hotel.get('reviewScore', 'N/A')
                    
                    hoteles_info.append({
                        'Nombre': nombre,
                        'Precio': precio,
                        'Puntuación': puntuacion
                    })
                except Exception as e:
                    st.warning(f"No se pudo procesar un hotel: {e}")
            
            # Mostrar tabla de hoteles
            if hoteles_info:
                st.table(hoteles_info)
            else:
                st.warning("No se pudo extraer información de los hoteles.")
        else:
            st.error("No se encontraron hoteles.")
    else:
        st.error("No se pudo encontrar el destino.")