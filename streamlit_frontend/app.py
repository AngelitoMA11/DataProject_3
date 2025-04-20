import streamlit as st
import requests
import uuid

API_URL = "http://api_agent:8000/chat"  # Nombre del servicio del contenedor FastAPI

st.set_page_config(page_title="Gemini Chat", layout="wide")
st.title("🤖 Travel Planner 🛩️🌴")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu mensaje"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                res = requests.post(API_URL, json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id
                })
                res.raise_for_status()
                reply = res.json()["response"]
            except Exception as e:
                reply = f"❌ Error: {str(e)}"

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
