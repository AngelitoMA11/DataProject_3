from langchain_core.messages import SystemMessage, AIMessage
from utils.schemas import State
from config import GEMINI_API_KEY
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY
)

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal['itinerary_agent', 'human_interrupt', 'FINISH']
    messages: str


def orchestrator(state: State) -> State:
    """Supervisor chatbot that routes messages to appropriate agents"""
    
    system_prompt = SystemMessage(content="""
    You are a travel planning assistant that coordinates between different specialized agents.
    Your role is to:
    1. Understand the user's request
    2. Route the request to the appropriate agent:
       - itinerary_agent: For creating travel itineraries and plans
       - flight_agent: For searching and booking flights
       - human: When you need clarification from the user
       - finish: When the request is complete
    3. Provide clear, helpful responses
    
    Always respond in a friendly and professional manner.
    """)
    
    # Get routing decision from LLM
    response = llm.invoke([system_prompt] + state["messages"])
    
    # Add the response to state
    state["messages"].append(AIMessage(content=response.content))
    return state