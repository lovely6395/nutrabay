from fastapi import FastAPI, HTTPException

from app.models.schemas import ScheduleRequest, ScheduleResponse
from app.services.gemini_client import GeminiClient
from app.services.recommendation_service import build_schedule_response

app = FastAPI(title="Interview Scheduling Automation System", version="0.1.0")

gemini_client = GeminiClient()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "gemini_enabled": gemini_client.enabled}


@app.post("/schedule", response_model=ScheduleResponse)
def schedule(req: ScheduleRequest) -> ScheduleResponse:
    try:
        result = build_schedule_response(
            candidate_input=req.candidate_availability,
            interviewer_input=req.interviewer_availability,
            gemini_client=gemini_client,
        )
        return ScheduleResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
