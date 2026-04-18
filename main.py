from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from pydantic import BaseModel
from ai_bot.agent import query_agent
import os

app = FastAPI()   # 👈 THIS IS REQUIRED
os.environ['GOOGLE_API_KEY'] = 'AQ.Ab8RN6KKHQno2jBHCaRMl2vJ0LLQb916IE7GRCtdo4oNKAMtFQ'

class Query(BaseModel):
    query: str

@app.post("/ask")
async def ask(q: Query):
    response = await query_agent(q.query)
    return {"response": response}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
