from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QLabel, QStackedLayout, QWidget, QHBoxLayout, QListWidget, QListWidgetItem,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

MAX_USERNAME_LENGTH = 32
MAX_PASSWORD_LENGTH = 32

USERNAME = ""
TOKEN = ""

def make_request(user: str, password: str):
    # TO BE IMPLEMENTED
    # RETURNS (TRUE, JWT Token) ON VALID CREDENTIALS AND (FALSE, $ERROR_MESSAGE) OTHERWISE
    return True, "TOKEN"

class LogInDialog(QDialog):
    def __init__(self):
        super().__init__()

        description_label = QLabel()
        description_label.setText("Insert credentials")

        self.username_line_edit = QLineEdit()
        self.username_line_edit.setMaxLength(MAX_USERNAME_LENGTH)
        self.username_line_edit.setPlaceholderText("Username...")
        self.username_line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.password_line_edit = QLineEdit()
        self.password_line_edit.setMaxLength(MAX_PASSWORD_LENGTH)
        self.password_line_edit.setPlaceholderText("Password...")
        self.password_line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        log_in_button = QPushButton("Login")
        log_in_button.setFixedSize(200, 30)
        log_in_button.clicked.connect(self.__validate_credentials)

        self.error_message = QLabel()
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_message.setStyleSheet("color: red;")

        layout = QVBoxLayout()
        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.username_line_edit, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.password_line_edit, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(log_in_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def __validate_credentials(self):
        username = self.username_line_edit.text()
        password = self.password_line_edit.text()

        ret = make_request(username, password)

        if ret[0]:
            global TOKEN, USERNAME
            TOKEN = ret[1]
            USERNAME = username
            self.accept()
        else:
            self.error_message.setText(ret[1])

class ChatList(QWidget):
    chat_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        list_widget = QListWidget()
        list_widget.setIconSize(QSize(32, 32))

        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # no vertical scrollbar
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # no horizontal scrollbar
        list_widget.currentRowChanged.connect(self.chat_selected.emit)

        chat_icon = QIcon("./Icons/chat_room_icon.png")

        for idx in range(10): # adding 10 chat rooms to the list
            item = QListWidgetItem(chat_icon, f"Chat {idx} abcd")
            list_widget.addItem(item)

        layout = QVBoxLayout()
        layout.addWidget(list_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)



class MainScreen(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        label = QLabel()
        label.setText("MAIN SCREEN")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # =======================================================
        # left panel
        # TO DO:
        #   - add context menu to widgets in list
        #       - mark as read
        #       Chat room:
        #           - add/remove members (if admin)
        #           - delete chatroom (if admin)
        #           - exit chat room
        #       User:
        #           - block user
        #   - make list dynamically update when exiting from a group chat
        #   - make right panel dynamically update when exiting from a group chat
        #   - add search bar (QLineEdit above and connect its text changed signal to a filtering method (contains the string))
        #   - add user profile button

        chat_list = ChatList()

        settings_button = QPushButton()
        settings_button.setText("Settings")
        settings_button.setFixedSize(30, 30)
        settings_button.clicked.connect(self.settings_requested.emit)

        left_panel = QWidget()
        left_panel_layout = QVBoxLayout()

        left_panel_layout.addWidget(chat_list, stretch=5)
        left_panel_layout.addWidget(settings_button, stretch=1)
        left_panel.setLayout(left_panel_layout)

        # =======================================================
        # right panel
        # TO DO:
        #   - make stacked widgets dynamically update when exiting a group chat
        #   - on the top add a button widget with the name of the chat to see its members and admins
        #   - bottom-up list widget (see other ways if it doesn't allow complex formats) for messages
        #       - complex formats: icon, username, edited flag, timestamp, replied to
        #   - add text box to send messages
        #   - add upload file button
        #   - add send message button

        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(label, stretch=3)
        self.setLayout(main_layout)

class SettingsScreen(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.back_button = QPushButton()
        self.back_button.setText("Close")
        self.back_button.setFixedSize(30, 30)
        self.back_button.clicked.connect(self.back_requested.emit)

        self.label = QLabel()
        self.label.setText("SETTINGS SCREEN")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, stretch=1)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter, stretch=5)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OuiChat")
        self.setFixedSize(600, 200)

        self.main_layout = QStackedLayout() # ADD ALL THE OTHER TABS HERE (SETTINGS, ETC.)

        main_screen_widget = MainScreen()
        main_screen_widget.settings_requested.connect(self.go_to_settings)

        settings_screen_widget = SettingsScreen()
        settings_screen_widget.back_requested.connect(self.go_to_main)

        self.main_layout.addWidget(main_screen_widget)
        self.main_layout.addWidget(settings_screen_widget)

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

    def go_to_main(self):
        self.main_layout.setCurrentIndex(0)

    def go_to_settings(self):
        self.main_layout.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication([])
    login = LogInDialog()

    if login.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow()
        main_window.show()
        app.exec()
    else:
        pass