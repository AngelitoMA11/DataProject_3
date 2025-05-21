import streamlit as st
import requests
import uuid
from config import DATA_API_URL

def sidebar():
    if not st.session_state.authenticated:
        menu = st.sidebar.radio("Selecciona una opción", ["Iniciar sesión", "Registrarse"])
        if menu == "Registrarse":
            registrarse()
        elif menu == "Iniciar sesión":
            iniciar_sesion()
    else:
        st.sidebar.subheader("Información Usuario")
        st.sidebar.markdown(f"""
            - **Usuario:** {st.session_state.usuario}
            - **Nombre:** {st.session_state.nombre}
            - **Apellidos:** {st.session_state.apellido}
            - **Mail:** {st.session_state.correo}
            - **ID:** {st.session_state.user_id}
        """)
        # Logout button
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.authenticated = False
            st.session_state.nombre = None
            st.session_state.apellido = None
            st.session_state.correo = None
            st.session_state.user_id = None
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()
        
        # Add new trip form in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("Tus Viajes")

        # Mostramos una lista de los viajes
        listar_viajes()

        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Nuevo Viaje")

        with st.sidebar.form("nuevo_viaje_form"):
            titulo = st.text_input("Título")     
            submitted = st.form_submit_button("Crear Viaje")
            
            if submitted and titulo:  # Moved outside the form context
                try:
                    response = requests.post(
                        f"{DATA_API_URL}/viajes",
                        json={
                            "titulo": titulo,
                            "user": st.session_state.usuario,
                            "thread_id": str(uuid.uuid4())
                        },
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    )
                    
                    if response.status_code == 200:
                        st.success("¡Viaje creado exitosamente!")
                        st.rerun()
                    else:
                        st.error(f"Error al crear el viaje: {response.text}")
                        
                except Exception as e:
                    st.error(f"Error al conectar con el servidor: {str(e)}")
            elif submitted and not titulo:
                st.error("Por favor, ingresa un título para el viaje")

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
                    f"{DATA_API_URL}/registro",
                    json={
                        "id": id,
                        "usuario": usuario,
                        "nombre": nombre,
                        "apellido": apellidos,
                        "correo": correo,
                        "PWD": password
                    }
                )
                st.info(response.text)
                    
                if response.status_code == 201:
                    st.session_state.authenticated = True
                    st.success("Usuario registrado")

                    st.session_state.usuario = usuario
                    st.session_state.nombre = nombre
                    st.session_state.apellido = apellidos
                    st.session_state.correo = correo
                    st.session_state.user_id = id

                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")

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
                response = requests.post(
                    f"{DATA_API_URL}/login",
                    json={
                        "usuario": username,
                        "pwd": password
                    }
                )
                st.info(response.text)
                
                if response.status_code == 200:
                    st.session_state.authenticated = True

                    user = response.json().get("user")
                    st.session_state.usuario = user['usuario']
                    st.session_state.nombre = user['nombre']
                    st.session_state.apellido = user['apellido']
                    st.session_state.correo = user['correo']
                    st.session_state.user_id = user['id']

                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
                    
            except Exception as e:
                st.error(f"Error al conectar con el servidor: {str(e)}")

def listar_viajes():
    try:
        response = requests.get(
            f"{DATA_API_URL}/viajes",
            params={
                "user": st.session_state.usuario
            }
        )
        
        if response.status_code == 200:
            viajes = response.json()
            if viajes:
                for viaje in viajes:
                    if st.sidebar.button(f"{viaje['titulo']}", use_container_width=True):
                        st.session_state.thread_id = viaje['thread_id']
                        st.session_state.messages = []
            else:
                st.sidebar.info("No tienes viajes guardados")
        else:
            st.sidebar.error(f"Error al obtener viajes: {response.text}")
            
    except Exception as e:
        st.sidebar.error(f"Error al conectar con el servidor: {str(e)}")