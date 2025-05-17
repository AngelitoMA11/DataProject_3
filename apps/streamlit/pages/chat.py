import streamlit as st
import requests
import uuid
import os

st.set_page_config(
    page_title="Chat Inteligente - Travel Planner",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Chat Inteligente")

API_URL = os.environ.get("AGENT_API_URL")
print(API_URL)


# Add a button to view the graph in the sidebar
with st.sidebar:
    st.title("Visualización")
    if st.button("Ver flujo del agente"):
        try:
            response = requests.get(f"{API_URL}/graph")
            if response.status_code == 200:
                st.image(response.content, caption="Flujo de trabajo del agente", use_column_width=True)
            else:
                st.error("Error al cargar el grafo")
        except Exception as e:
            st.error(f"Error: {str(e)}")

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
                res = requests.post(f"{API_URL}/chat", json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id
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