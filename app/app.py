from PySide6.QtWidgets import QApplication

from app.controllers.app_controller import AppController


def main():
    app = QApplication([])
    controller = AppController()
    controller.show()
    app.exec()
