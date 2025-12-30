from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QPushButton, QVBoxLayout, QWidget

from app.ui.components.image_viewer import ImageViewer
from app.ui.components.input_panel import InputPanel
from app.ui.components.reply_panel import ReplyPanel


class MainWindow(QWidget):
    generate_requested = Signal(str)
    open_character_requested = Signal()
    open_api_keys_requested = Signal()
    open_connection_requested = Signal()
    open_params_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FACELESS")
        self.resize(400, 700)

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.image_viewer = ImageViewer(self)
        self.root.addWidget(self.image_viewer)

        self.reply_panel = ReplyPanel(self)

        self.input_panel = InputPanel(self)
        self.input_panel.generate_requested.connect(self.generate_requested.emit)
        self.input_panel.visibility_changed.connect(self.position_overlays)

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

        self.input_panel.show()

        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(self.input_panel.trigger_generate)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_overlays()

    def position_overlays(self):
        self.btn_settings.move(self.width() - 60, 15)
        self.position_input_panel()
        self.position_reply_panel()

    def position_input_panel(self):
        container_height = self.input_panel.preferred_height()
        self.input_panel.setGeometry(0, self.height() - container_height, self.width(), container_height)
        self.input_panel.raise_()

    def position_reply_panel(self):
        reply_height = 140
        bottom_padding = 10
        input_height = self.input_panel.height()
        top = self.height() - input_height - reply_height - bottom_padding
        self.reply_panel.setGeometry(10, max(10, top), self.width() - 20, reply_height)
        self.reply_panel.raise_()

    def show_settings_menu(self):
        menu = QMenu(self)

        char_action = QAction("Character...", self)
        char_action.triggered.connect(self.open_character_requested.emit)
        menu.addAction(char_action)

        menu.addSeparator()

        api_action = QAction("API Keys...", self)
        api_action.triggered.connect(self.open_api_keys_requested.emit)
        menu.addAction(api_action)

        conn_action = QAction("Connection...", self)
        conn_action.triggered.connect(self.open_connection_requested.emit)
        menu.addAction(conn_action)

        params_action = QAction("Parameters...", self)
        params_action.triggered.connect(self.open_params_requested.emit)
        menu.addAction(params_action)

        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))

    def set_status(self, text: str):
        self.input_panel.set_status(text)

    def set_generate_enabled(self, enabled: bool):
        self.input_panel.set_generate_enabled(enabled)

    def clear_input(self):
        self.input_panel.clear_input()

    def clear_reply(self):
        self.reply_panel.set_reply("")

    def show_reply(self, text: str):
        self.reply_panel.set_reply(text)
        self.position_reply_panel()

    def set_image_bytes(self, data: bytes) -> bool:
        return self.image_viewer.set_image_bytes(data)
