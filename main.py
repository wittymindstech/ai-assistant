from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from pydantic import BaseModel
from ai_bot.agent import query_agent_with_usage
import os

app = FastAPI()   # 👈 THIS IS REQUIRED
os.environ['GOOGLE_API_KEY'] = 'AIzaSyDnHyzMM3HrGbbBjwnhmGD55Ye2q9RWUF0'

class Query(BaseModel):
    query: str

@app.post("/ask")
async def ask(q: Query):
    result = await query_agent_with_usage(q.query)
    return result

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
