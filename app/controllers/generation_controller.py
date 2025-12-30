from PySide6.QtCore import Qt

from app.controllers.workers import ChatGenerateWorker
from app.core.comfy_client import ComfyClient
from models import CharacterParams, GenParams
from app.core.world_state import WorldState


class GenerationController:
    def __init__(self, on_status, on_image, on_reply, on_done):
        self._on_status = on_status
        self._on_image = on_image
        self._on_reply = on_reply
        self._on_done = on_done

    def _handle_reply(self, text: str) -> None:
        print("[GEN_CONTROLLER] Signal reply emitted")
        self._on_reply(text)

    def start_chat_generation(
        self,
        client: ComfyClient,
        prompt_graph: dict,
        char_params: CharacterParams,
        user_text: str,
        gen_params: GenParams,
        provider: str,
        gemini_api_key: str,
        openai_api_key: str,
        openai_model: str,
        ollama_model: str,
        world_state: WorldState,
    ) -> None:
        print("[GEN_CONTROLLER] Creating worker and connecting signals")
        worker = ChatGenerateWorker(
            client,
            prompt_graph,
            char_params,
            user_text,
            gen_params,
            provider,
            gemini_api_key,
            openai_api_key,
            openai_model,
            ollama_model,
            world_state,
        )
        # Use Qt.QueuedConnection for cross-thread signals
        worker.signals.status.connect(self._on_status, Qt.QueuedConnection)
        worker.signals.image.connect(self._on_image, Qt.QueuedConnection)
        worker.signals.reply.connect(self._handle_reply, Qt.QueuedConnection)
        worker.signals.done.connect(self._on_done, Qt.QueuedConnection)
        print("[GEN_CONTROLLER] Signals connected, starting worker")
        worker.start()
