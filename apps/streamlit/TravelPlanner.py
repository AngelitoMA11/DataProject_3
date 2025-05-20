import uuid
import streamlit as st
import requests
from config import DATA_API_URL
from components.sidebar import sidebar
from components.chat import chat

# Page configuration
st.set_page_config(
    page_title="TravelPlanner",
    page_icon="✈️",
    layout="wide"
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'nombre' not in st.session_state:
    st.session_state.nombre = None
if 'apellido' not in st.session_state:
    st.session_state.apellido = None
if 'correo' not in st.session_state:
    st.session_state.correo = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# st.session_state.authenticated = True
# st.session_state.usuario = "admin"
# st.session_state.nombre = "admin"
# st.session_state.apellido = "admin"
# st.session_state.correo = "admin"
# st.session_state.user_id = "299da2ff-1c1b-4331-a18d-db009e1e42e6"

# Logo and Header
col1, col2 = st.columns([1, 4])
with col1:
    st.image("assets/logo.png", width=100)
with col2:
    st.title("TravelPlanner")

# Sidebar
sidebar()

# Main

if not st.session_state.thread_id:

    st.markdown("""
    ### Bienvenido al Travel Planner

    Esta aplicación te ayuda a planificar tus viajes de dos formas:

    1. 🤖 **Chat Inteligente**: Habla con nuestro asistente IA para planificar tu viaje de forma natural
    2. 📝 **Formulario de Búsqueda**: Usa nuestro formulario detallado para buscar vuelos y hoteles específicos

    Selecciona una opción en el menú lateral para comenzar.
    """)
    # No autenticado
    if not st.session_state.authenticated:
        st.warning("Por favor, inicia sesión para acceder a todas las funcionalidades.")

else:
    chat()