from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QWidget, QFormLayout, QCheckBox
)

from PyQt6.QtCore import Qt

from ouichat_frontend.brain import Brain

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32

def make_request(domain: str, user: str, password: str):
    # TO BE IMPLEMENTED
    # RETURNS (TRUE, JWT Token) ON VALID CREDENTIALS AND (FALSE, $ERROR_MESSAGE) OTHERWISE
    return True, "TOKEN"

class LogInDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        description_label = QLabel()
        description_label.setText("Insert domain and credentials")
        description_label.setFixedHeight(25)

        domain_label = QLabel()
        domain_label.setText("Domain:")
        domain_label.setFixedSize(60, 25)

        self.domain_line_edit = QLineEdit()
        self.domain_line_edit.setPlaceholderText("Domain...")
        self.domain_line_edit.setMinimumSize(225, 25)
        self.domain_line_edit.setMaximumSize(450, 25)

        username_label = QLabel()
        username_label.setText("Username:")
        username_label.setFixedSize(60, 25)

        self.username_line_edit = QLineEdit()
        self.username_line_edit.setMaxLength(MAX_USERNAME_LENGTH)
        self.username_line_edit.setPlaceholderText("Username...")
        self.username_line_edit.setMinimumSize(225, 25)
        self.username_line_edit.setMaximumSize(450, 25)

        password_label = QLabel()
        password_label.setText("Password:")
        password_label.setFixedSize(60, 25)

        self.password_line_edit = QLineEdit()
        self.password_line_edit.setMaxLength(MAX_PASSWORD_LENGTH)
        self.password_line_edit.setPlaceholderText("Password...")
        self.password_line_edit.setMinimumSize(225, 25)
        self.password_line_edit.setMaximumSize(450, 25)

        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(5)

        form_layout.addRow(domain_label, self.domain_line_edit)
        form_layout.addRow(username_label, self.username_line_edit)
        form_layout.addRow(password_label, self.password_line_edit)

        form_widget.setLayout(form_layout)

        self.register_checkbox = QCheckBox()
        self.register_checkbox.setText("Register and Login")

        log_in_button = QPushButton("Login")
        log_in_button.setFixedSize(125, 25)
        log_in_button.setAutoDefault(False)
        log_in_button.clicked.connect(self.__validate_credentials)

        self.error_message = QLabel()
        self.error_message.setStyleSheet("color: red;")
        self.error_message.setFixedHeight(25)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(form_widget)
        layout.addWidget(self.register_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(log_in_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.setMaximumSize(535, 195)

    def __validate_credentials(self):
        username = self.username_line_edit.text()
        password = self.password_line_edit.text()
        domain = self.domain_line_edit.text()

        register = self.register_checkbox.isChecked()

        if register:
            # REGISTER REQUEST
            pass

        # LOGIN REQUEST
        ret = make_request(domain, username, password)

        if ret[0]:
            self.username_line_edit.clear()
            self.password_line_edit.clear()
            self.domain_line_edit.clear()

            # IMPLEMENT INFO RETRIEVAL

            user_data = {
                "username": username,
                "domain": domain,
                "icon_path": "./Icons/default_user_icon.png",
                "request_token": "TOKEN",
                "refresh_token": "REFRESH_TOKEN",
            }

            for idx in range(20):  # adding 20 chat rooms to the list
                chat_data = {
                    "chat_type": "chatroom", # {"chatroom", "p2p"}
                    "chat_setting": "rw", # {"rw", "ro"}
                    "domain": "test.test.ro" if idx < 10 else "test2.test2.ro",
                    "chat_id": str(idx),
                    "chat_description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                    "icon_path": "./Icons/chat_room_icon.png",
                    "users":    [{"username": "fifo",
                                  "icon_path": "./Icons/default_user_icon.png",
                                  "is_admin": True}] if idx < 5 else
                                [{"username": "fifo",
                                  "icon_path": "./Icons/default_user_icon.png",
                                  "is_admin": True},
                                 {"username": "fifo2",
                                  "icon_path": "./Icons/default_user_icon.png",
                                  "is_admin": False}] if idx < 10 else
                                [{"username": "fifo2",
                                  "icon_path": "./Icons/default_user_icon.png",
                                  "is_admin": True}]
                }

                self.brain.add_chat(chat_data)

            self.brain.add_user(user_data) # also sets it as the current user

            self.accept()

        else:
            self.error_message.setText(ret[1])