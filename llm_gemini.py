from google import genai

from llm_contract import render_messages_for_prompt


class GeminiLLM:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_avatar_text(self, messages: list) -> str:
        prompt = render_messages_for_prompt(messages)
        response = self.client.models.generate_content(model=self.model, contents=prompt)
        text = response.text or ""
        print("[LLM] Raw response:")
        print(text)
        return text
