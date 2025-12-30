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
        print("[ReplyPanel] Initialized (hidden)")

    def set_reply(self, text: str):
        clean_text = text.strip()
        print(
            f"[ReplyPanel] set_reply called with: '{clean_text[:50]}...'"
            if len(clean_text) > 50
            else f"[ReplyPanel] set_reply called with: '{clean_text}'"
        )

        if clean_text:
            self.setPlainText(clean_text)
            print(f"[ReplyPanel] Text set, was hidden: {self.isHidden()}")
            if self.isHidden():
                self.show()
                print("[ReplyPanel] Called show()")
            print(f"[ReplyPanel] Now visible: {self.isVisible()}")
        else:
            self.clear()
            self.hide()
            print("[ReplyPanel] Cleared and hidden (empty text)")
