from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.utils.graph import process_message, process_message_agente2, get_messages

app = FastAPI()

# Initialize the AI agent
# agent = LangraphAgent()

class Input(BaseModel):
    message: str
    thread_id: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Travel Planning Agent"}

@app.get("/messages")
def messages(thread_id: str):
    result = get_messages(thread_id)
    return result

@app.post("/chat2")
async def chat(input: Input):
    result = process_message(input.message, input.thread_id)
    return result

@app.post("/chat")
async def chat2(input: Input):
    result = process_message_agente2(input.message, input.thread_id)
    return result

