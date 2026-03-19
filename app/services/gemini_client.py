import json
import os
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> None:
        return None

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


class GeminiClient:
    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.enabled = bool(self.api_key and genai is not None)

        if self.enabled:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def _extract_json(self, text: str) -> Any:
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                text = text.replace("json", "", 1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def parse_availability(self, availability_text: str) -> List[Dict[str, str]]:
        if not self.enabled:
            raise RuntimeError("Gemini is not configured.")

        prompt = (
            "Convert the following availability into a JSON array of objects only. "
            "Each object must have keys: day, start, end. "
            "Use full day names and 24-hour HH:MM format. "
            "Do not include explanation text.\n\n"
            f"Availability: {availability_text}"
        )

        response = self.model.generate_content(prompt)
        parsed = self._extract_json(response.text)
        if not isinstance(parsed, list):
            raise ValueError("Gemini parser response is not a JSON array.")
        return parsed

    def generate_reasoning(self, context: Dict[str, Any]) -> str:
        if not self.enabled:
            raise RuntimeError("Gemini is not configured.")

        prompt = (
            "You are an interview scheduling assistant. "
            "Using the JSON context, produce a concise recommendation explanation in 2-4 sentences. "
            "Mention overlap count, conflict highlights, and one fallback option.\n\n"
            f"Context JSON: {json.dumps(context)}"
        )

        response = self.model.generate_content(prompt)
        return response.text.strip()
