from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import GEMINI_API_KEY
from tools.fligths import search_flights

# Memoria
memory = MemorySaver()

# Estado
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Graph Builder
graph_builder = StateGraph(State)

# Tools
tools = [search_flights]


llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY
)
llm_flight_tool = llm.bind_tools(tools)

def planner(state: State) -> State:
    """Plan the vacation based on user input"""

    system_prompt = SystemMessage(content="""
    Eres un agente experto en planificación de vacaciones. Tu trabajo es:
    1. Analizar la solicitud del usuario
    2. Identificar destino, fechas y preferencias
    3. Sugerir un plan inicial
    4. Decidir si necesitas buscar vuelos

    Responde de forma amigable y profesional.
    """)
    
    # Generamos la respuesta con el llm
    response = llm_flight_tool.invoke([system_prompt] + state["messages"])
    
    # Hacemos un append del mensaje generado
    state["messages"].append(AIMessage(content=response.content))
    return state

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}



# Nodos
graph_builder.add_node("planner", planner)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)


# Edges

graph_builder.add_conditional_edges(
    "planner",
    tools_condition,
)

graph_builder.add_edge(START, "planner")
graph_builder.add_edge("tools", "planner")


# Build
graph = graph_builder.compile(checkpointer=memory)

# Guardar el grafo en local
with open("graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())

# Create the main agent interface
def process_message(message: str, thread_id: str) -> str:
    """Process a single message and return the response with intermediate steps printed"""
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Use stream instead of invoke to get intermediate steps
    for step in graph.stream(state, config):
        # step["planner"]["messages"][-1].pretty_print()
        # Print intermediate state for debugging
        print(f"Step output: {step}")
        
    # Return final message
    # result = graph.invoke(state, config)
    return step["planner"]["messages"][-1].content
