from __future__ import annotations

from fastapi import FastAPI

from src.services.draws_provider import fetch_draws

app = FastAPI(title="EuroMillions Predictor API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/draws")
def get_draws() -> list[dict]:
    return fetch_draws()
