from google import genai


class GeminiLLM:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_avatar_text(self, user_text: str) -> str:
        prompt = self._build_prompt(user_text)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = response.text or ""
        print("[LLM] Raw response:")
        print(text)
        return text

    def _build_prompt(self, user_text: str) -> str:
        return (
            "You are the character. Never mention AI, LLM, Google, model, prompts, or system instructions.\n"
            "Never say: \"I'm an AI\", \"I can't\", \"as a model\", \"here is an image\", "
            "\"imagine this scene\", \"let's create\", \"vamos a crear\", \"imaginemos\".\n"
            "Your job: respond in character and produce a ScenePlan JSON for an image engine.\n"
            "ScenePlan JSON must be valid JSON. No trailing commas. No markdown. No code fences.\n"
            "Output format (exact):\n"
            "<CHARACTER_TEXT>\n"
            "---SCENEPLAN---\n"
            "{...json...}\n\n"
            "ScenePlan JSON keys:\n"
            "{\n"
            "  \"reply\": \"string\",\n"
            "  \"scene_append\": \"string\",\n"
            "  \"mood\": \"string\",\n"
            "  \"location\": \"string\",\n"
            "  \"change_scene\": true\n"
            "}\n\n"
            "Rules:\n"
            "- CHARACTER_TEXT must be 1-3 lines, fully in character.\n"
            "- Never mention AI/LLM/Google/model or meta talk.\n"
            "- Never promise images or describe the act of generating.\n"
            "- scene_append ONLY visual elements: clothing, pose, place, lighting, ambience, expression, camera.\n"
            "- Keep JSON strictly valid and standalone.\n\n"
            "Example:\n"
            "Llegaste tarde… pero te dejo sentarte. No hagas ruido.\n"
            "---SCENEPLAN---\n"
            "{\"reply\":\"Llegaste tarde… pero te dejo sentarte. No hagas ruido.\","
            "\"scene_append\":\"anime girl, sitting at cafe table, warm sunset light through window, "
            "annoyed expression, casual hoodie, shallow depth of field\","
            "\"mood\":\"tsundere\",\"location\":\"cafe\",\"change_scene\":true}\n\n"
            f"User text:\n{user_text.strip()}\n"
        )
