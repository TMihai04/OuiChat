from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout
)

from MainScreen.chats_and_users import ChatsAndUsersPanel
from MainScreen.chat_environment import ChatEnvironment
from dialogs import AddUsersDialog, LogInDialog
from brain import Brain

class MainScreen(QWidget):
    def __init__(self, brain: Brain, login_dialog: LogInDialog):
        super().__init__()

        add_users_dialog = AddUsersDialog(brain)

        left_panel = ChatsAndUsersPanel(brain, login_dialog, add_users_dialog)

        right_panel = ChatEnvironment(brain, add_users_dialog)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)