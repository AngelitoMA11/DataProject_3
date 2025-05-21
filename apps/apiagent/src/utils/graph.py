from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.agents.core import core_agent
from src.agents.agente import travel_agent
from src.utils.logger_config import setup_logger
from typing import Dict, Any


# Create logger for this module
logger = setup_logger('api_agent.graph')

def get_messages(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    messages = travel_agent.graph.get_state(config)[0].get('messages', [])
    
    def format(msg):
        return {
            'role': 'user' if isinstance(msg, HumanMessage) else 'assistant',
            'content': msg.content
        }

    if not messages:
        return []
    elif len(messages) == 1:
        return [format(messages[0])]
    else:
        respuesta = []
        for i in range(1, len(messages)):
            if isinstance(messages[i], HumanMessage):
                respuesta.append(format(messages[i-1]))
                respuesta.append(format(messages[i]))
        respuesta.append(format(messages[-1]))
        return respuesta

def process_message(message: str, thread_id: str) -> dict:
    """Process a single message and return the response and reasoning chain"""
    logger.info(f"Processing message for thread {thread_id}")
    
    # Setup config for memory
    config = {"configurable": {"thread_id": thread_id}}
    
    # Setup state
    state = {"messages": [HumanMessage(content=message)]}
    logger.debug(f"Initial state: {state}")
    
    # Process message through the graph
    response = core_agent.invoke(state, config)
    logger.info(f"Agent response: {response}")

    # Obtenemos los mensajes
    messages = response["messages"]

    # Obtenemos los mensajes de la última interacción
    last_interaction_messages = get_last_interaction_messages(messages)
    logger.info(f"Last interaction messages: {last_interaction_messages}")
    
    return {
        "response": messages[-1].content,
        "reasoning_chain": "\n".join(message.pretty_repr(html=False) for message in last_interaction_messages)
    }



def process_message_agente2(message: str, thread_id: str) -> dict:
    """Process a single message and return the response and reasoning chain"""
    logger.info(f"Processing message for thread {thread_id}")
    
    # Setup config for memory
    config = {"configurable": {"thread_id": thread_id}}
    
    # Setup state
    state = {"messages": [HumanMessage(content=message)]}
    logger.debug(f"Initial state: {state}")
    
    # Process message through the graph
    response = travel_agent.graph.invoke(state, config)
    logger.info(f"Agent response: {response}")

    # Obtenemos los mensajes
    messages = response["messages"]

    # Obtenemos los mensajes de la última interacción
    last_interaction_messages = get_last_interaction_messages(messages)
    logger.info(f"Last interaction messages: {last_interaction_messages}")
    
    return {
        "response": messages[-1].content,
        "reasoning_chain": "\n".join(message.pretty_repr(html=False) for message in last_interaction_messages)
    }

def get_last_interaction_messages (messages):
    # Find the index of the last HumanMessage
    last_human_index = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_index = i

    # Get all messages from the last HumanMessage to the end
    return messages[last_human_index:]

def get_last_interaction_messages (messages):
    # Find the index of the last HumanMessage
    last_human_index = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_index = i

    # Get all messages from the last HumanMessage to the end
    return messages[last_human_index:]