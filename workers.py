import threading
import uuid
from typing import Any, Dict

from PySide6.QtCore import QObject, Signal

from comfy_client import ComfyClient
from models import CharacterParams, GenParams
from workflow_patcher import patch_workflow


class WorkerSignals(QObject):
    status = Signal(str)
    image = Signal(bytes)
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
