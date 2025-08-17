from __future__ import annotations

from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import router as api_router

load_dotenv()

app = FastAPI(
    title="Classificação de Tickets (OpenAI)",
    version="1.0.0",
    description="Rota única para resumo (≤3 frases) e classificação em 1 categoria."
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
