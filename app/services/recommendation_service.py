from typing import Dict, List, Union

from app.services.availability_parser import parse_availability
from app.services.gemini_client import GeminiClient
from app.services.scheduler import schedule_interview


def _fallback_reasoning(result: Dict[str, object]) -> str:
    top_slots = result.get("top_slots", [])
    conflicts = result.get("conflicts", [])
    final_rec = result.get("final_recommendation", "")

    if not top_slots:
        return "No valid common slot was found. Please collect more interviewer availability or broaden candidate time windows."

    reason = f"Selected {final_rec} because it maximizes candidate-interviewer overlap and appears earliest among top-scoring options."
    if conflicts:
        reason += f" Conflicts detected: {'; '.join(conflicts[:2])}."
    if len(top_slots) > 1:
        reason += f" Fallback options include {', '.join(top_slots[1:])}."
    return reason


def build_schedule_response(
    candidate_input: Union[str, List[Dict[str, str]]],
    interviewer_input: Dict[str, Union[str, List[Dict[str, str]]]],
    gemini_client: GeminiClient,
) -> Dict[str, object]:
    candidate_intervals = parse_availability(candidate_input, gemini_client)

    parsed_interviewers: Dict[str, List[Dict[str, str]]] = {}
    for interviewer, availability in interviewer_input.items():
        parsed_interviewers[interviewer] = parse_availability(availability, gemini_client)

    scheduling = schedule_interview(candidate_intervals, parsed_interviewers)

    try:
        reasoning = gemini_client.generate_reasoning(scheduling["reasoning_context"])
    except Exception:
        reasoning = _fallback_reasoning(scheduling)

    return {
        "top_slots": scheduling["top_slots"],
        "conflicts": scheduling["conflicts"],
        "final_recommendation": scheduling["final_recommendation"],
        "reasoning": reasoning,
    }
