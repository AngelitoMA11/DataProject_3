from typing import Annotated, TypedDict, List, Literal
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]

class Router(TypedDict):
    next: Literal["itinerary_agent", "flight_agent", "human", "finish"]
    message: str