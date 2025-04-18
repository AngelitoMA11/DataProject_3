import streamlit as st
from datetime import date
import sys
import os
import traceback

# Añadir el directorio actual al path para importar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from hotel_raul2 import main as buscar_hoteles_api

# --- Interfaz de Streamlit ---
st.title("Buscador de Viajes")

with st.form("travel_search_form"):
    # Campos de origen y destino
    col1, col2 = st.columns(2)
    with col1:
        ciudad_origen = st.text_input("Ciudad de origen", "Madrid")
    with col2:
        ciudad_destino = st.text_input("Ciudad de destino", "London")
    
    # Fechas
    col3, col4 = st.columns(2)
    with col3:
        fecha_entrada = st.date_input("Fecha de ida", date.today())
    with col4:
        fecha_salida = st.date_input("Fecha de vuelta", date(2025, 4, 25))
    
    # Otras opciones
    col5, col6 = st.columns(2)
    with col5:
        adultos = st.number_input("Número de adultos", min_value=1, value=1)
    with col6:
        habitaciones = st.number_input("Número de habitaciones", min_value=1, value=1)
    
    # Pestañas para buscar hoteles o vuelos
    buscar_hoteles = st.checkbox("Buscar hoteles", value=True)
    buscar_vuelos = st.checkbox("Buscar vuelos", value=False)
    
    submitted = st.form_submit_button("Buscar")

if submitted:
    # Validar que se haya ingresado origen y destino
    if not ciudad_origen:
        st.error("Por favor, ingrese una ciudad de origen.")
    elif not ciudad_destino:
        st.error("Por favor, ingrese una ciudad de destino.")
    else:
        # Convertir fechas a cadena con formato YYYY-MM-DD
        fecha_entrada_str = fecha_entrada.strftime("%Y-%m-%d")
        fecha_salida_str = fecha_salida.strftime("%Y-%m-%d")
        
        # Validar fechas
        if fecha_entrada >= fecha_salida:
            st.error("La fecha de ida debe ser anterior a la fecha de vuelta.")
        else:
            # Buscar hoteles si se ha marcado la casilla
            if buscar_hoteles:
                st.subheader("Resultados de Hoteles")
                with st.spinner('Buscando hoteles...'):
                    # Mostrar los parámetros para depuración
                    with st.expander("Ver parámetros de búsqueda"):
                        st.write(f"Origen: {ciudad_origen}")
                        st.write(f"Destino: {ciudad_destino}")
                        st.write(f"Fecha ida: {fecha_entrada_str}")
                        st.write(f"Fecha vuelta: {fecha_salida_str}")
                        st.write(f"Adultos: {adultos}")
                        st.write(f"Habitaciones: {habitaciones}")
                    
                    # Llamar a la función principal con parámetros (incluyendo origen aunque no se use ahora)
                    hoteles = buscar_hoteles_api(
                        origen=ciudad_origen,
                        ciudad=ciudad_destino,
                        entrada=fecha_entrada_str,
                        salida=fecha_salida_str,
                        num_adultos=adultos,
                        num_habitaciones=habitaciones
                    )
                    
                    # Procesar resultados
                    if hoteles:
                        if "error" in hoteles:
                            st.error(f"Error: {hoteles['error']}")
                            st.warning("Detalles del error disponibles en la consola. Verifica los logs para más información.")
                        else:
                            # Verificar si hay un mensaje informativo
                            if "info_message" in hoteles:
                                st.warning(hoteles["info_message"])
                                st.info("Prueba con otras fechas o una ciudad diferente.")
                            
                            # Extraer información de hoteles
                            hoteles_info = []
                            try:
                                lista_hoteles = hoteles.get('data', {}).get('hotels', [])
                                if lista_hoteles:
                                    for hotel in lista_hoteles:
                                        # Acceder a la información del hotel de manera segura
                                        hotel_prop = hotel.get('property', {})
                                        precio = hotel_prop.get('priceBreakdown', {}).get('grossPrice', {})
                                        hoteles_info.append({
                                            'Nombre': hotel_prop.get('name', 'N/A'),
                                            'Precio': f"{precio.get('value', 'N/A')} {precio.get('currency', '')}",
                                            'Puntuación': hotel_prop.get('reviewScore', 'N/A')
                                        })
                                    
                                    # Mostrar tabla de hoteles
                                    if hoteles_info:
                                        st.success(f"Se encontraron {len(hoteles_info)} hoteles")
                                        st.table(hoteles_info)
                                else:
                                    # Este mensaje solo se mostrará si no existe un info_message
                                    if "info_message" not in hoteles:
                                        st.warning("La API no devolvió hoteles. Prueba con otras fechas o una ciudad diferente.")
                                    
                                # Expandible para ver JSON completo
                                with st.expander("Ver respuesta completa de la API"):
                                    st.json(hoteles)
                            except Exception as e:
                                st.error(f"Error al procesar hoteles: {e}")
                                st.code(traceback.format_exc())
                    else:
                        st.error("No se pudo completar la búsqueda de hoteles. Verifica la conexión a internet y los parámetros.")
            
            # Buscar vuelos si se ha marcado la casilla
            if buscar_vuelos:
                st.subheader("Resultados de Vuelos")
                st.info("La búsqueda de vuelos estará disponible próximamente.")
                # Aquí irá la llamada a la API de vuelos cuando esté implementada