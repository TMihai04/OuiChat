from PyQt6.QtWidgets import (
    QPushButton, QVBoxLayout, QLabel, QWidget,
)

from PyQt6.QtCore import Qt, pyqtSignal

from ouichat_frontend.brain import Brain

class SettingsScreen(QWidget):
    """
    TO DO:
        - implement use-cases
    """

    back_requested = pyqtSignal()

    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.back_button = QPushButton()
        self.back_button.setText("Close")
        self.back_button.setFixedSize(30, 30)
        self.back_button.clicked.connect(self.brain.main_window_comms_requested.emit)

        self.label = QLabel()
        self.label.setText("SETTINGS SCREEN")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.back_button)
        layout.addWidget(self.label)
        self.setLayout(layout)