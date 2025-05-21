from typing import Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import InjectedState
from langgraph.graph import StateGraph, START, MessagesState, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from src.utils.schemas import CustomAgentState
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode
from typing import Dict, Any, List
from src.utils.logger_config import setup_logger


logger = setup_logger('agents.core')


research_agent = create_react_agent(
    model=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
    ),
    tools=[],
    prompt=(
        "You are a research agent.\n\n"
        "INSTRUCTIONS:\n"
        "- Assist ONLY with research-related tasks, DO NOT do any math\n"
        "- After you're done with your tasks, respond to the supervisor directly\n"
        "- Respond ONLY with the results of your work, do NOT include ANY other text."
    ),
    name="research_agent",
)


def add(a: float, b: float):
    """Add two numbers."""
    return a + b


def multiply(a: float, b: float):
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float):
    """Divide two numbers."""
    return a / b


math_agent = create_react_agent(
    model=ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
    ),
    tools=[add, multiply, divide],
    prompt=(
        "You are a math agent.\n\n"
        "INSTRUCTIONS:\n"
        "- Assist ONLY with math-related tasks\n"
        "- After you're done with your tasks, respond to the supervisor directly\n"
        "- Respond ONLY with the results of your work, do NOT include ANY other text."
    ),
    name="math_agent",
)


def create_handoff_tool(*, agent_name: str, description: str | None = None):
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,  
            update={**state, "messages": state["messages"] + [tool_message]},  
            graph=Command.PARENT,  
        )

    return handoff_tool


# Handoffs
assign_to_research_agent = create_handoff_tool(
    agent_name="research_agent",
    description="Assign task to a researcher agent.",
)

assign_to_math_agent = create_handoff_tool(
    agent_name="math_agent",
    description="Assign task to a math agent.",
)

# Create the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    tools=[
        assign_to_research_agent,
        assign_to_math_agent
    ]
)

# Define the system prompt
SYSTEM_PROMPT = """
You are a supervisor managing two agents:
- a research agent. Assign research-related tasks to this agent
- a math agent. Assign math-related tasks to this agent

Responde únicamente con el nombre de la tool a utilizar

Available tools:
- assign_to_research_agent: Use this for research-related tasks
- assign_to_math_agent: Use this for math-related tasks
"""

def supervisor_agent(state: CustomAgentState) -> Dict[str, Any]:
    """
    Supervisor agent that manages and delegates tasks to specialized agents.
    
    Args:
        state: The current state containing messages and context
        
    Returns:
        Updated state with the supervisor's response
    """

    # Get the last message from the user
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    
    if not last_message or not isinstance(last_message, HumanMessage):
        return {
            "messages": [AIMessage(content="I need a message to process. Please provide your request.")],
            "next": END
        }
    
    # Create the full message history with system prompt
    full_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *messages
    ]
    
    # Get response from LLM
    response = llm.invoke(full_messages)

    logger.info(f"--------------------------------------\n{response}")
    
    # Update state with the response
    return {
        "messages": [*messages, response],
        "next": "research_agent" if "research" in response.content.lower() else "math_agent"
    }

core = (StateGraph(CustomAgentState)
    # NOTE: `destinations` is only needed for visualization and doesn't affect runtime behavior
    .add_node(supervisor_agent, destinations=("research_agent", "math_agent", END))
    .add_node(research_agent)
    .add_node(math_agent)
    .add_edge(START, "supervisor_agent")
    .add_edge("research_agent", END)
    .add_edge("math_agent", END)
)

# supervisor_agent = create_react_agent(
#     model="openai:gpt-4.1",
#     tools=[assign_to_research_agent, assign_to_math_agent],
#     prompt=(
#         "You are a supervisor managing two agents:\n"
#         "- a research agent. Assign research-related tasks to this agent\n"
#         "- a math agent. Assign math-related tasks to this agent\n"
#         "Assign work to one agent at a time, do not call agents in parallel.\n"
#         "Do not do any work yourself."
#     ),
#     name="supervisor",
# )

