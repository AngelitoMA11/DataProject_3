from typing import Annotated, List, Literal
from typing_extensions import TypedDict 
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState


class CustomAgentState(AgentState):
    """The state of the agent."""
    # messages: Annotated[Sequence[BaseMessage], add_messages]
    # is_last_step: IsLastStep
    # remaining_steps: RemainingSteps

    # TODO Añadir estados para los agentes
