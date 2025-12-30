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
        print("[ReplyPanel] set_reply called")
        print(
            f"[ReplyPanel] Input text: '{clean_text[:50]}...'"
            if len(clean_text) > 50
            else f"[ReplyPanel] Input text: '{clean_text}'"
        )
        print(f"[ReplyPanel] Current state: visible={self.isVisible()}, geometry={self.geometry()}")

        if clean_text:
            self.setPlainText(clean_text)
            print("[ReplyPanel] Text set in QTextEdit")

            was_hidden = self.isHidden()
            if was_hidden:
                self.show()
                print("[ReplyPanel] Called show() (was hidden)")

            print(f"[ReplyPanel] Final state: visible={self.isVisible()}, isHidden={self.isHidden()}")
            print(f"[ReplyPanel] Geometry: {self.geometry()}")
            print(f"[ReplyPanel] Parent: {self.parent()}")
        else:
            self.clear()
            self.hide()
            print("[ReplyPanel] Cleared and hidden (empty text)")
