import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal

from app.controllers.generation_controller import GenerationController
from app.core.comfy_client import ComfyClient
from app.core.workflow_patcher import detect_cliptext_nodes
from app.core.world_state import WorldState
from app.ui.dialogs import ApiKeysDialog, CharacterDialog, ConnectionDialog, ParamsDialog
from app.ui.main_window import MainWindow
from config_store import load_config, save_config
from llm_ollama import OllamaLLM
from models import CharacterParams, GenParams


class StatusSignals(QObject):
    status = Signal(str)


class AppController:
    def __init__(self):
        self.window = MainWindow()
        self.window.generate_requested.connect(self.on_generate)
        self.window.open_character_requested.connect(self.open_character_dialog)
        self.window.open_api_keys_requested.connect(self.open_api_keys_dialog)
        self.window.open_connection_requested.connect(self.open_connection_dialog)
        self.window.open_params_requested.connect(self.open_params_dialog)

        self.base_dir = Path(__file__).resolve().parents[2]
        self.workflow_path = self.base_dir / "facelessbase.json"
        self.config = load_config(self.base_dir)

        self.prompt_graph: Optional[Dict[str, Any]] = None
        self.params = GenParams()
        self.char_params = CharacterParams()
        self.world_state = WorldState(identity_profile=self.char_params.identity_profile)
        self.comfy_url = "http://127.0.0.1:8188"
        self.available_loras: list[str] = []
        self.available_checkpoints: list[str] = []
        self.comfy_busy = False
        self.connection_ok = False
        self.status_signals = StatusSignals()
        self.status_signals.status.connect(self.window.set_status)

        self.generation_controller = GenerationController(
            self.window.set_status,
            self.on_image,
            self.on_reply_text,
            self.on_worker_done,
        )

        self.load_workflow(self.workflow_path)
        self.test_connection_silent()
        self.bootstrap_ollama()

    def show(self):
        self.window.show()

    def load_workflow(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "nodes" in data:
                self.prompt_graph = None
                return

            if not isinstance(data, dict):
                raise ValueError("Workflow must be dict")

            self.prompt_graph = data
            pos_id, neg_id = detect_cliptext_nodes(data)
            print(f"[INFO] Workflow loaded. Nodes: pos={pos_id}, neg={neg_id}")

        except Exception as e:
            self.prompt_graph = None
            print(f"[ERROR] Workflow load failed: {e}")

        self.refresh_generate_state()

    def refresh_generate_state(self):
        provider = self.config.get("llm_provider", "gemini").lower()
        has_provider = True
        if provider == "gemini":
            has_provider = bool(self.config.get("gemini_api_key"))
        elif provider == "ollama":
            has_provider = bool(self.config.get("ollama_model"))
        else:
            has_provider = False

        allow_while_busy = not self.config.get("prefer_ollama_while_busy", True)
        busy_block = self.comfy_busy and not allow_while_busy
        can_generate = self.connection_ok and self.prompt_graph is not None and has_provider and not busy_block
        self.window.set_generate_enabled(can_generate)

    def test_connection_silent(self):
        client = ComfyClient(self.comfy_url)
        self.connection_ok = client.ping()
        self.refresh_generate_state()
        print(f"[INFO] Connection: {'✅' if self.connection_ok else '❌'}")

    def bootstrap_ollama(self):
        if self.config.get("llm_provider", "gemini").lower() != "ollama":
            return

        model = self.config.get("ollama_model") or "qwen2.5:7b-instruct"

        def run():
            try:
                self.status_signals.status.emit("Checking Ollama model…")
                llm = OllamaLLM(model=model)
                llm.ensure_model(lambda msg: self.status_signals.status.emit(msg))
                self.status_signals.status.emit("")
            except Exception as exc:
                self.status_signals.status.emit(f"❌ {exc}")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def open_character_dialog(self):
        client = ComfyClient(self.comfy_url)
        self.available_loras = client.get_loras()

        dialog = CharacterDialog(self.char_params, self.available_loras, self.window)
        if dialog.exec():
            self.char_params = dialog.get_params()
            self.world_state.update_identity_profile(self.char_params.identity_profile)
            print(
                f"[INFO] Character updated: LoRA={self.char_params.lora_name or '(None)'} @ {self.char_params.lora_strength}"
            )

    def open_api_keys_dialog(self):
        dialog = ApiKeysDialog(self.config, self.window)
        if dialog.exec():
            self.config.update(dialog.get_config())
            save_config(self.base_dir / "config.json", self.config)
            print("[INFO] API keys updated")
            self.refresh_generate_state()
            self.bootstrap_ollama()

    def open_connection_dialog(self):
        dialog = ConnectionDialog(self.comfy_url, self.window)
        if dialog.exec():
            self.comfy_url = dialog.get_url()
            self.test_connection_silent()

    def open_params_dialog(self):
        client = ComfyClient(self.comfy_url)
        self.available_checkpoints = client.get_checkpoints()

        dialog = ParamsDialog(self.params, self.available_checkpoints, self.window)
        if dialog.exec():
            self.params = dialog.get_params()
            print("[INFO] Parameters updated")

    def on_generate(self, user_text: str):
        if not user_text:
            return

        provider = self.config.get("llm_provider", "gemini").lower()
        client = ComfyClient(self.comfy_url)
        if not client.ping():
            self.connection_ok = False
            self.refresh_generate_state()
            self.window.set_status("❌ Not connected")
            return
        self.connection_ok = True
        if self.prompt_graph is None:
            self.window.set_status("❌ Workflow not loaded")
            return
        if provider == "gemini" and not self.config.get("gemini_api_key"):
            self.window.set_status("❌ Missing GEMINI_API_KEY (set in ⚙ → API Keys...)")
            return
        if provider == "ollama" and not self.config.get("ollama_model"):
            self.window.set_status("❌ Missing Ollama model (set in ⚙ → API Keys...)")
            return

        self.comfy_busy = True
        self.refresh_generate_state()
        self.window.set_status("…")

        self.window.clear_reply()
        self.window.clear_input()

        self.generation_controller.start_chat_generation(
            client,
            self.prompt_graph,
            self.char_params,
            user_text,
            self.params,
            provider,
            self.config.get("gemini_api_key", ""),
            self.config.get("ollama_model", "qwen2.5:7b-instruct"),
            self.world_state,
        )

    def on_worker_done(self):
        self.comfy_busy = False
        self.refresh_generate_state()

    def on_image(self, data: bytes):
        print(f"[APP_CONTROLLER] on_image called with {len(data)} bytes")
        if not self.window.set_image_bytes(data):
            self.window.set_status("ERROR: decode failed")

    def on_reply_text(self, text: str):
        print(f"[APP_CONTROLLER] on_reply_text called with: '{text[:50]}...'")
        if text:
            self.window.show_reply(text)
