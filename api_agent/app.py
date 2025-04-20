from fastapi import FastAPI, Request
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agents.main_agent import MainAgent

app = FastAPI()

# Initialize the AI agent
# agent = LangraphAgent()

@app.get("/")
def read_root():
    return {"message": "Welcome to the API Agent"}

@app.post("/query/")
async def query_agent(query: str):
    response = MainAgent.process_query(query)
    return {"response": response}
from pydantic import BaseModel

class Input(BaseModel):
    message: str
    thread_id: str

@app.post("/chat")
async def chat(input: Input):
    config = {"configurable": {"thread_id": input.thread_id}}
    result = MainAgent.invoke({"messages": [HumanMessage(content=input.message)]}, config)
    return {"response": result["messages"][-1].content}

