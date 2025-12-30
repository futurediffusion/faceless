from PySide6.QtWidgets import QTextEdit


class ReplyPanel(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: rgba(10, 10, 10, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }
        """
        )
        self.hide()

    def set_reply(self, text: str):
        if text:
            self.setPlainText(text)
            self.show()
        else:
            self.clear()
            self.hide()
