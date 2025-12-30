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
        layout.setContentsMargins(15, 8, 15, 10)
        layout.setSpacing(2)

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

        self.input_container = QWidget()
        self.input_container.setFixedHeight(70)
        self.input_container.setStyleSheet(
            """
            QWidget {
                background-color: rgba(40, 40, 40, 200);
                border: 2px solid rgba(80, 80, 80, 150);
                border-radius: 12px;
            }
        """
        )
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(10, 6, 10, 6)
        input_layout.setSpacing(8)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Chat input...")
        self.chat_input.setStyleSheet(
            """
            QTextEdit {
                background: transparent;
                color: white;
                border: none;
                font-size: 12px;
            }
        """
        )
        input_layout.addWidget(self.chat_input)

        self.btn_generate = QPushButton("↑")
        self.btn_generate.setFixedSize(34, 34)
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                color: #111111;
                border-radius: 17px;
                font-size: 18px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:disabled {
                background-color: rgba(80, 80, 80, 140);
                color: rgba(200, 200, 200, 120);
            }
        """
        )
        self.btn_generate.clicked.connect(self._emit_generate)
        input_layout.addWidget(self.btn_generate)
        layout.addWidget(self.input_container)

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

        self.input_container.setVisible(self._input_visible)
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
