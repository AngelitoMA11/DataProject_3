import streamlit as st
import json
import hashlib
import os

# Ruta al archivo de usuarios
USER_FILE = "usuarios.json"

# Crear archivo si no existe
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({}, f)

# Función para cargar usuarios
def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)

# Guardar usuarios
def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Función para hashear contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Interfaz de usuario
st.title("🔐 Mi Cuenta de Viaje")

menu = st.sidebar.radio("Selecciona una opción", ["Iniciar sesión", "Registrarse"])

users = load_users()

if menu == "Registrarse":
    st.subheader("✍️ Registro de usuario")

    new_user = st.text_input("Nombre de usuario")
    new_pass = st.text_input("Contraseña", type="password")

    if st.button("Crear cuenta"):
        if new_user in users:
            st.error("⚠️ Ese usuario ya existe")
        else:
            users[new_user] = {
                "password": hash_password(new_pass),
                "viaje": {}  # vacía por ahora
            }
            save_users(users)
            st.success("✅ Usuario creado con éxito, ahora puedes iniciar sesión")

elif menu == "Iniciar sesión":
    st.subheader("🔑 Accede a tu cuenta")

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
