from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor
from src.utils.schemas import CustomAgentState
from src.agents.recomendador import recomendador_agent
from src.agents.alojamiento import buscador_alojamiento_agent
from src.agents.vuelos import vuelos_agent

prompt = """
Eres un supervisor experto en coordinar agentes para planificar viajes.

Agentes disponibles:
- recomendador_destinos_agent: extrae la información esencial del usuario (fechas, presupuesto, origen, tipo de destino) y recomienda destinos afines según esas preferencias. Es el punto de partida para usuarios sin destino definido.
- buscador_vuelos_agent: busca vuelos solo cuando se tiene un destino claro, junto con fechas y origen.
- buscador_alojamiento_agent: busca alojamientos tras confirmarse la reserva de vuelo o destino.

REGLAS:

- Tu función es asignar el agente correcto según la información disponible en la conversación.
- Asigna trabajo a los agentes.
- No hagas nada por ti mismo. Únicamente asigna tareas a los agentes.

"""

supervisor = create_supervisor(
    state_schema=CustomAgentState,
    model=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
    ),
    prompt=prompt,
    agents=[
        recomendador_agent,
        vuelos_agent,
        buscador_alojamiento_agent,
    ],
    add_handoff_back_messages=True
)