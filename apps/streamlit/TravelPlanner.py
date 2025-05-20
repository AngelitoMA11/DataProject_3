import uuid
import streamlit as st
import requests
from config import DATA_API_URL

# Icono
st.logo("assets/logo.png")

st.set_page_config(
    page_title="Travel Planner",
    page_icon="✈️",
    layout="wide"
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

st.title("✈️ Travel Planner 🌴")

def registrarse():
    with st.sidebar.form("formulario_registro"):
        id = str(uuid.uuid4())
        usuario = st.text_input("Usuario")
        nombre = st.text_input("Nombre")
        apellidos = st.text_input("Apellidos")
        correo = st.text_input("Correo")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Crear cuenta")

        if submitted:
            try:
                response = requests.post(
                    f"{DATA_API_URL}/usuarios",
                    json={
                        "id": id,
                        "usuario": usuario,
                        "nombre": nombre,
                        "apellido": apellidos,
                        "correo": correo,
                        "pwd": password
                    }
                )
                st.info(response.text)
                    
                if response.status_code == 200:
                    st.session_state.user_id = id
                    st.session_state.authenticated = True
                    st.session_state.username = usuario
                    st.rerun()
                else:
                    st.error(f"Credenciales incorrectas: {response.text}")

            except Exception as e:
                st.error(f"Error al conectar con el servidor: {str(e)}")

def iniciar_sesion():
    with st.sidebar.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")
        
        if submitted:
            try:
                # Make authentication request
                response = requests.get(
                    f"{DATA_API_URL}/usuarios",
                    json={
                        "usuario": username,
                        "pwd": password
                    }
                )
                st.info(response.text)
                
                if response.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
                    
            except Exception as e:
                st.error(f"Error al conectar con el servidor: {str(e)}")

# Login form in sidebar
if not st.session_state.authenticated:
    st.sidebar.warning("Por favor, inicia sesión para acceder a todas las funcionalidades.")
    menu = st.sidebar.radio("Selecciona una opción", ["Iniciar sesión", "Registrarse"])
    if menu == "Registrarse":
        registrarse()

    elif menu == "Iniciar sesión":

        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión"):
            if username in users and users[username]["password"] == hash_password(password):
                st.success(f"Bienvenido, {username}")

                # Mostrar los datos del viaje
                viaje = users[username].get("viaje", {})
                if viaje:
                    st.markdown("### ✈️ Tu Planificación de Viaje")
                    for k, v in viaje.items():
                        st.markdown(f"**{k.capitalize()}**: {v}")
                else:
                    st.info("Todavía no tienes un viaje planificado")

            else:
                st.error("Usuario o contraseña incorrectos")
    
    
    
else:   
    # Add new trip form in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Crear Nuevo Viaje")
    
    with st.sidebar.form("nuevo_viaje_form"):
        thread_id = st.text_input("Thread ID")
        titulo = st.text_input("Título del Viaje")
        
        submitted = st.form_submit_button("Crear Viaje")
        
        if submitted:
            try:
                # Make POST request to the endpoint
                response = requests.post(
                    "xxx/viajes",
                    json={
                        "usuario": st.session_state.username,
                        "pwd": password,
                        "threadid": thread_id,
                        "titulo": titulo
                    }
                )
                
                if response.status_code == 200:
                    st.success("¡Viaje creado exitosamente!")
                else:
                    st.error(f"Error al crear el viaje: {response.text}")
                    
            except Exception as e:
                st.error(f"Error al conectar con el servidor: {str(e)}")
    
    # Logout button
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

# Main content
if st.session_state.authenticated:
    st.markdown("""
    ### Bienvenido al Travel Planner

    Esta aplicación te ayuda a planificar tus viajes de dos formas:

    1. 🤖 **Chat Inteligente**: Habla con nuestro asistente IA para planificar tu viaje de forma natural
    2. 📝 **Formulario de Búsqueda**: Usa nuestro formulario detallado para buscar vuelos y hoteles específicos

    Selecciona una opción en el menú lateral para comenzar.
    """)
else:
    st.markdown("""
    ### Bienvenido al Travel Planner
    
    Por favor, inicia sesión para acceder a todas las funcionalidades.
    """)
