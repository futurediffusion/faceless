from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout


class InputPanel(QWidget):
    generate_requested = Signal(str)
    visibility_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_visible = True
        self.setStyleSheet(
            """
            QWidget {
                background-color: rgba(20, 20, 20, 240);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 15)
        layout.setSpacing(8)

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
        layout.addLayout(toggle_layout)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Chat input...")
        self.chat_input.setFixedHeight(70)
        self.chat_input.setStyleSheet(
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
        layout.addWidget(self.chat_input)

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
        self.btn_generate.clicked.connect(self._emit_generate)
        layout.addWidget(self.btn_generate)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #808080; font-size: 10px;")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setVisible(False)
        layout.addWidget(self.status)

    def _emit_generate(self):
        text = self.chat_input.toPlainText().strip()
        if text:
            self.generate_requested.emit(text)

    def toggle_input(self):
        self._input_visible = not self._input_visible
        self.btn_toggle.setText("▼" if self._input_visible else "▲")

        self.chat_input.setVisible(self._input_visible)
        self.btn_generate.setVisible(self._input_visible)
        if self._input_visible:
            self.status.setVisible(bool(self.status.text()))
        else:
            self.status.setVisible(False)
        self.visibility_changed.emit()

    def preferred_height(self) -> int:
        return 190 if self._input_visible else 45

    def set_status(self, text: str):
        self.status.setText(text)
        self.status.setVisible(bool(text))

    def clear_input(self):
        self.chat_input.clear()

    def set_generate_enabled(self, enabled: bool):
        self.btn_generate.setEnabled(enabled)

    def trigger_generate(self):
        self._emit_generate()
