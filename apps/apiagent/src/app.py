from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.utils.graph import process_message, process_message_agente2

app = FastAPI()

# Initialize the AI agent
# agent = LangraphAgent()

class Input(BaseModel):
    message: str
    thread_id: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Travel Planning Agent"}

@app.post("/chat")
async def chat(input: Input):
    result = process_message(input.message, input.thread_id)
    return result

@app.post("/chat2")
async def chat2(input: Input):
    # Here you can implement different logic for the second agent
    # For now, we'll use the same process_message function
    result = process_message_agente2(input.message, input.thread_id)
    return result

