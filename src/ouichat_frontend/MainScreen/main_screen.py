from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout
)

from PyQt6.QtCore import pyqtSignal

from .chats_and_users import ChatsAndUsersPanel
from .chat_environment import ChatEnvironment

class MainScreen(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, initial_user_data: dict, login_dialog):
        super().__init__()

        left_panel = ChatsAndUsersPanel(initial_user_data, login_dialog)

        right_panel = ChatEnvironment()
        right_panel.chat_history.update_current_user(initial_user_data)
        left_panel.chat_selected.connect(right_panel.message_window.set_visibility_dict)
        left_panel.user_changed.connect(right_panel.chat_history.update_current_user)

        left_panel.settings_requested.connect(self.settings_requested.emit)
        left_panel.chat_selected.connect(right_panel.chat_history.show_chat)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)