def construir_prompt_core_agent(user_input):
    return f"""
Eres un asistente de planificación de viajes. Extrae los siguientes datos y devuélvelos en JSON:

- presupuesto (en euros)
- fechas (inicio y fin, o duración estimada)
- preferencias: entorno (playa, montaña, ciudad, etc.) y tipo de viaje (relax, cultural, gastronómico, etc.)
- acompañantes (solo, pareja, familia, amigos)
- alcance: nacional, internacional, intercontinental
- ciudad de origen

Si faltan datos, devuélvelos bajo el campo 'campos_faltantes' con preguntas para completar. Ejemplo:

{{
  "presupuesto": 1000,
  "fechas": {{
    "inicio": "2024-06-10",
    "fin": "2024-06-17"
  }},
  "preferencias": {{
    "entorno": ["playa", "montaña"],
    "tipo_viaje": "relax"
  }},
  "acompañantes": "familia",
  "alcance": "internacional",
  "ciudad_origen": "Madrid",
  "campos_faltantes": [
    {{
      "campo": "fechas",
      "pregunta": "¿Qué fechas exactas tienes en mente?"
    }},
    {{
      "campo": "ciudad_origen",
      "pregunta": "¿Desde qué ciudad estarás viajando?"
    }}
  ]
}}

Texto del usuario:
\"{user_input}\"
"""
