from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.debate import router          # ← add "backend." prefix

app = FastAPI(title="Fantasy Cricket Debate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"status": "Fantasy Cricket Debate API is running"}