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

supervisor = create_supervisor(
    agents=[flight_assistant, hotel_assistant, explorador],
    model=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
    ),
    state_schema=CustomAgentState,
    prompt="""
    Eres un sistema multiagente con el objetivo de ayudar a los usuarios a planificar sus viajes.
    Tu misión es asignar trabajo a los siguientes agentes:
    - Hotel booking assistant
    - Flight booking assistant
    - explorador: Un agente que ayuda al usuario a decidir donde quiere ir.

    Ten en cuanta las siguientes normas:
    - Si los agentes te piden información, pidesela al usuario.
    - El usuario no puede hablar con los agentes, lo hará siempre a través de ti.
    - No menciones a los agentes, el usuario no debe de saber que existen.
    """
).compile(checkpointer=memory) # Añadimos la memoria


def     process_message(message: str, thread_id: str) -> dict:
    """Process a single message and return the response and reasoning chain"""
    logger.info(f"Processing message for thread {thread_id}")
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Process message through the graph
    for step in supervisor.stream(state, config):
        logger.debug(f"Step output: {step}")
    
    logger.info("Message processing completed")
    all_messages = step["supervisor"]["messages"]

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
