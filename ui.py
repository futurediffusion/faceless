import json
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QApplication,
)

from comfy_client import ComfyClient
from dialogs import CharacterDialog, ConnectionDialog, ParamsDialog
from models import CharacterParams, GenParams
from workers import GenerateWorker
from workflow_patcher import detect_cliptext_nodes


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
        self.btn_settings.setStyleSheet(
            """
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
        """
        )
        self.btn_settings.clicked.connect(self.show_settings_menu)
        self.btn_settings.raise_()

        # Input container (overlay at bottom)
        self.input_container = QWidget(self)
        self.input_container.setStyleSheet(
            """
            QWidget {
                background-color: rgba(20, 20, 20, 240);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """
        )
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(15, 12, 15, 15)
        input_layout.setSpacing(8)

        # Toggle button
        toggle_layout = QHBoxLayout()
        toggle_layout.addStretch()
        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedSize(35, 25)
        self.btn_toggle.setStyleSheet(
            """
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
        """
        )
        self.btn_toggle.clicked.connect(self.toggle_input)
        toggle_layout.addWidget(self.btn_toggle)
        toggle_layout.addStretch()
        input_layout.addLayout(toggle_layout)

        # Scene/action prompt (base removed from here)
        self.append = QTextEdit()
        self.append.setPlaceholderText("Scene/action/emotion...")
        self.append.setFixedHeight(100)
        self.append.setStyleSheet(
            """
            QTextEdit {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 2px solid rgba(80, 80, 80, 150);
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
            }
        """
        )
        input_layout.addWidget(self.append)

        # Generate button
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setFixedHeight(45)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet(
            """
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
        """
        )
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
            print(
                f"[INFO] Character updated: LoRA={self.char_params.lora_name or '(None)'} @ {self.char_params.lora_strength}"
            )

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
            print("[INFO] Parameters updated")

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


def main():
    app = QApplication([])
    w = FacelessDevApp()
    w.show()
    app.exec()
