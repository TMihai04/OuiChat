from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout
)

from ouichat_frontend.MainScreen.chats_and_users import ChatsAndUsersPanel
from ouichat_frontend.MainScreen.chat_environment import ChatEnvironment
from ouichat_frontend.brain import Brain

class MainScreen(QWidget):
    def __init__(self, brain: Brain, login_dialog):
        super().__init__()

        left_panel = ChatsAndUsersPanel(brain, login_dialog)

        right_panel = ChatEnvironment(brain)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)