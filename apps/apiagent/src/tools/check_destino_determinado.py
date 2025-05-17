def check_destino_determinado(state):
    return "directo_vuelos" if state.get("destino_determinado", False) else "ir_recomendador"