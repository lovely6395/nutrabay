from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from app.services.availability_parser import DAY_ORDER


@dataclass(frozen=True)
class Slot:
    day: str
    hour: int


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _minutes_to_12h(minutes: int) -> str:
    hour = minutes // 60
    minute = minutes % 60
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12
    if minute == 0:
        return f"{hour12} {suffix}"
    return f"{hour12}:{minute:02d} {suffix}"


def _slot_to_human(slot: Slot) -> str:
    start = slot.hour * 60
    end = start + 60
    return f"{slot.day[:3]} {_minutes_to_12h(start)}-{_minutes_to_12h(end)}"


def normalize_to_hour_slots(intervals: List[Dict[str, str]]) -> Set[Slot]:
    slots: Set[Slot] = set()
    for interval in intervals:
        day = interval["day"]
        start_min = _time_to_minutes(interval["start"])
        end_min = _time_to_minutes(interval["end"])

        cursor = start_min
        while cursor + 60 <= end_min:
            slots.add(Slot(day=day, hour=cursor // 60))
            cursor += 60
    return slots


def _sort_key(slot: Slot) -> Tuple[int, int]:
    return (DAY_ORDER.index(slot.day), slot.hour)


def schedule_interview(
    candidate_intervals: List[Dict[str, str]],
    interviewer_intervals: Dict[str, List[Dict[str, str]]],
) -> Dict[str, object]:
    candidate_slots = normalize_to_hour_slots(candidate_intervals)

    interviewer_slots = {
        name: normalize_to_hour_slots(intervals)
        for name, intervals in interviewer_intervals.items()
    }

    slot_scores: Dict[Slot, int] = defaultdict(int)
    slot_present_interviewers: Dict[Slot, List[str]] = defaultdict(list)

    for slot in candidate_slots:
        for interviewer, slots in interviewer_slots.items():
            if slot in slots:
                slot_scores[slot] += 1
                slot_present_interviewers[slot].append(interviewer)

    ranked_slots = sorted(
        slot_scores.keys(),
        key=lambda s: (-slot_scores[s], _sort_key(s)),
    )

    top_slots = [_slot_to_human(slot) for slot in ranked_slots[:3]]
    final_recommendation = top_slots[0] if top_slots else ""

    conflicts: List[str] = []
    if not candidate_slots:
        conflicts.append("Candidate availability could not be converted into valid 1-hour slots.")

    for interviewer, slots in interviewer_slots.items():
        if not slots:
            conflicts.append(f"Missing or invalid availability for {interviewer}.")
            continue

        overlap = candidate_slots.intersection(slots)
        if not overlap:
            conflicts.append(f"No overlap between candidate and {interviewer}.")
        elif len(overlap) < len(candidate_slots):
            conflicts.append(f"Partial overlap with {interviewer}.")

    if not top_slots:
        conflicts.append("No common interview slot found.")

    reasoning_context = {
        "top_slots": top_slots,
        "final_recommendation": final_recommendation,
        "slot_scores": {
            _slot_to_human(slot): slot_scores[slot] for slot in ranked_slots[:3]
        },
        "interviewer_presence": {
            _slot_to_human(slot): slot_present_interviewers[slot]
            for slot in ranked_slots[:3]
        },
        "conflicts": conflicts,
    }

    return {
        "top_slots": top_slots,
        "conflicts": conflicts,
        "final_recommendation": final_recommendation,
        "reasoning_context": reasoning_context,
    }
