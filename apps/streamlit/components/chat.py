import streamlit as st
import requests
from config import AGENT_API_URL

def importar_mensajes():
    res = requests.get(f"{AGENT_API_URL}/messages",
        params={
            "thread_id": st.session_state.thread_id
        }
    )
    res.raise_for_status()
    return res.json()

def chat():

    if st.session_state.messages == []:
        st.session_state.messages = importar_mensajes()

    # Add agent selector in the sidebar
    with st.sidebar:
        st.write(st.session_state.thread_id)

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
                    res = requests.post(f"{AGENT_API_URL}/chat", json={
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