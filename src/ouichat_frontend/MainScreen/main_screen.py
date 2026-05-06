from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout
)

from .chats_and_users import ChatsAndUsersPanel
from .chat_environment import ChatEnvironment
from ..brain import Brain

class MainScreen(QWidget):
    def __init__(self, brain: Brain, login_dialog):
        super().__init__()

        left_panel = ChatsAndUsersPanel(brain, login_dialog)

        right_panel = ChatEnvironment(brain)
        right_panel.chat_history.update_current_user(brain.get_current_user())

        brain.interaction_panel_chat_selected.connect(right_panel.message_window.set_visibility_dict)
        brain.interaction_panel_chat_selected.connect(right_panel.chat_history.show_chat)
        brain.interaction_panel_current_user_changed.connect(right_panel.chat_history.update_current_user)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)