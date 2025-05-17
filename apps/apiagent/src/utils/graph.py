from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.agents.flight_assistant import flight_assistant
from src.agents.hotel_assistant import hotel_assistant
from src.agents.explorador import explorador
from src.utils.schemas import CustomAgentState
from src.utils.logger_config import setup_logger

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor

# Create logger for this module
logger = setup_logger('api_agent.graph')

# Memory
memory = MemorySaver()

# supervisor = create_supervisor(
#     agents=[flight_assistant, hotel_assistant, explorador],
#     model=ChatGoogleGenerativeAI(
#         model="gemini-2.0-flash",
#     ),
#     state_schema=CustomAgentState,
#     prompt="""
#     Eres un sistema multiagente con el objetivo de ayudar a los usuarios a planificar sus viajes.
#     Tu misión es asignar trabajo a los siguientes agentes:
#     - Hotel booking assistant
#     - Flight booking assistant
#     - explorador: Un agente que ayuda al usuario a decidir donde quiere ir.

#     Ten en cuanta las siguientes normas:
#     - Si los agentes te piden información, pidesela al usuario.
#     - El usuario no puede hablar con los agentes, lo hará siempre a través de ti.
#     - No menciones a los agentes, el usuario no debe de saber que existen.
#     """
# ).compile(checkpointer=memory) # Añadimos la memoria


from langgraph.graph import StateGraph, END

# Crear el grafo de estados
builder = StateGraph(state_schema=ViajeState)

# 1. Agentes reales (usa los nombres de función que ya definiste)
builder.add_node("coordinador_agent", coordinador_agent)
builder.add_node("core_agent", core_agent)
builder.add_node("recomendador_destinos_agent", recomendador_destinos_agent)
builder.add_node("buscador_vuelos_agent", buscador_vuelos_agent)
builder.add_node("buscador_alojamiento_agent", buscador_alojamiento_agent)

# 2. Entrada
builder.set_entry_point("coordinador_agent")

# 3. Transiciones según coordinador
builder.add_conditional_edges(
    "coordinador_agent",
    lambda state: state.get("siguiente_agente", END),
    {
        "core_agent": "core_agent",
        "recomendador_destinos_agent": "recomendador_destinos_agent",
        "buscador_vuelos_agent": "buscador_vuelos_agent",
        "buscador_alojamiento_agent": "buscador_alojamiento_agent",
        END: END
    }
)

# 4. Vuelta al coordinador tras cada agente
builder.add_edge("core_agent", "coordinador_agent")
builder.add_edge("recomendador_destinos_agent", "coordinador_agent")
builder.add_edge("buscador_vuelos_agent", "coordinador_agent")
builder.add_edge("buscador_alojamiento_agent", "coordinador_agent")

# 5. Compilar
graph = builder.compile(chechpointer=memory)


def     process_message(message: str, thread_id: str) -> dict:
    """Process a single message and return the response and reasoning chain"""
    logger.info(f"Processing message for thread {thread_id}")
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Process message through the graph
    for step in graph.stream(state, config):
        logger.debug(f"Step output: {step}")
    
    logger.info("Message processing completed")
    all_messages = step["coordinador_agent"]["messages"]

    # Find the index of the last HumanMessage
    last_human_index = -1
    for i, msg in enumerate(all_messages):
        if isinstance(msg, HumanMessage):
            last_human_index = i

    # Get all messages from the last HumanMessage to the end
    last_interaction_messages = all_messages[last_human_index:]
    logger.info(f"Last interaction messages: {last_interaction_messages}")
    
    return {
        "response": all_messages[-1].content,
        "reasoning_chain": "\n".join(message.pretty_repr(html=False) for message in last_interaction_messages)
    }



