import streamlit as st

st.set_page_config(
    page_title="Travel Planner",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Travel Planner 🌴")

st.markdown("""
### Bienvenido al Travel Planner

Esta aplicación te ayuda a planificar tus viajes de dos formas:

1. 🤖 **Chat Inteligente**: Habla con nuestro asistente IA para planificar tu viaje de forma natural
2. 📝 **Formulario de Búsqueda**: Usa nuestro formulario detallado para buscar vuelos y hoteles específicos

Selecciona una opción en el menú lateral para comenzar.
""")

# Sidebar navigation
st.sidebar.title("Navegación")
st.sidebar.markdown("""
- [Chat Inteligente](/pages/chat.py)
- [Búsqueda de Vuelos](/pages/flights.py)
""")
