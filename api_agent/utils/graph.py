from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.flight_assistant import flight_assistant
from agents.hotel_assistant import hotel_assistant
from agents.explorador import explorador
from utils.schemas import State, CustomAgentState
from langchain_core.messages import convert_to_messages
from utils.logger_config import setup_logger

# from agents.human_interrupt import human_interrupt
# from agents.itinerary_planner import itinerary_planner
# from agents.orchestrator import orchestrator
# from agents.travel_planner import travel_planner

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor

from agents.supervisor import supervisor

# Create logger for this module
logger = setup_logger('api_agent.graph')

# Memory
memory = MemorySaver()

# Graph Builder
# logger.info("Initializing graph builder")
# graph_builder = StateGraph(State)

# graph_builder.add_node(supervisor, destinations=("research", "math_agent"))
# graph_builder.add_node(research)
# graph_builder.add_node(math_agent)

# # always return back to the supervisor
# graph_builder.add_edge(START, "supervisor")
# graph_builder.add_edge("research", "supervisor")
# graph_builder.add_edge("math_agent", "supervisor")

# # Build graph
# logger.info("Compiling graph")
# graph = graph_builder.compile(checkpointer=memory)
# logger.info("Graph compilation completed")

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


def process_message(message: str, thread_id: str) -> dict:
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

# def pretty_print_message(message, indent=False):
#     pretty_message = message.pretty_repr(html=False)
#     if not indent:
#         return f'{pretty_message}\n'

#     indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
#     return f'{indented}\n'