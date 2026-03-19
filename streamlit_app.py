import json
from typing import Any, Dict, List

import streamlit as st

from app.services.gemini_client import GeminiClient
from app.services.recommendation_service import build_schedule_response

SAMPLE_CANDIDATE = "Tue 2-5 PM"
SAMPLE_INTERVIEWERS = {
    "Interviewer A": "Tue 3-6 PM",
    "Interviewer B": "Tue 1-4 PM",
    "Interviewer C": "Wed 2-5 PM",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

            :root {
                --bg-1: #0f172a;
                --bg-2: #111827;
                --panel: rgba(255, 255, 255, 0.08);
                --panel-strong: rgba(255, 255, 255, 0.12);
                --text: #f8fafc;
                --muted: #cbd5e1;
                --accent: #0ea5a4;
                --accent-2: #f59e0b;
            }

            .stApp {
                background:
                    radial-gradient(1200px 600px at -5% -10%, rgba(14, 165, 164, 0.22), transparent 60%),
                    radial-gradient(900px 420px at 105% 0%, rgba(245, 158, 11, 0.18), transparent 60%),
                    linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 70%);
                color: var(--text);
            }

            h1, h2, h3 {
                font-family: 'Space Grotesk', sans-serif !important;
                letter-spacing: 0.01em;
            }

            p, li, label, span, div {
                font-family: 'Manrope', sans-serif !important;
            }

            .hero {
                padding: 1.2rem 1.4rem;
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.16);
                background: linear-gradient(135deg, rgba(14,165,164,0.18), rgba(245,158,11,0.16));
                box-shadow: 0 20px 40px rgba(2, 6, 23, 0.3);
                animation: rise 450ms ease-out;
            }

            .subtle {
                color: var(--muted);
                margin-top: 0.3rem;
            }

            .slot-card {
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.16);
                background: var(--panel);
                padding: 0.9rem 1rem;
                margin-bottom: 0.6rem;
                animation: rise 450ms ease-out;
            }

            .slot-rank {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #fde68a;
                margin-bottom: 0.2rem;
            }

            .slot-time {
                font-size: 1.05rem;
                font-weight: 700;
            }

            .badge {
                display: inline-block;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 999px;
                font-size: 0.75rem;
                padding: 0.16rem 0.58rem;
                color: #e2e8f0;
                margin-left: 0.35rem;
            }

            @keyframes rise {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0px); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_json_input(json_text: str, expected_type: type) -> Any:
    parsed = json.loads(json_text)
    if not isinstance(parsed, expected_type):
        type_name = "array" if expected_type is list else "object"
        raise ValueError(f"Expected JSON {type_name}.")
    return parsed


def init_state() -> None:
    if "candidate_text" not in st.session_state:
        st.session_state.candidate_text = SAMPLE_CANDIDATE

    if "candidate_structured" not in st.session_state:
        st.session_state.candidate_structured = json.dumps(
            [{"day": "Tuesday", "start": "14:00", "end": "17:00"}],
            indent=2,
        )

    if "interviewer_rows" not in st.session_state:
        st.session_state.interviewer_rows = [
            {"name": "Interviewer A", "availability": "Tue 3-6 PM"},
            {"name": "Interviewer B", "availability": "Tue 1-4 PM"},
            {"name": "Interviewer C", "availability": "Wed 2-5 PM"},
        ]

    if "interviewer_structured" not in st.session_state:
        st.session_state.interviewer_structured = json.dumps(
            {
                "Interviewer A": [{"day": "Tuesday", "start": "15:00", "end": "18:00"}],
                "Interviewer B": [{"day": "Tuesday", "start": "13:00", "end": "16:00"}],
                "Interviewer C": [{"day": "Wednesday", "start": "14:00", "end": "17:00"}],
            },
            indent=2,
        )

    if "timezone" not in st.session_state:
        st.session_state.timezone = "UTC"

    if "history" not in st.session_state:
        st.session_state.history = []


def build_interviewer_map_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    auto_idx = 1
    for row in rows:
        if not isinstance(row, dict):
            continue

        name = str(row.get("name", "")).strip()
        availability = str(row.get("availability", "")).strip()
        if not availability:
            continue

        if not name:
            name = f"Interviewer {auto_idx}"
            auto_idx += 1

        result[name] = availability

    return result


def render_slots(top_slots: List[str], recommendation: str) -> None:
    st.subheader("Top 3 Suggested Slots")
    if not top_slots:
        st.warning("No common slots found. Update availability windows and try again.")
        return

    for idx, slot in enumerate(top_slots, start=1):
        is_best = slot == recommendation
        badge = '<span class="badge">Best Match</span>' if is_best else ""
        st.markdown(
            (
                '<div class="slot-card">'
                f'<div class="slot-rank">Rank {idx}</div>'
                f'<div class="slot-time">{slot}{badge}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Interview Scheduling Assistant",
        page_icon="calendar",
        layout="wide",
    )
    inject_styles()
    init_state()

    gemini_client = GeminiClient()

    st.markdown(
        """
        <div class="hero">
            <h1 style="margin:0;">Interview Scheduling Automation</h1>
            <p class="subtle">Find the best interview window from candidate and interviewer availability in seconds.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([2.2, 1], gap="large")

    with right:
        st.subheader("System Status")
        st.metric("Gemini", "Enabled" if gemini_client.enabled else "Fallback Mode")
        st.caption("Fallback mode still schedules slots using deterministic parsing.")

        st.text_input("Timezone", key="timezone")

        if st.button("Load Sample Data", use_container_width=True):
            st.session_state.candidate_text = SAMPLE_CANDIDATE
            st.session_state.interviewer_rows = [
                {"name": name, "availability": availability}
                for name, availability in SAMPLE_INTERVIEWERS.items()
            ]
            st.success("Sample values loaded.")

        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.info("History cleared.")

    with left:
        st.subheader("Inputs")

        candidate_mode = st.radio(
            "Candidate Availability Input",
            ["Natural language", "Structured JSON"],
            horizontal=True,
        )

        if candidate_mode == "Natural language":
            candidate_input = st.text_area(
                "Candidate availability",
                key="candidate_text",
                help="Example: Tue-Thu 2-5 PM, Fri 9 AM-12 PM",
                height=96,
            )
        else:
            candidate_json = st.text_area(
                "Candidate structured JSON array",
                key="candidate_structured",
                height=140,
            )
            candidate_input = parse_json_input(candidate_json, list)

        interviewer_mode = st.radio(
            "Interviewer Availability Input",
            ["Interactive table", "Structured JSON"],
            horizontal=True,
        )

        if interviewer_mode == "Interactive table":
            st.caption("Add 3-5 interviewers (or more) and write availability in natural language.")
            rows = st.data_editor(
                st.session_state.interviewer_rows,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Interviewer Name", required=False),
                    "availability": st.column_config.TextColumn(
                        "Availability",
                        required=False,
                        help="Example: Tue 3-6 PM",
                    ),
                },
            )
            interviewer_input = build_interviewer_map_from_rows(rows)
            st.session_state.interviewer_rows = rows
        else:
            interviewer_json = st.text_area(
                "Interviewer structured JSON object",
                key="interviewer_structured",
                height=220,
            )
            interviewer_input = parse_json_input(interviewer_json, dict)

        with st.expander("Request payload preview"):
            st.json(
                {
                    "candidate_availability": candidate_input,
                    "interviewer_availability": interviewer_input,
                    "timezone": st.session_state.timezone,
                }
            )

        if st.button("Generate Schedule", type="primary", use_container_width=True):
            try:
                if not interviewer_input:
                    raise ValueError("Add at least one interviewer with availability.")

                response = build_schedule_response(
                    candidate_input=candidate_input,
                    interviewer_input=interviewer_input,
                    gemini_client=gemini_client,
                )

                st.session_state.history.insert(
                    0,
                    {
                        "candidate": candidate_input,
                        "interviewers": interviewer_input,
                        "result": response,
                    },
                )

                st.success("Schedule generated.")

                metrics = st.columns(3)
                metrics[0].metric("Suggested Slots", len(response["top_slots"]))
                metrics[1].metric("Conflicts", len(response["conflicts"]))
                metrics[2].metric("Final Recommendation", response["final_recommendation"] or "None")

                render_slots(response["top_slots"], response["final_recommendation"])

                st.subheader("Conflict Detection")
                if response["conflicts"]:
                    for conflict in response["conflicts"]:
                        st.error(conflict)
                else:
                    st.success("No conflicts found.")

                st.subheader("Reasoning")
                st.info(response["reasoning"])

                st.subheader("Strict JSON Output")
                st.code(json.dumps(response, indent=2), language="json")
            except Exception as exc:
                st.error(f"Failed to generate schedule: {exc}")

    st.subheader("Run History")
    if not st.session_state.history:
        st.caption("No runs yet. Generate a schedule to populate history.")
    else:
        for idx, item in enumerate(st.session_state.history[:5], start=1):
            with st.expander(f"Run {idx} - {item['result'].get('final_recommendation', 'No recommendation')}"):
                st.write("Candidate")
                st.write(item["candidate"])
                st.write("Interviewers")
                st.json(item["interviewers"])
                st.write("Result")
                st.json(item["result"])


if __name__ == "__main__":
    main()
