def core_agent(state):
    user_input = state["mensaje_usuario"]

    # Si no hay campos faltantes, no hace falta invocar nada
    if "contexto_user" in state and not state["contexto_user"].get("campos_faltantes"):
        print("✅ Todos los campos ya están completos. core_agent no hace nada.")
        return state

    prompt = construir_prompt_core_agent(user_input)
    result = completar_datos_viaje_gemini(model, prompt)

    # Solo actualiza los campos faltantes, no sobrescribas todo el contexto si ya hay datos útiles
    if "contexto_user" in state:
        state["contexto_user"].update(result)
    else:
        state["contexto_user"] = result

    state["destino_determinado"] = result.get("destino_determinado", False)
    return state