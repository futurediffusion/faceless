from typing import Callable, List, Optional

from ollama import ResponseError, chat, list as ollama_list, pull, show


class OllamaLLM:
    def __init__(self, model: str = "qwen2.5:7b-instruct"):
        self.model = model

    def is_running(self) -> bool:
        try:
            ollama_list()
        except Exception:
            return False
        return True

    def ensure_model(self, status_cb: Optional[Callable[[str], None]] = None) -> None:
        try:
            show(self.model)
            return
        except ResponseError as exc:
            if exc.status_code == 404:
                if status_cb:
                    status_cb("Downloading model…")
                pull(self.model)
                return
            raise RuntimeError(f"Ollama error: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    def generate(self, messages: List[dict]) -> str:
        if not self.is_running():
            raise RuntimeError("Ollama is not running. Start it with `ollama serve`.")

        def _run_chat() -> str:
            resp = chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.6, "top_p": 0.9, "num_ctx": 4096},
            )
            return (resp.get("message") or {}).get("content", "")

        try:
            return _run_chat()
        except ResponseError as exc:
            if exc.status_code == 404:
                pull(self.model)
                return _run_chat()
            raise RuntimeError(f"Ollama error: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc
