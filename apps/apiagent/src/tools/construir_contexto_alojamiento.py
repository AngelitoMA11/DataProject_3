def construir_contexto_alojamiento(destino_elegido, fechas, vuelo_elegido, compañia_viaje):
    return {
        "ciudad": destino_elegido.get("nombre", "Destino desconocido"),
        "fechas": fechas,
        "adults": compañia_viaje.get("adults", 2),
        "children": compañia_viaje.get("children", 0),
        "vuelo": vuelo_elegido,
        "viajeros": compañia_viaje
    }