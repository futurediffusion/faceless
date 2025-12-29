from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QTextEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
)

from comfy_client import ComfyClient
from models import CharacterParams, GenParams


class ApiKeysDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Keys")
        self.setModal(True)
        self.config = config

        layout = QFormLayout(self)

        self.provider = QComboBox()
        self.provider.addItem("Gemini")
        layout.addRow("Provider:", self.provider)

        self.gemini_key = QLineEdit(config.get("gemini_api_key", ""))
        self.gemini_key.setEchoMode(QLineEdit.Password)
        layout.addRow("GEMINI_API_KEY:", self.gemini_key)

        info = QLabel("Stored locally in config.json (not committed)")
        info.setStyleSheet("color: #808080; font-size: 10px;")
        layout.addRow(info)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

    def get_config(self) -> dict:
        return {
            "llm_provider": "gemini",
            "gemini_api_key": self.gemini_key.text().strip(),
        }


class CharacterDialog(QDialog):
    def __init__(self, char_params: CharacterParams, loras: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character Settings")
        self.setModal(True)
        self.char_params = char_params

        layout = QFormLayout(self)

        # Visual character description
        self.visual_base = QTextEdit(char_params.visual_base)
        self.visual_base.setFixedHeight(100)
        self.visual_base.setPlaceholderText("Character description (appearance, style, etc.)")
        layout.addRow("Visual character description (used for images):", self.visual_base)

        # Identity profile (LLM-only)
        self.identity_profile = QTextEdit(char_params.identity_profile)
        self.identity_profile.setFixedHeight(100)
        self.identity_profile.setPlaceholderText(
            "This will be used later by the LLM, not sent to ComfyUI."
        )
        layout.addRow("Identity profile (LLM only, not used for images yet):", self.identity_profile)

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
            visual_base=self.visual_base.toPlainText().strip(),
            identity_profile=self.identity_profile.toPlainText().strip(),
            lora_name=lora,
            lora_strength=self.lora_strength.value(),
        )


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
        samplers = [
            "euler",
            "euler_ancestral",
            "heun",
            "dpm_2",
            "dpm_2_ancestral",
            "lms",
            "dpm_fast",
            "dpm_adaptive",
            "dpmpp_2s_ancestral",
            "dpmpp_sde",
            "dpmpp_2m",
            "ddim",
            "uni_pc",
            "uni_pc_bh2",
        ]
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
            checkpoint=ckpt,
        )
