from langgraph.prebuilt import create_react_agent

def book_flight(from_airport: str, to_airport: str):
    """Book a flight"""
    return f"Successfully booked a flight from {from_airport} to {to_airport}."

flight_assistant = create_react_agent(
    model="google_genai:gemini-2.0-flash",
    tools=[book_flight],
    prompt="You are a flight booking assistant",
    name="flight_assistant"
)