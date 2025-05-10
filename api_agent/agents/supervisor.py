from typing import Annotated, Union, TypedDict, List
from utils.graph import State
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.types import Command
from config import GOOGLE_API_KEY
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from utils.logger_config import setup_logger
from langgraph.prebuilt import create_react_agent

# Create logger for this module
logger = setup_logger('api_agent.supervisor')

class SupervisorState(TypedDict):
    messages: List[HumanMessage | SystemMessage | AIMessage]

def create_task_description_handoff_tool(
    *, agent_name: str, description: str | None = None
):
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
        # this is populated by the supervisor LLM
        task_description: Annotated[
            str,
            "Description of what the next agent should do, including all of the relevant context.",
        ],
        # these parameters are ignored by the LLM
        state: Annotated[State, InjectedState],
    ) -> Command:
        task_description_message = {"role": "user", "content": task_description}
        agent_input = {**state, "messages": [task_description_message]}
        return Command(
            # highlight-next-line
            goto=[Send(agent_name, agent_input)],
            graph=Command.PARENT,
        )

    return handoff_tool


# Handoffs
assign_to_research_agent_with_description = create_task_description_handoff_tool(
    agent_name="research",
    description="Assign task to a researcher agent.",
)

assign_to_math_agent_with_description = create_task_description_handoff_tool(
    agent_name="math_agent",
    description="Assign task to a math agent.",
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY
).bind_tools([
    assign_to_research_agent_with_description,
    assign_to_math_agent_with_description
])

def supervisor(state: State) -> SupervisorState:
    """
    Supervisor agent that decides which agent to use based on the user's message.
    """
    logger.info("Supervisor agent started processing")
    logger.info(f"Current state: {state}")
    
    # Get the last message from the user
    last_message = state["messages"][-1]
    logger.debug(f"Processing message: {last_message.content}")
    
    # Define the system prompt
    system_prompt = SystemMessage(
        content="""
        You are a supervisor agent that decides which agent to use based on the user's message.
        You can choose between:
        - research: For questions about general knowledge, research, or information gathering
        - math_agent: For mathematical calculations, equations, or numerical problems
        You 
        """
    )
    
    # Get the response from the LLM
    logger.debug("Sending request to LLM")
    response = llm.invoke([system_prompt] + state["messages"])
    logger.debug(f"Received response from LLM: {response.content}")
    
    # Add the response to the state
    state["messages"].append(response)
    
    logger.info(f"Supervisor decided to use agent: {response.content}")
    return state