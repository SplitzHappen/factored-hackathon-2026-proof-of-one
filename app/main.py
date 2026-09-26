from fastapi import FastAPI

from app.schemas import HealthResponse

app = FastAPI(
    title="Proof of One",
    description="Bounded account and payment support prototype for the Factored AI & Data Hackathon 2026.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="proof-of-one",
        llm_connected=False,
    )
