def recomendador_destinos_agent(state: ViajeState) -> ViajeState:
    debug_logger("recomendador_destinos_agent", state, "Ejecutando bucle de recomendación...")

    # 🛡️ Protegemos acceso al contexto
    contexto = state.get("contexto_user", {})
    if not contexto:
        print("⚠️ No hay contexto aún. Volviendo al core_agent.")
        state["siguiente_agente"] = "core_agent"
        return state

    contexto_actualizado = loop_recomendacion_y_feedback(model, contexto)
    state["contexto_user"] = contexto_actualizado

    if "destino_elegido" in contexto_actualizado:
        state["destino_determinado"] = True
        state["siguiente_agente"] = "buscador_vuelos_agent"
    else:
        state["siguiente_agente"] = "recomendador_destinos_agent"

    return state
