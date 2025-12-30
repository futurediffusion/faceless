from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


class ImageViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(400)
        self.setStyleSheet("background-color: #000;")
        self._pixmap: QPixmap | None = None

    def set_image_bytes(self, data: bytes) -> bool:
        image = QImage.fromData(data)
        if image.isNull():
            return False
        self._pixmap = QPixmap.fromImage(image)
        self._apply_scale()
        return True

    def _apply_scale(self):
        if not self._pixmap:
            return
        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scale()
