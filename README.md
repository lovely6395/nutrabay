# Interview Scheduling Automation System (MVP)

An MVP backend that automates interview slot suggestions by combining candidate and interviewer availability.

## Tech Stack

- Python 3.10+
- FastAPI
- Gemini API (Google Generative AI)

## Project Structure

```text
app/
	main.py
	models/
		schemas.py
	services/
		gemini_client.py
		availability_parser.py
		scheduler.py
		recommendation_service.py
sample_run.py
requirements.txt
.env.example
```

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
copy .env.example .env
```

Set your Gemini key in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

## Run API

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

## API Contract

### POST `/schedule`

Input example:

```json
{
	"candidate_availability": "Tue-Thu 2-5 PM, Fri 9 AM-12 PM",
	"interviewer_availability": {
		"Interviewer A": "Tue 3-6 PM",
		"Interviewer B": "Tue 1-4 PM",
		"Interviewer C": "Wed 2-5 PM"
	},
	"timezone": "UTC"
}
```

Strict output format:

```json
{
	"top_slots": [],
	"conflicts": [],
	"final_recommendation": "",
	"reasoning": ""
}
```

## Sample Test Execution

Run:

```bash
python sample_run.py
```

Expected behavior for sample input:

- Top slots include `Tue 3 PM-4 PM`.
- Final recommendation prefers max interviewer overlap and earliest slot.

## Module Summary (MVP)

1. Input Parser
- Uses Gemini to parse natural language into `{day, start, end}`.
- Includes deterministic regex fallback.

2. Time Normalization Engine
- Converts to 24-hour format.
- Splits into 1-hour slots.

3. Overlap Detection Engine
- Computes candidate and interviewer intersections.
- Scores by interviewer count.

4. Ranking Algorithm
- Sorts by highest overlap, then earliest day/time.
- Returns top 3.

5. Conflict Detection
- Flags missing, partial, and no-overlap conditions.

6. LLM Reasoning Layer
- Gemini generates human-readable reasoning and fallback suggestions.
- Uses deterministic fallback reasoning if Gemini is unavailable.