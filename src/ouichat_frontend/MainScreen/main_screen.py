from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QApplication
)

from MainScreen.chats_and_users import ChatsAndUsersPanel
from MainScreen.chat_environment import ChatEnvironment
from dialogs import AddUsersDialog, LogInDialog, ErrorDialog
from brain import Brain

class MainScreen(QWidget):
    def __init__(self, app: QApplication, brain: Brain, login_dialog: LogInDialog):
        super().__init__()

        self.brain = brain
        self.error_dialog = ErrorDialog()
        self.brain.run_error_dialog.connect(self.run_error_dialog)

        add_users_dialog = AddUsersDialog(brain)

        left_panel = ChatsAndUsersPanel(app, brain, login_dialog, add_users_dialog)

        right_panel = ChatEnvironment(brain, add_users_dialog)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)

    def run_error_dialog(self, error_message: str):
        self.error_dialog.set_error_message(error_message)
        self.error_dialog.exec()
        return