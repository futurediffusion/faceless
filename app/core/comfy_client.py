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
        print(f"[COMFY] Queueing prompt to {self.base_url}/prompt")
        try:
            r = requests.post(f"{self.base_url}/prompt", json=payload, timeout=30)
            r.raise_for_status()
            result = r.json()
            print(f"[COMFY] Queue response: {result}")
            return result["prompt_id"]
        except Exception as e:
            print(f"[COMFY] Queue failed: {e}")
            raise

    def get_queue(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/queue", timeout=10)
        r.raise_for_status()
        return r.json()

    def wait_for_history(self, prompt_id: str, poll=0.5, timeout_s=180) -> Dict[str, Any]:
        start = time.time()
        extended_timeout = timeout_s
        warned = False
        poll_count = 0
        print(f"[COMFY] Waiting for history: {prompt_id}")
        while time.time() - start < extended_timeout:
            poll_count += 1
            try:
                r = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if prompt_id in data:
                        print(f"[COMFY] ✅ History received after {poll_count} polls")
                        return data[prompt_id]
            except requests.exceptions.RequestException as e:
                print(f"[COMFY] Poll {poll_count} failed: {e}")
            if poll_count % 10 == 0:
                elapsed = time.time() - start
                print(f"[COMFY] Still waiting... ({elapsed:.1f}s elapsed, {poll_count} polls)")
            time.sleep(poll)
            if time.time() - start >= timeout_s and not warned:
                try:
                    queue = self.get_queue()
                except Exception:
                    queue = {}
                running = queue.get("queue_running") or queue.get("running") or []
                pending = queue.get("queue_pending") or queue.get("pending") or []
                print(f"[COMFY] Queue check: running={len(running)}, pending={len(pending)}")
                if running or pending:
                    extended_timeout += 120
                    warned = True
                    print("[COMFY] Extended timeout by 120s (queue active)")
                else:
                    print("[COMFY] No active queue items, giving up")
                    break
        print(f"[COMFY] ❌ Timeout after {time.time() - start:.1f}s ({poll_count} polls)")
        raise TimeoutError(
            "ComfyUI did not return results after polling. "
            "Check ComfyUI console for errors (OOM/VRAM issues)."
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
