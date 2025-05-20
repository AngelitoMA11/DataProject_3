import streamlit as st
import requests
import uuid
from config import AGENT_API_URL
import os

# Check authentication
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.warning("Por favor, inicia sesión para acceder al chat.")
    st.stop()

st.set_page_config(
    page_title="Chat Inteligente - Travel Planner",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Chat Inteligente")

# Add agent selector in the sidebar
with st.sidebar:
    st.title("Configuración")
    selected_agent = st.selectbox(
        "Selecciona el agente",
        ["Agente 1", "Agente 2"],
        index=0
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "reasoning" in msg and msg["reasoning"]:
            with st.expander("Ver cadena de razonamiento"):
                st.text(msg["reasoning"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu mensaje"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                agent_endpoint = "/chat2" if selected_agent == "Agente 2" else "/chat"
                res = requests.post(f"{API_URL}{agent_endpoint}", json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id,
                    "username": st.session_state.username  # Add username to the request
                })
                res.raise_for_status()
                result = res.json()
                reply = result["response"]
                reasoning = result["reasoning_chain"]
            except Exception as e:
                reply = f"❌ Error: {str(e)}"
                reasoning = ""

            st.markdown(reply)
            if reasoning:
                with st.expander("Ver cadena de razonamiento"):
                    st.text(reasoning)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": reply,
                "reasoning": reasoning
            }) 