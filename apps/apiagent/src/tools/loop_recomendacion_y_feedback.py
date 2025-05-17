def loop_recomendacion_y_feedback(model, contexto_user, max_intentos=3):
    destinos_rechazados = []
    intentos = 0  # Contador para los intentos

    while True:
        if destinos_rechazados:
            contexto_user["destinos_rechazados"] = destinos_rechazados

        # Obtener nuevas recomendaciones
        resultados = obtener_recomendaciones_destino(contexto_user)

        # ⚠️ Validación de campos esperados
        if not resultados or "destinos_recomendados" not in resultados or "iata_origen" not in resultados:
            print("❌ Error: respuesta incompleta del agente de recomendación.")
            break

        recomendaciones = resultados["destinos_recomendados"]
        iata_origen = resultados["iata_origen"]

        if not recomendaciones:
            print("❌ No se pudieron generar recomendaciones.")
            break

        print("\n🌍 DESTINOS RECOMENDADOS:\n")
        for idx, destino in enumerate(recomendaciones, start=1):
            print(f"[{idx}] {destino['nombre']} ({destino['país']})")
            print(f"    ➤ Motivo: {destino['razón']}")
            print(f"    💰 Estimación coste total: {destino['estimacion_coste_total']}€")
            print(f"    ✈️ Ciudad base: {destino['ciudad_base']} ({destino['iata']})\n")

        eleccion = input("🧭 ¿Cuál destino eliges? Escribe el número o 'ninguno' si no te convence ninguno:\n👉 ").strip().lower()

        if eleccion == "ninguno":
            print("🔁 Mostrando nuevas recomendaciones...")
            destinos_rechazados.extend([d["nombre"] for d in recomendaciones])
            intentos += 1
            if intentos >= max_intentos:
                print("❌ Has alcanzado el máximo de intentos.")
                break
            continue

        try:
            idx = int(eleccion) - 1
            destino_elegido = recomendaciones[idx]
            contexto_user.update({
                "destino_elegido": destino_elegido,
                "iata_origen": iata_origen  # ✅ Ahora sí quedará en el JSON final
            })

            break
        except (ValueError, IndexError):
            print("❌ Entrada no válida. Por favor, elige un número correcto o 'ninguno'.")
            continue

    return contexto_user