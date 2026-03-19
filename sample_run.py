import json

from app.services.gemini_client import GeminiClient
from app.services.recommendation_service import build_schedule_response


def main() -> None:
    candidate = "Tue 2-5 PM"
    interviewers = {
        "Interviewer A": "Tue 3-6 PM",
        "Interviewer B": "Tue 1-4 PM",
        "Interviewer C": "Wed 2-5 PM",
    }

    response = build_schedule_response(candidate, interviewers, GeminiClient())
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
