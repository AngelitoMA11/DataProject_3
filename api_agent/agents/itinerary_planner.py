from langchain_core.messages import SystemMessage, AIMessage
from utils.schemas import State
from config import GEMINI_API_KEY
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY
)

def itinerary_planner(state: State) -> State:
    """Agent specialized in creating travel itineraries"""
    
    system_prompt = SystemMessage(content="""
    You are an expert travel itinerary planner. Your role is to:
    1. Create detailed day-by-day travel plans
    2. Include activities, accommodations, and transportation
    3. Consider user preferences and constraints
    4. Provide practical and enjoyable suggestions
    
    Format your response in a clear, structured way.
    """)
    
    response = llm.invoke([system_prompt] + state["messages"])
    state["messages"].append(AIMessage(content=response.content))
    return state
