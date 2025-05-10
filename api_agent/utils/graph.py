from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.flight_assistant import flight_assistant
from agents.hotel_assistant import hotel_assistant
from utils.schemas import State
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
logger.info("Initializing graph builder")
graph_builder = StateGraph(State)

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
    agents=[flight_assistant, hotel_assistant],
    model=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash"
    ),
    prompt="""
    Eres un supervisor que maneja dos agentes:
    - Hotel booking assistant
    - Flight booking assistant

    Asignales trabajo

    - Si los agentes piden informacion, pidesela al usuario.
    - El usuario no puede hablar con los agentes, lo hará siempre a través de ti.
    """
).compile(checkpointer=memory)

def process_message(message: str, thread_id: str) -> str:
    """Process a single message and return the response"""
    logger.info(f"Processing message for thread {thread_id}")
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Process message through the graph
    for step in supervisor.stream(state, config):
        # steps = '\n'.join([i.content for i in final_message_history])
        logger.debug(f"Step output: {step}")
        # pretty_print_messages(step, last_message=True)

    
    logger.info("Message processing completed")
    final_message_history = step["supervisor"]["messages"]
    for message in final_message_history:
        message.pretty_print()
    
    return final_message_history[-1].content

def pretty_print_message(message, indent=False):
    text = ''
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        text += f'{pretty_message}\n'
        return text

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    text += f'{indented}\n'
    return text

def pretty_print_messages(update, last_message=False):
    text = ''
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        text += f'Update from subgraph {graph_id}:\n\n'
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label
        
        text += f'{update_label}\n\n'

        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]

        for m in messages:
            text += pretty_print_message(m, indent=is_subgraph) +"\n"
        text += "\n"
    
    logger.debug(text)