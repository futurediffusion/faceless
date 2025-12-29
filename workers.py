import threading
import uuid
from dataclasses import replace
from typing import Any, Dict

from PySide6.QtCore import QObject, Signal

from comfy_client import ComfyClient
from llm_contract import validate_contract
from llm_gemini import GeminiLLM
from models import CharacterParams, GenParams
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
            self.signals.status.emit("Patching workflow…")
            graph = patch_workflow(self.prompt_graph, self.char_params, self.append_text, self.gen_params)

            client_id = str(uuid.uuid4())
            self.signals.status.emit("Queueing prompt…")
            prompt_id = self.client.queue_prompt(graph, client_id)

            self.signals.status.emit("Waiting for image…")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit(f"Downloading: {imgref.filename}")
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
            self.signals.status.emit("Calling Gemini…")
            llm = GeminiLLM(self.api_key)
            contract_raw = llm.generate_avatar_json(self.user_text)
            print("[LLM] Parsed contract:")
            print(contract_raw)
            contract = validate_contract(contract_raw)

            image_contract = contract.get("image", {})
            scene_append = image_contract.get("scene_append", "") or ""
            negative_append = image_contract.get("negative_append", "") or ""
            print(f"[LLM] scene_append: {scene_append}")
            print(f"[LLM] negative_append: {negative_append}")

            if not image_contract.get("do_generate", False):
                self.signals.reply.emit(contract.get("reply_text", ""))
                self.signals.status.emit("")
                return

            final_negative = self.gen_params.negative
            if negative_append:
                final_negative = f"{final_negative}, {negative_append}"
            print(f"[DEBUG] final_negative: {final_negative}")

            run_params = replace(self.gen_params, negative=final_negative)
            if image_contract.get("seed") is not None:
                run_params.seed = image_contract["seed"]
            if image_contract.get("steps") is not None:
                run_params.steps = image_contract["steps"]
            if image_contract.get("cfg") is not None:
                run_params.cfg = image_contract["cfg"]

            self.signals.status.emit("Patching workflow…")
            graph = patch_workflow(self.prompt_graph, self.char_params, scene_append, run_params)

            client_id = str(uuid.uuid4())
            self.signals.status.emit("Queueing prompt…")
            prompt_id = self.client.queue_prompt(graph, client_id)

            self.signals.status.emit("Waiting for image…")
            hist = self.client.wait_for_history(prompt_id)

            imgref = self.client.extract_first_image(hist)
            self.signals.status.emit(f"Downloading: {imgref.filename}")
            img_bytes = self.client.download_image(imgref)

            self.signals.image.emit(img_bytes)
            self.signals.reply.emit(contract.get("reply_text", ""))
            self.signals.status.emit("")
        except Exception as e:
            self.signals.status.emit(f"ERROR: {e}")
            print(f"[ERROR] {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.signals.done.emit()
