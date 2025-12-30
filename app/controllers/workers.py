import threading
import uuid
from dataclasses import replace
from typing import Any, Dict

from PySide6.QtCore import QObject, Signal

from app.core.comfy_client import ComfyClient
from llm_contract import build_messages, build_system_prompt
from llm_gemini import GeminiLLM
from llm_ollama import OllamaLLM
from models import CharacterParams, GenParams
from sceneplan_parser import parse_sceneplan
from app.core.world_state import WorldState
from app.core.workflow_patcher import patch_workflow


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
            self.signals.status.emit("Parchando workflow…")
            print("[WORKER] Phase 1: Patching workflow")
            graph = patch_workflow(self.prompt_graph, self.char_params, self.append_text, self.gen_params)
            print("[WORKER] Workflow patched successfully")

            client_id = str(uuid.uuid4())
            self.signals.status.emit("Encolando en ComfyUI…")
            print(f"[WORKER] Phase 2: Queueing to ComfyUI (client_id={client_id})")
            prompt_id = self.client.queue_prompt(graph, client_id)
            print(f"[WORKER] Prompt queued: {prompt_id}")

            self.signals.status.emit("Esperando resultado…")
            print("[WORKER] Phase 3: Waiting for history")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit("Descargando imagen…")
            print("[WORKER] Phase 4: Downloading image")
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
        provider: str,
        api_key: str,
        ollama_model: str,
        world_state: WorldState,
    ):
        super().__init__(daemon=True)
        self.client = client
        self.prompt_graph = prompt_graph
        self.char_params = char_params
        self.user_text = user_text
        self.gen_params = gen_params
        self.provider = provider
        self.api_key = api_key
        self.ollama_model = ollama_model
        self.world_state = world_state
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.status.emit("Llamando LLM…")
            print("[WORKER] Phase 1: Calling LLM")
            system_prompt = build_system_prompt(self.world_state.build_llm_context())
            messages = build_messages(self.user_text, self.world_state.history, system_prompt)
            if self.provider == "gemini":
                llm = GeminiLLM(self.api_key)
                raw_text = llm.generate_avatar_text(messages)
            elif self.provider == "ollama":
                llm = OllamaLLM(self.ollama_model)
                raw_text = llm.generate(messages)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
            print(f"[WORKER] LLM response length: {len(raw_text)} chars")
            self.signals.status.emit("Procesando ScenePlan…")
            print("[WORKER] Phase 2: Parsing ScenePlan")
            scene_plan = parse_sceneplan(raw_text)
            print("[LLM] ScenePlan:")
            print(scene_plan)

            scene_append = scene_plan.scene_append
            print(f"[LLM] scene_append: {scene_append}")

            current_anchor = self.world_state.visual_anchor
            anchor_for_prompt = current_anchor
            if scene_plan.change_scene and scene_plan.visual_anchor:
                anchor_for_prompt = scene_plan.visual_anchor

            append_parts = []
            if anchor_for_prompt:
                append_parts.append(anchor_for_prompt)
            if scene_append:
                append_parts.append(scene_append)
            prompt_append = ", ".join(append_parts)

            run_params = replace(self.gen_params)

            self.signals.status.emit("Parchando workflow…")
            print("[WORKER] Phase 3: Patching workflow")
            graph = patch_workflow(self.prompt_graph, self.char_params, prompt_append, run_params)
            print("[WORKER] Workflow patched successfully")

            client_id = str(uuid.uuid4())
            self.signals.status.emit("Encolando en ComfyUI…")
            print(f"[WORKER] Phase 4: Queueing to ComfyUI (client_id={client_id})")
            prompt_id = self.client.queue_prompt(graph, client_id)
            print(f"[WORKER] Prompt queued: {prompt_id}")

            self.signals.status.emit("Esperando resultado…")
            print("[WORKER] Phase 5: Waiting for history")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit("Descargando imagen…")
            print("[WORKER] Phase 6: Downloading image")
            img_bytes = self.client.download_image(imgref)

            self.world_state.apply_sceneplan(scene_plan)
            self.world_state.add_turn(self.user_text, scene_plan.reply, scene_plan)

            self.signals.image.emit(img_bytes)
            self.signals.reply.emit(scene_plan.reply)
            self.signals.status.emit("")
        except TimeoutError:
            print("[WORKER] Timeout waiting for ComfyUI history")
            self.signals.status.emit("Comfy no devolvió resultado. Revisa consola/VRAM.")
        except Exception as e:
            self.signals.status.emit(f"ERROR: {e}")
            print(f"[ERROR] {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.signals.done.emit()
