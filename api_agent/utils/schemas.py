from typing import Annotated, List, Literal
from typing_extensions import TypedDict 
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]