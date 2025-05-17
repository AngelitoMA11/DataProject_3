def buscador_vuelos_agent(state):
    contexto = state.get("contexto_user", {})
    print("🔍 Contexto recibido en buscador_vuelos_agent:", contexto)

    origen = contexto.get("iata_origen")
    destino = contexto.get("destino_elegido", {}).get("iata")
    fecha_ida = contexto.get("fechas", {}).get("inicio")
    fecha_vuelta = contexto.get("fechas", {}).get("fin")

    # Fallbacks extra por si alguno es None
    if not origen:
        origen = contexto.get("ciudad_origen", "").strip()
    if not destino:
        destino = contexto.get("destino_elegido", {}).get("ciudad_base", "").strip()
    if not fecha_ida:
        fecha_ida = "2025-06-01"  # fallback temporal solo para debug

    # 💥 DEBUG fuerte
    print("📌 Validando campos requeridos...")
    print(f"  ➤ origen: {origen} ({type(origen)})")
    print(f"  ➤ destino: {destino} ({type(destino)})")
    print(f"  ➤ fecha_ida: {fecha_ida} ({type(fecha_ida)})")
    print(f"  ➤ fecha_vuelta: {fecha_vuelta} ({type(fecha_vuelta)})")
    print(f"  ➤ all(...) = {all([origen, destino, fecha_ida])}")

    if not all([origen, destino, fecha_ida]):
        print("❌ Faltan datos obligatorios para buscar vuelos (origen, destino, fecha_ida).")
        print("🛠️ Corrige el formato del estado o revisa el contenido en contexto_user.")
        state["siguiente_agente"] = "recomendador_destinos_agent"
        return state

    # ✅ Datos listos
    vuelos = obtener_vuelos_serpapi(origen, destino, fecha_ida, fecha_vuelta, api_key_serpapi)

    if not vuelos:
        print("⚠️ No se encontraron vuelos. Puedes probar otro destino o ajustar fechas.")
        state["siguiente_agente"] = "recomendador_destinos_agent"
        return state

    vuelo_elegido = mostrar_opciones_vuelos(vuelos)

    if not vuelo_elegido:
        print("❌ No se seleccionó ningún vuelo.")
        state["siguiente_agente"] = "recomendador_destinos_agent"
        return state

    try:
        precio = float(str(vuelo_elegido.get("precio", "0")).replace("€", "").replace(",", "").strip())
    except:
        precio = 0.0

    presupuesto = contexto.get("presupuesto", 0)
    restante = max(presupuesto - precio, 0)

    state["vuelo_elegido"] = vuelo_elegido
    state["presupuesto_inicial"] = presupuesto
    state["presupuesto_restante"] = restante
    state["siguiente_agente"] = "buscador_alojamiento_agent"

    print(f"\n✅ Vuelo seleccionado: {vuelo_elegido.get('compañias', '---')} — Precio: {vuelo_elegido.get('precio', '---')}")
    print(f"💰 Presupuesto restante: {restante:.2f} €")

    return state