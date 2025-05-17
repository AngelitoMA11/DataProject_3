def completar_gemini(prompt: str) -> str:
    print("⏳ Enviando prompt al modelo...")
    try:
        response = model.generate_content(prompt)
        print("✅ Respuesta recibida del modelo")
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error al invocar el modelo: {e}")
        return ""


def coordinador_agent(state: dict) -> dict:
    # Detectar error en buscador_vuelos_agent para evitar bucles
    error = state.get("error_agente", False)
    ultimo_agente = state.get("ultimo_agente", None)

    if error and ultimo_agente == "buscador_vuelos_agent":
        print("⚠️ Detectado error en buscador_vuelos_agent, redirigiendo a recomendador_destinos_agent")
        state["error_agente"] = False  # Reset para evitar bucles
        state["siguiente_agente"] = "recomendador_destinos_agent"
        return state

    print("🧭 Analizando estado para decidir siguiente agente...")

    prompt = f"""
Eres un agente coordinador experto en un sistema de planificación de viajes multi-agente.

Tu trabajo es analizar el estado del viaje (`state`) y decidir qué agente debe actuar a continuación. 

Tienes cinco opciones:

- core_agent → si FALTAN campos importantes del viaje (presupuesto, fechas, ciudad origen, etc.)
- recomendador_destinos_agent → si el usuario no ha elegido aún un destino
- buscador_vuelos_agent → si ya hay un destino definido y se pueden buscar vuelos
- buscador_alojamiento_agent → si ya hay un vuelo confirmado y falta buscar alojamiento
- END → si todos los pasos han sido completados

⚠️ INSTRUCCIONES CLAVE:
- Si el campo `contexto_user["campos_faltantes"]` está vacío, NO LLAMES a `core_agent`.
- Si el campo `destino_determinado` es False, llama a `recomendador_destinos_agent`.
- Si el campo `destino_determinado` es True y NO hay vuelo aún, llama a `buscador_vuelos_agent`.
- Si ya hay vuelo y destino, pero falta alojamiento, llama a `buscador_alojamiento_agent`.
- Si ya hay destino, vuelo y alojamiento, llama a `END`.

NO EXPLIQUES TU ELECCIÓN. NO INCLUYAS TEXTO EXTRA. RESPONDE SOLO con el nombre del agente.

---

🧾 Estado actual del viaje:
{json.dumps(state, indent=2, ensure_ascii=False)}

🗣️ Último mensaje del usuario:
"{state.get("mensaje_usuario", "")}"

¿Qué agente debe ejecutarse ahora?
RESPONDE SOLO con el nombre del agente.
"""

    siguiente = completar_gemini(prompt).strip()

    agentes_validos = [
        "core_agent",
        "recomendador_destinos_agent",
        "buscador_vuelos_agent",
        "buscador_alojamiento_agent",
        "END"
    ]
    if siguiente not in agentes_validos:
        print(f"⚠️ El modelo respondió un valor inválido o vacío: '{siguiente}'. Usando fallback a 'core_agent'.")
        siguiente = "core_agent"

    print(f"🤖 Modelo ha decidido llamar a: {siguiente}")
    state["siguiente_agente"] = siguiente

        # Aquí añadimos la llamada al resumen final:
    if siguiente == "END":
        print("\n📋 Generando resumen final del viaje para el usuario...\n")
        resumen_final_viaje(state)  # Esta función imprime el resumen
    return state