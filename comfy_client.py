import time
from dataclasses import dataclass
from typing import Any, Dict

import requests


@dataclass
class ComfyImageRef:
    filename: str
    subfolder: str
    type: str


class ComfyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def ping(self, timeout=2.5) -> bool:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False

    def get_loras(self) -> list:
        """Get available LoRA files from ComfyUI"""
        try:
            r = requests.get(f"{self.base_url}/object_info/LoraLoader", timeout=5)
            if r.status_code == 200:
                data = r.json()
                loras = data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [None])[0]
                return sorted(loras) if loras else []
        except Exception as e:
            print(f"[ERROR] Failed to get LoRAs: {e}")
        return []

    def get_checkpoints(self) -> list:
        """Get available checkpoint files from ComfyUI"""
        try:
            r = requests.get(f"{self.base_url}/object_info/CheckpointLoaderSimple", timeout=5)
            if r.status_code == 200:
                data = r.json()
                ckpts = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [None])[0]
                return sorted(ckpts) if ckpts else []
        except Exception as e:
            print(f"[ERROR] Failed to get checkpoints: {e}")
        return []

    def queue_prompt(self, prompt_graph: Dict[str, Any], client_id: str) -> str:
        payload = {"prompt": prompt_graph, "client_id": client_id}
        r = requests.post(f"{self.base_url}/prompt", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["prompt_id"]

    def get_queue(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/queue", timeout=10)
        r.raise_for_status()
        return r.json()

    def wait_for_history(self, prompt_id: str, poll=0.5, timeout_s=180) -> Dict[str, Any]:
        start = time.time()
        extended_timeout = timeout_s
        warned = False
        while time.time() - start < extended_timeout:
            r = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if prompt_id in data:
                    return data[prompt_id]
            time.sleep(poll)
            if time.time() - start >= timeout_s and not warned:
                try:
                    queue = self.get_queue()
                except Exception:
                    queue = {}
                running = queue.get("running") or []
                pending = queue.get("pending") or []
                if running or pending:
                    extended_timeout += 120
                    warned = True
                else:
                    break
        raise TimeoutError(
            "No apareció en history; Comfy pudo fallar o reiniciarse."
        )

    def extract_first_image(self, history_item: Dict[str, Any]) -> ComfyImageRef:
        outputs = history_item.get("outputs", {})
        for _node_id, out in outputs.items():
            imgs = out.get("images")
            if imgs and isinstance(imgs, list):
                im0 = imgs[0]
                return ComfyImageRef(
                    filename=im0.get("filename", ""),
                    subfolder=im0.get("subfolder", ""),
                    type=im0.get("type", "output"),
                )
        raise ValueError("No images found in ComfyUI history outputs.")

    def download_image(self, img: ComfyImageRef) -> bytes:
        params = {"filename": img.filename, "subfolder": img.subfolder, "type": img.type}
        r = requests.get(f"{self.base_url}/view", params=params, timeout=30)
        r.raise_for_status()
        return r.content
