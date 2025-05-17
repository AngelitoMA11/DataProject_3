from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.utils.graph import process_message

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

