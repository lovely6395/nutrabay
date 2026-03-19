from typing import Dict, List, Union

from pydantic import BaseModel, Field


class StructuredAvailability(BaseModel):
    day: str = Field(description="Day name, e.g. Tuesday")
    start: str = Field(description="24-hour time HH:MM")
    end: str = Field(description="24-hour time HH:MM")


class ScheduleRequest(BaseModel):
    candidate_availability: Union[str, List[StructuredAvailability]]
    interviewer_availability: Dict[str, Union[str, List[StructuredAvailability]]]
    timezone: str = "UTC"


class ScheduleResponse(BaseModel):
    top_slots: List[str]
    conflicts: List[str]
    final_recommendation: str
    reasoning: str
