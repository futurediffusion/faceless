import json
import time
import uuid
import random
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPixmap, QImage, QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QDialog,
    QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QMenu
)

# =========================
# ComfyUI client
# =========================

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

    def wait_for_history(self, prompt_id: str, poll=0.5, timeout_s=180) -> Dict[str, Any]:
        start = time.time()
        while time.time() - start < timeout_s:
            r = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if prompt_id in data:
                    return data[prompt_id]
            time.sleep(poll)
        raise TimeoutError("ComfyUI timeout: no result in /history")

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

# =========================
# Generation Parameters
# =========================

@dataclass
class GenParams:
    seed: Optional[int] = None
    steps: int = 8
    cfg: float = 2.2
    sampler: str = "euler_ancestral"
    scheduler: str = "simple"
    quality_tags: str = "masterpiece, best quality, high quality, detailed"
    negative: str = "worst aesthetic, worst quality, low quality, bad quality, lowres, signature, username, logo, bad hands, mutated hands, ambiguous form, feral"
    checkpoint: str = ""  # Empty = use workflow default

@dataclass
class CharacterParams:
    base_prompt: str = ""
    lora_name: str = ""  # Empty = disabled
    lora_strength: float = 0.0  # 0.0 = disabled, 1.0 = default when enabled

# =========================
# Workflow patching
# =========================

def find_node_by_title(prompt_graph: Dict[str, Any], title: str) -> Optional[str]:
    """Find node ID by _meta.title"""
    for node_id, node in prompt_graph.items():
        if not isinstance(node, dict):
            continue
        if node.get("_meta", {}).get("title", "") == title:
            return node_id
    return None


def detect_cliptext_nodes(prompt_graph: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Detect positive/negative CLIPTextEncode nodes by _meta.title."""
    pos_id = None
    neg_id = None
    
    for node_id, node in prompt_graph.items():
        if not isinstance(node, dict):
            continue
        
        meta_title = node.get("_meta", {}).get("title", "")
        
        if meta_title == "__PROMPT_POS__":
            pos_id = node_id
        elif meta_title == "__PROMPT_NEG__":
            neg_id = node_id
    
    print(f"[DEBUG] Detected nodes by title: pos={pos_id}, neg={neg_id}")
    
    return pos_id, neg_id


def patch_workflow(prompt_graph: Dict[str, Any], char_params: CharacterParams, append_text: str, gen_params: GenParams) -> Dict[str, Any]:
    """Patch workflow with character, prompts and parameters."""
    g = json.loads(json.dumps(prompt_graph))
    pos_id, neg_id = detect_cliptext_nodes(g)
    
    if pos_id is None:
        raise ValueError("No __PROMPT_POS__ node found.")

    # === POSITIVE PROMPT: QUALITY_TAGS + BASE + APPEND ===
    current = (g[pos_id].get("inputs") or {}).get("text", "") or ""
    base = char_params.base_prompt.strip() if char_params.base_prompt else current
    extra = append_text.strip()
    quality = gen_params.quality_tags.strip()

    parts = []
    if quality:
        parts.append(quality)
    if base:
        parts.append(base)
    if extra:
        parts.append(extra)
    
    final_positive = ", ".join(parts) if parts else "high quality, detailed"

    print(f"[DEBUG] POSITIVE - Quality: {quality[:60]}...")
    print(f"[DEBUG] POSITIVE - Base: {base[:60]}...")
    print(f"[DEBUG] POSITIVE - Append: {extra}")
    print(f"[DEBUG] POSITIVE - Final: {final_positive[:120]}...")
    
    g[pos_id]["inputs"]["text"] = final_positive

    # === NEGATIVE PROMPT ===
    if neg_id and gen_params.negative:
        print(f"[DEBUG] NEGATIVE: {gen_params.negative[:80]}...")
        g[neg_id]["inputs"]["text"] = gen_params.negative

    # === CHARACTER LORA (__LORA_CHARACTER__) ===
    lora_char_id = find_node_by_title(g, "__LORA_CHARACTER__")
    if lora_char_id and g[lora_char_id].get("class_type") == "LoraLoader":
        if char_params.lora_name:
            g[lora_char_id]["inputs"]["lora_name"] = char_params.lora_name
            g[lora_char_id]["inputs"]["strength_model"] = char_params.lora_strength
            g[lora_char_id]["inputs"]["strength_clip"] = char_params.lora_strength
            print(f"[DEBUG] Character LoRA: {char_params.lora_name} @ {char_params.lora_strength}")
        else:
            # Disable LoRA by setting strength to 0
            g[lora_char_id]["inputs"]["strength_model"] = 0.0
            g[lora_char_id]["inputs"]["strength_clip"] = 0.0
            print(f"[DEBUG] Character LoRA: disabled")
    else:
        print(f"[WARN] __LORA_CHARACTER__ node not found")

    # === CHECKPOINT (__CHECKPOINT_BASE__) ===
    if gen_params.checkpoint:
        ckpt_id = find_node_by_title(g, "__CHECKPOINT_BASE__")
        if ckpt_id and g[ckpt_id].get("class_type") == "CheckpointLoaderSimple":
            g[ckpt_id]["inputs"]["ckpt_name"] = gen_params.checkpoint
            print(f"[DEBUG] Checkpoint: {gen_params.checkpoint}")

    # === KSAMPLER (__SAMPLER_MAIN__) ===
    sampler_id = find_node_by_title(g, "__SAMPLER_MAIN__")
    if sampler_id and g[sampler_id].get("class_type") in ["KSampler", "KSamplerAdvanced"]:
        inputs = g[sampler_id].get("inputs", {})
        
        if gen_params.seed is None:
            new_seed = random.randint(1, 2**31 - 1)
            print(f"[DEBUG] KSampler: Random seed = {new_seed}")
        else:
            new_seed = gen_params.seed
            print(f"[DEBUG] KSampler: Fixed seed = {new_seed}")
        
        if "seed" in inputs:
            inputs["seed"] = new_seed
        if "steps" in inputs:
            inputs["steps"] = gen_params.steps
        if "cfg" in inputs:
            inputs["cfg"] = gen_params.cfg
        if "sampler_name" in inputs:
            inputs["sampler_name"] = gen_params.sampler
        if "scheduler" in inputs:
            inputs["scheduler"] = gen_params.scheduler
        
        print(f"[DEBUG] KSampler: steps={gen_params.steps}, cfg={gen_params.cfg}, sampler={gen_params.sampler}")
    else:
        print(f"[WARN] __SAMPLER_MAIN__ node not found")
    
    return g

# =========================
# Character Dialog
# =========================

class CharacterDialog(QDialog):
    def __init__(self, char_params: CharacterParams, loras: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character Settings")
        self.setModal(True)
        self.char_params = char_params
        
        layout = QFormLayout(self)
        
        # Base prompt
        self.base_prompt = QTextEdit(char_params.base_prompt)
        self.base_prompt.setFixedHeight(100)
        self.base_prompt.setPlaceholderText("Character description (appearance, style, etc.)")
        layout.addRow("Base character:", self.base_prompt)
        
        # LoRA selector
        self.lora_combo = QComboBox()
        self.lora_combo.addItem("(None - Disabled)")
        self.lora_combo.addItems(loras)
        if char_params.lora_name and char_params.lora_name in loras:
            self.lora_combo.setCurrentText(char_params.lora_name)
        self.lora_combo.currentTextChanged.connect(self.on_lora_changed)
        layout.addRow("Character LoRA:", self.lora_combo)
        
        # LoRA strength
        strength_layout = QHBoxLayout()
        self.lora_strength = QDoubleSpinBox()
        self.lora_strength.setRange(0.0, 2.0)
        self.lora_strength.setSingleStep(0.1)
        self.lora_strength.setValue(char_params.lora_strength)
        self.lora_strength.setEnabled(bool(char_params.lora_name))
        
        btn_down = QPushButton("-")
        btn_down.setFixedWidth(30)
        btn_down.clicked.connect(lambda: self.lora_strength.setValue(max(0.0, self.lora_strength.value() - 0.1)))
        
        btn_up = QPushButton("+")
        btn_up.setFixedWidth(30)
        btn_up.clicked.connect(lambda: self.lora_strength.setValue(min(2.0, self.lora_strength.value() + 0.1)))
        
        strength_layout.addWidget(btn_down)
        strength_layout.addWidget(self.lora_strength)
        strength_layout.addWidget(btn_up)
        layout.addRow("LoRA strength:", strength_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Apply")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
    
    def on_lora_changed(self, text):
        is_enabled = text != "(None - Disabled)"
        self.lora_strength.setEnabled(is_enabled)
        if is_enabled and self.lora_strength.value() == 0.0:
            self.lora_strength.setValue(1.0)
    
    def get_params(self) -> CharacterParams:
        lora = self.lora_combo.currentText()
        if lora == "(None - Disabled)":
            lora = ""
        return CharacterParams(
            base_prompt=self.base_prompt.toPlainText().strip(),
            lora_name=lora,
            lora_strength=self.lora_strength.value()
        )

# =========================
# Connection Dialog
# =========================

class ConnectionDialog(QDialog):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.url = QLineEdit(url)
        layout.addRow("ComfyUI URL:", self.url)
        
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.clicked.connect(self.test_connection)
        layout.addRow(self.btn_test)
        
        self.status = QLabel("")
        self.status.setStyleSheet("color: #808080;")
        layout.addRow(self.status)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
    
    def test_connection(self):
        client = ComfyClient(self.url.text().strip())
        if client.ping():
            self.status.setText("✅ Connected")
            self.status.setStyleSheet("color: #00ff00;")
        else:
            self.status.setText("❌ Not connected")
            self.status.setStyleSheet("color: #ff0000;")
    
    def get_url(self) -> str:
        return self.url.text().strip()

# =========================
# Parameters Dialog
# =========================

class ParamsDialog(QDialog):
    def __init__(self, params: GenParams, checkpoints: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generation Parameters")
        self.setModal(True)
        self.params = params
        
        layout = QFormLayout(self)
        
        # Checkpoint selector
        self.checkpoint_combo = QComboBox()
        self.checkpoint_combo.addItem("(Workflow Default)")
        self.checkpoint_combo.addItems(checkpoints)
        if params.checkpoint and params.checkpoint in checkpoints:
            self.checkpoint_combo.setCurrentText(params.checkpoint)
        layout.addRow("Base Model:", self.checkpoint_combo)
        
        # Quality tags
        self.quality = QLineEdit(params.quality_tags)
        layout.addRow("Quality tags:", self.quality)
        
        # Seed
        self.seed_random = QCheckBox("Random seed")
        self.seed_random.setChecked(params.seed is None)
        self.seed_random.toggled.connect(self.on_seed_toggle)
        layout.addRow("Seed mode:", self.seed_random)
        
        self.seed_value = QSpinBox()
        self.seed_value.setRange(1, 2**31 - 1)
        self.seed_value.setValue(params.seed if params.seed else 12345)
        self.seed_value.setEnabled(params.seed is not None)
        layout.addRow("Fixed seed:", self.seed_value)
        
        # Steps
        self.steps = QSpinBox()
        self.steps.setRange(1, 100)
        self.steps.setValue(params.steps)
        layout.addRow("Steps:", self.steps)
        
        # CFG
        self.cfg = QDoubleSpinBox()
        self.cfg.setRange(0.1, 30.0)
        self.cfg.setSingleStep(0.1)
        self.cfg.setValue(params.cfg)
        layout.addRow("CFG Scale:", self.cfg)
        
        # Sampler
        self.sampler = QComboBox()
        samplers = ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                   "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                   "dpmpp_sde", "dpmpp_2m", "ddim", "uni_pc", "uni_pc_bh2"]
        self.sampler.addItems(samplers)
        self.sampler.setCurrentText(params.sampler)
        layout.addRow("Sampler:", self.sampler)
        
        # Scheduler
        self.scheduler = QComboBox()
        schedulers = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"]
        self.scheduler.addItems(schedulers)
        self.scheduler.setCurrentText(params.scheduler)
        layout.addRow("Scheduler:", self.scheduler)
        
        # Negative prompt
        self.negative = QTextEdit()
        self.negative.setPlainText(params.negative)
        self.negative.setFixedHeight(100)
        layout.addRow("Negative prompt:", self.negative)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Apply")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
    
    def on_seed_toggle(self, checked):
        self.seed_value.setEnabled(not checked)
    
    def get_params(self) -> GenParams:
        ckpt = self.checkpoint_combo.currentText()
        if ckpt == "(Workflow Default)":
            ckpt = ""
        return GenParams(
            seed=None if self.seed_random.isChecked() else self.seed_value.value(),
            steps=self.steps.value(),
            cfg=self.cfg.value(),
            sampler=self.sampler.currentText(),
            scheduler=self.scheduler.currentText(),
            quality_tags=self.quality.text().strip(),
            negative=self.negative.toPlainText().strip(),
            checkpoint=ckpt
        )

# =========================
# Worker
# =========================

class WorkerSignals(QObject):
    status = Signal(str)
    image = Signal(bytes)
    done = Signal()

class GenerateWorker(threading.Thread):
    def __init__(self, client: ComfyClient, prompt_graph: Dict[str, Any], 
                 char_params: CharacterParams, append_text: str, gen_params: GenParams):
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

# =========================
# UI
# =========================

class FacelessDevApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FACELESS")
        self.resize(400, 700)  # Escalable, tamaño inicial más pequeño

        self.base_dir = Path(__file__).resolve().parent
        self.workflow_path = self.base_dir / "facelessbase.json"

        self.prompt_graph: Optional[Dict[str, Any]] = None
        self.params = GenParams()
        self.char_params = CharacterParams()
        self.comfy_url = "http://127.0.0.1:8188"
        self.input_visible = True
        self.available_loras = []
        self.available_checkpoints = []

        # Main layout
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        # Image container (fullscreen)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(400)
        self.image_label.setStyleSheet("background-color: #000;")
        self.root.addWidget(self.image_label)

        # Settings button (gear, top-right overlay)
        self.btn_settings = QPushButton("⚙", self)
        self.btn_settings.setFixedSize(45, 45)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 40, 40, 180);
                color: white;
                border-radius: 22px;
                font-size: 22px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(60, 60, 60, 200);
            }
        """)
        self.btn_settings.clicked.connect(self.show_settings_menu)
        self.btn_settings.raise_()

        # Input container (overlay at bottom)
        self.input_container = QWidget(self)
        self.input_container.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 240);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(15, 12, 15, 15)
        input_layout.setSpacing(8)

        # Toggle button
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()
        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedSize(35, 25)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 150);
                color: white;
                border-radius: 12px;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 180);
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_input)
        toggle_layout.addWidget(self.btn_toggle)
        toggle_layout.addStretch()
        input_layout.addLayout(toggle_layout)

        # Scene/action prompt (base removed from here)
        self.append = QTextEdit()
        self.append.setPlaceholderText("Scene/action/emotion...")
        self.append.setFixedHeight(100)
        self.append.setStyleSheet("""
            QTextEdit {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 2px solid rgba(80, 80, 80, 150);
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
            }
        """)
        input_layout.addWidget(self.append)

        # Generate button
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setFixedHeight(45)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #ff8800;
                color: white;
                border-radius: 22px;
                font-size: 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff9920;
            }
            QPushButton:disabled {
                background-color: rgba(80, 80, 80, 100);
                color: rgba(150, 150, 150, 100);
            }
        """)
        self.btn_generate.clicked.connect(self.on_generate)
        input_layout.addWidget(self.btn_generate)

        # Status label
        self.status = QLabel("")
        self.status.setStyleSheet("color: #808080; font-size: 10px;")
        self.status.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(self.status)

        # Position input container at bottom
        self.input_container.show()

        # Shortcuts
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(self.on_generate)

        # Wiring
        self.load_workflow(self.workflow_path)
        self.test_connection_silent()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition settings button (top-right)
        self.btn_settings.move(self.width() - 60, 15)
        
        # Reposition input container (bottom)
        self.position_input_container()
        
        # Scale image
        pm = self.image_label.pixmap()
        if pm:
            scaled = pm.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)

    def position_input_container(self):
        container_height = 220 if self.input_visible else 45
        self.input_container.setGeometry(0, self.height() - container_height, self.width(), container_height)
        self.input_container.raise_()

    def toggle_input(self):
        self.input_visible = not self.input_visible
        self.btn_toggle.setText("▲" if self.input_visible else "▼")
        
        self.append.setVisible(self.input_visible)
        self.btn_generate.setVisible(self.input_visible)
        self.status.setVisible(self.input_visible)
        
        self.position_input_container()

    def show_settings_menu(self):
        menu = QMenu(self)
        
        char_action = QAction("Character...", self)
        char_action.triggered.connect(self.open_character_dialog)
        menu.addAction(char_action)
        
        menu.addSeparator()
        
        conn_action = QAction("Connection...", self)
        conn_action.triggered.connect(self.open_connection_dialog)
        menu.addAction(conn_action)
        
        params_action = QAction("Parameters...", self)
        params_action.triggered.connect(self.open_params_dialog)
        menu.addAction(params_action)
        
        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))
    
    def open_character_dialog(self):
        # Refresh LoRA list from ComfyUI
        client = ComfyClient(self.comfy_url)
        self.available_loras = client.get_loras()
        
        dialog = CharacterDialog(self.char_params, self.available_loras, self)
        if dialog.exec():
            self.char_params = dialog.get_params()
            print(f"[INFO] Character updated: LoRA={self.char_params.lora_name or '(None)'} @ {self.char_params.lora_strength}")

    def open_connection_dialog(self):
        dialog = ConnectionDialog(self.comfy_url, self)
        if dialog.exec():
            self.comfy_url = dialog.get_url()
            self.test_connection_silent()

    def open_params_dialog(self):
        # Refresh checkpoint list from ComfyUI
        client = ComfyClient(self.comfy_url)
        self.available_checkpoints = client.get_checkpoints()
        
        dialog = ParamsDialog(self.params, self.available_checkpoints, self)
        if dialog.exec():
            self.params = dialog.get_params()
            print(f"[INFO] Parameters updated")

    def set_status(self, text: str):
        self.status.setText(text)

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
        client = ComfyClient(self.comfy_url)
        ok = client.ping()
        self.btn_generate.setEnabled(ok and self.prompt_graph is not None)

    def test_connection_silent(self):
        client = ComfyClient(self.comfy_url)
        ok = client.ping()
        self.btn_generate.setEnabled(ok and self.prompt_graph is not None)
        print(f"[INFO] Connection: {'✅' if ok else '❌'}")

    def on_generate(self):
        client = ComfyClient(self.comfy_url)
        if not client.ping():
            self.set_status("❌ Not connected")
            return
        if self.prompt_graph is None:
            self.set_status("❌ Workflow not loaded")
            return

        self.btn_generate.setEnabled(False)
        self.set_status("Generating...")

        append_text = self.append.toPlainText().strip()

        worker = GenerateWorker(client, self.prompt_graph, self.char_params, append_text, self.params)
        worker.signals.status.connect(self.set_status)
        worker.signals.image.connect(self.on_image)
        worker.signals.done.connect(self.on_worker_done)
        worker.start()

    def on_worker_done(self):
        self.btn_generate.setEnabled(True)

    def on_image(self, data: bytes):
        img = QImage.fromData(data)
        if img.isNull():
            self.set_status("ERROR: decode failed")
            return
        pix = QPixmap.fromImage(img)
        scaled = pix.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)


if __name__ == "__main__":
    app = QApplication([])
    w = FacelessDevApp()
    w.show()
    app.exec()