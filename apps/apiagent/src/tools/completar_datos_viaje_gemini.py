import json
import re

def completar_datos_viaje_gemini(model, mensaje_inicial):
    historial = [mensaje_inicial]
    user_input = mensaje_inicial

    while True:
        prompt = construir_prompt_core_agent(user_input)
        response = model.generate_content(prompt)
        output = response.text
        print("\n🔽 OUTPUT DEL LLM 🔽\n", output)

        try:
            json_text = re.search(r'\{[\s\S]*\}', output).group(0)
            datos = json.loads(json_text)
        except Exception as e:
            print("❌ Error extrayendo JSON:", e)
            break

        preguntas_faltantes = []

        def recolectar_preguntas(obj):
            if isinstance(obj, dict):
                if "campos_faltantes" in obj:
                    preguntas_faltantes.extend(obj["campos_faltantes"])
                for value in obj.values():
                    recolectar_preguntas(value)
            elif isinstance(obj, list):
                for item in obj:
                    recolectar_preguntas(item)

        recolectar_preguntas(datos)

        if not preguntas_faltantes:
            print("\n✅ Todos los campos han sido completados.")
            return datos

        for campo in preguntas_faltantes:
            respuesta = input(campo["pregunta"] + " ")
            historial.append(respuesta)

        user_input = " ".join(historial)