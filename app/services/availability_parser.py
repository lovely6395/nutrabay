import re
from typing import Dict, List, Optional

from app.services.gemini_client import GeminiClient

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

DAY_ALIASES = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}

SEGMENT_PATTERN = re.compile(
    r"(?P<days>[A-Za-z]{3,9}(?:\s*[-–]\s*[A-Za-z]{3,9})?)\s+"
    r"(?P<start>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\s*[-–]\s*"
    r"(?P<end>\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)"
)


def normalize_day(raw_day: str) -> str:
    key = raw_day.strip().lower()
    if key not in DAY_ALIASES:
        raise ValueError(f"Unknown day: {raw_day}")
    return DAY_ALIASES[key]


def _extract_meridiem(time_token: str) -> Optional[str]:
    token = time_token.strip().lower()
    if token.endswith("am"):
        return "am"
    if token.endswith("pm"):
        return "pm"
    return None


def _to_24h(time_token: str, fallback_meridiem: Optional[str] = None) -> str:
    token = time_token.strip().lower().replace(" ", "")
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)?$", token)
    if not match:
        raise ValueError(f"Invalid time token: {time_token}")

    hour = int(match.group(1))
    minute = int(match.group(2) or "00")
    meridiem = match.group(3) or fallback_meridiem

    if minute not in (0, 30):
        raise ValueError("Only :00 and :30 minutes are supported in MVP.")

    if meridiem:
        if hour < 1 or hour > 12:
            raise ValueError(f"Invalid 12-hour value: {time_token}")
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
    else:
        if hour < 0 or hour > 23:
            raise ValueError(f"Invalid 24-hour value: {time_token}")

    return f"{hour:02d}:{minute:02d}"


def _expand_days(days_expr: str) -> List[str]:
    tokens = re.split(r"[-–]", days_expr)
    tokens = [normalize_day(token) for token in tokens]

    if len(tokens) == 1:
        return tokens

    start_day, end_day = tokens[0], tokens[1]
    start_idx = DAY_ORDER.index(start_day)
    end_idx = DAY_ORDER.index(end_day)
    if start_idx <= end_idx:
        return DAY_ORDER[start_idx : end_idx + 1]

    return DAY_ORDER[start_idx:] + DAY_ORDER[: end_idx + 1]


def _fallback_parse_text(availability_text: str) -> List[Dict[str, str]]:
    intervals: List[Dict[str, str]] = []
    for segment in availability_text.split(","):
        segment = segment.strip()
        if not segment:
            continue

        match = SEGMENT_PATTERN.search(segment)
        if not match:
            continue

        days_expr = match.group("days")
        start_raw = match.group("start")
        end_raw = match.group("end")

        end_meridiem = _extract_meridiem(end_raw)
        start_meridiem = _extract_meridiem(start_raw) or end_meridiem

        start = _to_24h(start_raw, start_meridiem)
        end = _to_24h(end_raw, end_meridiem)

        for day in _expand_days(days_expr):
            intervals.append({"day": day, "start": start, "end": end})

    return intervals


def parse_availability(
    input_value: str | List[Dict[str, str]], gemini_client: GeminiClient
) -> List[Dict[str, str]]:
    if isinstance(input_value, list):
        normalized_items: List[Dict[str, str]] = []
        for item in input_value:
            if isinstance(item, dict):
                day = item.get("day")
                start = item.get("start")
                end = item.get("end")
            else:
                day = getattr(item, "day", None)
                start = getattr(item, "start", None)
                end = getattr(item, "end", None)

            if day is None or start is None or end is None:
                raise ValueError("Structured availability must include day, start, and end.")

            normalized_items.append(
                {
                    "day": normalize_day(str(day)),
                    "start": _to_24h(str(start)),
                    "end": _to_24h(str(end)),
                }
            )

        return [
            {
                "day": item["day"],
                "start": item["start"],
                "end": item["end"],
            }
            for item in normalized_items
        ]

    try:
        llm_intervals = gemini_client.parse_availability(input_value)
        normalized = []
        for item in llm_intervals:
            normalized.append(
                {
                    "day": normalize_day(str(item["day"])),
                    "start": _to_24h(str(item["start"])),
                    "end": _to_24h(str(item["end"])),
                }
            )
        if normalized:
            return normalized
    except Exception:
        pass

    fallback = _fallback_parse_text(input_value)
    if not fallback:
        raise ValueError("Unable to parse availability input.")
    return fallback
