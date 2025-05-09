from typing import Annotated, TypedDict, List, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.human_interrupt import human_interrupt
from agents.itinerary_planner import itinerary_planner
from agents.orchestrator import orchestrator
from agents.travel_planner import travel_planner

# Memory
memory = MemorySaver()

# State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Router Schema
class Router(TypedDict):
    next: Literal["itinerary_agent", "flight_agent", "human", "finish"]
    message: str

# Graph Builder
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("orchestrator", orchestrator)
graph_builder.add_node("itinerary_planner", itinerary_planner)
graph_builder.add_node("travel_planner", travel_planner)
graph_builder.add_node("human", human_interrupt)

# Add edges
graph_builder.add_edge(START, "orchestrator")
graph_builder.add_edge("orchestrator", "itinerary_planner")
graph_builder.add_edge("orchestrator", "travel_planner")
graph_builder.add_edge("orchestrator", "human")
graph_builder.add_edge("orchestrator", END)

# Build graph
graph = graph_builder.compile(checkpointer=memory)

# Save graph visualization
with open("graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())

def process_message(message: str, thread_id: str) -> str:
    """Process a single message and return the response"""
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Process message through the graph
    for step in graph.stream(state, config):
        print(f"Step output: {step}")
    
    # Return final message
    return step["chatbot"]["messages"][-1].content
