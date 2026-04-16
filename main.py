from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from pydantic import BaseModel
from agent import agent

app = FastAPI()   # 👈 THIS IS REQUIRED

class Query(BaseModel):
    query: str

@app.post("/ask")
def ask(q: Query):
    response = agent.generate_content(q.query)
    return {"response": response}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
