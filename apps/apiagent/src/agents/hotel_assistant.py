from langgraph.prebuilt import create_react_agent

def book_hotel(hotel_name: str):
    """Book a hotel"""
    return f"Successfully booked a stay at {hotel_name}."

hotel_assistant = create_react_agent(
    model="google_genai:gemini-2.0-flash",
    tools=[book_hotel],
    prompt="You are a hotel booking assistant",
    name="hotel_assistant"
)