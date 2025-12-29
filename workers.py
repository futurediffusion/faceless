import threading
import uuid
from dataclasses import replace
from typing import Any, Dict

from PySide6.QtCore import QObject, Signal

from comfy_client import ComfyClient
from llm_gemini import GeminiLLM
from models import CharacterParams, GenParams
from scene_plan import has_strong_scene_change, parse_scene_plan
from workflow_patcher import patch_workflow


class WorkerSignals(QObject):
    status = Signal(str)
    image = Signal(bytes)
    reply = Signal(str)
    done = Signal()


class GenerateWorker(threading.Thread):
    def __init__(
        self,
        client: ComfyClient,
        prompt_graph: Dict[str, Any],
        char_params: CharacterParams,
        append_text: str,
        gen_params: GenParams,
    ):
        super().__init__(daemon=True)
        self.client = client
        self.prompt_graph = prompt_graph
        self.char_params = char_params
        self.append_text = append_text
        self.gen_params = gen_params
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.status.emit("…")
            graph = patch_workflow(self.prompt_graph, self.char_params, self.append_text, self.gen_params)

            client_id = str(uuid.uuid4())
            self.signals.status.emit("…")
            prompt_id = self.client.queue_prompt(graph, client_id)

            self.signals.status.emit("…")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit("…")
            img_bytes = self.client.download_image(imgref)

            self.signals.image.emit(img_bytes)
            self.signals.status.emit("")
        except Exception as e:
            self.signals.status.emit(f"ERROR: {e}")
            print(f"[ERROR] {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.signals.done.emit()


class ChatGenerateWorker(threading.Thread):
    def __init__(
        self,
        client: ComfyClient,
        prompt_graph: Dict[str, Any],
        char_params: CharacterParams,
        user_text: str,
        gen_params: GenParams,
        api_key: str,
    ):
        super().__init__(daemon=True)
        self.client = client
        self.prompt_graph = prompt_graph
        self.char_params = char_params
        self.user_text = user_text
        self.gen_params = gen_params
        self.api_key = api_key
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.status.emit("…")
            llm = GeminiLLM(self.api_key)
            raw_text = llm.generate_avatar_text(self.user_text)
            scene_plan = parse_scene_plan(raw_text, self.user_text)
            print("[LLM] ScenePlan:")
            print(scene_plan)

            scene_append = scene_plan.scene_append
            print(f"[LLM] scene_append: {scene_append}")

            should_generate = scene_plan.change_scene or has_strong_scene_change(scene_append)
            if not should_generate:
                self.signals.reply.emit(scene_plan.reply)
                self.signals.status.emit("")
                return

            run_params = replace(self.gen_params)

            self.signals.status.emit("…")
            graph = patch_workflow(self.prompt_graph, self.char_params, scene_append, run_params)

            client_id = str(uuid.uuid4())
            self.signals.status.emit("…")
            prompt_id = self.client.queue_prompt(graph, client_id)

            self.signals.status.emit("…")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit("…")
            img_bytes = self.client.download_image(imgref)

            self.signals.image.emit(img_bytes)
            self.signals.reply.emit(scene_plan.reply)
            self.signals.status.emit("")
        except Exception as e:
            self.signals.status.emit(f"ERROR: {e}")
            print(f"[ERROR] {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.signals.done.emit()
