from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.agents.supervisor import supervisor

from src.utils.schemas import CustomAgentState
from src.utils.logger_config import setup_logger

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor

# Create logger for this module
logger = setup_logger('api_agent.graph')

# Memory
memory = MemorySaver()

# Creamos el grafo
graph = supervisor.compile(checkpointer=memory)


def process_message(message: str, thread_id: str) -> dict:
    """Process a single message and return the response and reasoning chain"""
    logger.info(f"Processing message for thread {thread_id}")
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    # Log initial state
    logger.info(f"Initial state: {state}")
    
    # Process message through the graph
    for step in graph.stream(state, config):
        logger.debug(f"Step output: {step}")
        # Log state after each step
        logger.info(f"State after step: {step.get('supervisor', {})}")
    
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
    
    # Log final state
    logger.info(f"Final state: {step.get('supervisor', {})}")
    
    return {
        "response": all_messages[-1 if len(last_interaction_messages) == 2 else -4].content,
        "reasoning_chain": "\n".join(message.pretty_repr(html=False) for message in last_interaction_messages)
    }



