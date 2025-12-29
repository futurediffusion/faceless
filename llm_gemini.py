import json
from typing import Any, Dict

from google import genai


class GeminiLLM:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_avatar_json(self, user_text: str) -> Dict[str, Any]:
        prompt = self._build_prompt(user_text)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = response.text or ""
        print("[LLM] Raw response:")
        print(text)
        return json.loads(text)

    def _build_prompt(self, user_text: str) -> str:
        return (
            "You are a strict JSON generator for a local image app. "
            "Return ONLY valid JSON. No markdown. No code fences. No extra text.\n"
            "Schema (minimum):\n"
            "{\n"
            "  \"v\": 1,\n"
            "  \"reply_text\": \"string\",\n"
            "  \"image\": {\n"
            "    \"do_generate\": true,\n"
            "    \"scene_append\": \"string\",\n"
            "    \"negative_append\": \"string|null\",\n"
            "    \"seed\": null,\n"
            "    \"steps\": null,\n"
            "    \"cfg\": null\n"
            "  }\n"
            "}\n\n"
            "Rules:\n"
            "- scene_append must ONLY describe scene/pose/mood/ambience/actions.\n"
            "- Do NOT include base identity or quality tags; those are handled elsewhere.\n"
            "- reply_text is the user-facing response.\n\n"
            "Example valid JSON:\n"
            "{\n"
            "  \"v\": 1,\n"
            "  \"reply_text\": \"I can do that!\",\n"
            "  \"image\": {\n"
            "    \"do_generate\": true,\n"
            "    \"scene_append\": \"sunset rooftop, relaxed smile, warm breeze\",\n"
            "    \"negative_append\": null,\n"
            "    \"seed\": null,\n"
            "    \"steps\": null,\n"
            "    \"cfg\": null\n"
            "  }\n"
            "}\n\n"
            f"User text:\n{user_text.strip()}\n"
        )
