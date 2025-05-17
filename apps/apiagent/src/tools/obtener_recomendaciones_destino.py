def obtener_recomendaciones_destino(contexto_user):
    prompt = f"""
    Eres un experto en planificación de viajes. Con base en la siguiente información del usuario, realiza dos tareas:

    1️⃣ Extrae el código IATA del aeropuerto principal de la ciudad de origen del usuario.
    2️⃣ Recomienda entre 3 y 5 destinos que cumplan con sus preferencias.

    🔍 Requisitos estrictos para cada destino:
    - Debe ser una ciudad o región específica.
    - Incluir la ciudad base con aeropuerto cercana o principal.
    - Incluir el código IATA exacto de esa ciudad base.
    - Ajustarse al presupuesto estimado.
    - Cumplir con el tipo de viaje y características deseadas.
    - Respetar el tipo de alcance indicado (nacional, internacional, intercontinental).

    📍 Ciudad de origen del usuario: {contexto_user.get("ciudad_origen", "Desconocida")}

    🎯 Contexto completo del usuario (en JSON):
    {json.dumps(contexto_user, indent=2, ensure_ascii=False)}

    📦 Formato de respuesta (solo JSON válido):
    {{
      "iata_origen": "Código IATA del aeropuerto de la ciudad de origen",
      "destinos_recomendados": [
        {{
          "nombre": "Nombre del destino",
          "país": "País del destino",
          "razón": "Explicación breve de por qué es una buena opción",
          "estimacion_coste_total": 1400,
          "ciudad_base": "Ciudad con aeropuerto desde la cual se accede al destino",
          "iata": "Código IATA de la ciudad base"
        }}
      ]
    }}
    """

    try:
        # Generar respuesta
        response = model.generate_content(prompt)

        # Extraer y limpiar el JSON
        json_part = response.text.strip().split("```json")[-1].split("```")[0]
        data = json.loads(json_part)

        # Validación básica
        if not data.get("iata_origen"):
            raise ValueError("Falta el código IATA de origen (iata_origen)")

        for destino in data.get("destinos_recomendados", []):
            if not destino.get("iata") or not destino.get("ciudad_base"):
                raise ValueError("Falta IATA o ciudad_base en al menos un destino")

        return data

    except Exception as e:
        print("❌ Error al parsear o validar la respuesta del modelo:", e)
        print("🔴 Respuesta cruda:", response.text)
        return {}