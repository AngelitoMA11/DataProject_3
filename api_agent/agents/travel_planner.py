from langchain_core.messages import SystemMessage, AIMessage
from utils.schemas import State
from config import GEMINI_API_KEY
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.fligths import search_flights

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GEMINI_API_KEY
)

# Tools
tools = [search_flights]
llm_with_tools = llm.bind_tools(tools)

def travel_planner(state: State) -> State:
    """Agent specialized in flight search and booking"""
    
    system_prompt = SystemMessage(content="""
    You are a flight search specialist. Your role is to:
    1. Extract travel details from user requests
    2. Search for available flights using the search_flights tool
    3. Present flight options in a clear format
    4. Help with flight selection
    
    Always verify flight details before presenting them.
    """)
    
    response = llm_with_tools.invoke([system_prompt] + state["messages"])
    state["messages"].append(AIMessage(content=response.content))
    return state