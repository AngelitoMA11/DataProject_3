def buscador_alojamiento_agent(state):
    contexto = state.get("contexto_user", {})
    vuelo_elegido = state.get("vuelo_elegido", {})
    destino_elegido = contexto.get("destino_elegido", {})
    fechas = contexto.get("fechas", {})
    tipo_acompañante = contexto.get("acompañantes", "solo")

    # Mapear acompañantes a número de adultos
    if tipo_acompañante == "solo":
        adultos = 1
    elif tipo_acompañante == "pareja":
        adultos = 2
    elif tipo_acompañante == "familia":
        adultos = 2  # Puedes ajustar si quieres considerar niños
    else:
        adultos = 1

    if not destino_elegido:
        print("❌ Error: No hay destino elegido.")
        state["siguiente_agente"] = "recomendador_destinos_agent"
        return state

    ciudad = destino_elegido.get("ciudad_base", destino_elegido.get("nombre", ""))
    fecha_inicio = fechas.get("inicio")
    fecha_fin = fechas.get("fin")

    # Aquí llama directamente a buscar_alojamientos (la función que ya tienes)
    alojamientos = buscar_alojamientos(
        api_key_serpapi="2a6f69c74ec76ec1770b95c43601c5380fd53be9172899af533393c02a7dd2f8", 
        ciudad=ciudad, 
        fecha_inicio=fecha_inicio, 
        fecha_fin=fecha_fin, 
        adultos=adultos
    )

    if not alojamientos:
        print("⚠️ No se encontraron alojamientos.")
        state["siguiente_agente"] = "recomendador_alojamiento_agent"  # o maneja error
        return state

    # Mostrar opciones y que el usuario elija
    alojamiento_elegido = elegir_alojamiento(alojamientos)
    state["alojamiento_elegido"] = alojamiento_elegido
    state["siguiente_agente"] = "finalizador_agent"

    print(f"\n✅ Alojamiento seleccionado: {alojamiento_elegido.get('nombre', '---')}")
    return state