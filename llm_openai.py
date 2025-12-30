from openai import OpenAI

from llm_contract import render_messages_for_prompt


class OpenAILLM:
    def __init__(self, api_key: str, model: str = "gpt-5-nano"):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_avatar_text(self, messages: list) -> str:
        prompt = render_messages_for_prompt(messages)
        response = self.client.responses.create(model=self.model, input=prompt)
        text = getattr(response, "output_text", "") or ""
        print("[LLM] Raw response:")
        print(text)
        return text
