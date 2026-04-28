from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QPushButton, QVBoxLayout, QLineEdit, QLabel, QStackedLayout,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QFormLayout, QMenu,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

from abc import ABC, ABCMeta, abstractmethod

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32

USERNAME = ""
TOKEN = ""
USER_ICON = "./Icons/default_user_icon.png"

# TO BE IMPLEMENTED IN SOME OTHER WAY
CHAT_PRIVILEGE = "admin" # {"default", "admin"}
CHAT_TYPE = "chatroom" # {"p2p", "chatroom"}
CHAT_SETTING = "rw" # {"ro", "rw"}

def make_request(domain: str, user: str, password: str):
    # TO BE IMPLEMENTED
    # RETURNS (TRUE, JWT Token) ON VALID CREDENTIALS AND (FALSE, $ERROR_MESSAGE) OTHERWISE
    return True, "TOKEN"

class LogInDialog(QDialog):
    def __init__(self):
        super().__init__()

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

        self.error_message = QLabel()
        self.error_message.setStyleSheet("color: red;")
        self.error_message.setFixedHeight(25)

        log_in_button = QPushButton("Login")
        log_in_button.setFixedSize(125, 25)
        log_in_button.clicked.connect(self.__validate_credentials)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(form_widget)
        layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(log_in_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.setMaximumSize(535, 195)

    def __validate_credentials(self):
        username = self.username_line_edit.text()
        password = self.password_line_edit.text()
        domain = self.domain_line_edit.text()

        ret = make_request(domain, username, password)

        if ret[0]:
            global TOKEN, USERNAME
            TOKEN = ret[1]
            USERNAME = username
            self.accept()
        else:
            self.error_message.setText(ret[1])

class LeftPanelInteractions(QWidget):
    settings_requested = pyqtSignal()
    user_personalization_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        settings_button = QPushButton()
        settings_button.setFixedSize(40, 40)
        settings_button.setIconSize(QSize(32, 32))
        settings_button.setIcon(QIcon("./Icons/settings_icon.png"))
        settings_button.clicked.connect(self.settings_requested.emit)

        user_button = QPushButton()
        user_button.setFixedSize(180, 40)
        user_button.setIconSize(QSize(32, 32))
        user_button.setIcon(QIcon(USER_ICON))
        user_button.setText(USERNAME)
        user_button.setStyleSheet("text-align: left; padding-left: 10px;")
        user_button.clicked.connect(self.user_personalization_requested.emit)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(user_button)
        layout.addWidget(settings_button)

        self.setLayout(layout)

class QABCMeta(type(QWidget), ABCMeta):
    pass

class GenericList(QWidget, ABC, metaclass=QABCMeta):
    entry_selected = pyqtSignal(int)

    def __init__(self,
                 search_bar_width: int, search_bar_height: int, enable_entry_selection: bool,
                 layout_margins: tuple[int, int, int, int], layout_spacing: int
                 ):
        super().__init__()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedSize(search_bar_width, search_bar_height)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.__search)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setFixedWidth(225)
        self.list_widget.setMinimumHeight(180)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        if enable_entry_selection:
            self.list_widget.currentRowChanged.connect(self.entry_selected.emit)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(layout_margins[0], layout_margins[1], layout_margins[2], layout_margins[3])
        self.layout.setSpacing(layout_spacing)

        self.layout.addWidget(self.search_bar)
        self.layout.addWidget(self.list_widget)
        self.setLayout(self.layout)

    def find_item_by_data(self, key, value):
        items = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            val = item_data.get(key, None)
            if val == value:
                items.append(item)

        return items

    def __search(self, text):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def add_entry(self):
        # TO BE IMPLEMENTED
        pass

    @abstractmethod
    def show_context_menu(self, position):
        pass

class ChatList(GenericList):
    """
    TO DO:
        - implement the context menus
        - send signal to right panel to update when switching chats
        - automatically switch to previous chat (next if the current chat was the 1st one) when deleting current chat
            (MIGHT BE ALREADY IMPLEMENTED BY DEFAULT)
    """

    chat_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__(
            search_bar_width=225, search_bar_height=25,
            enable_entry_selection=True,
            layout_margins=(0, 0, 0, 0), layout_spacing=5
        )

        self.chat_icon = QIcon("./Icons/chat_room_icon.png")
        for idx in range(10): # adding 10 chat rooms to the list
            item = QListWidgetItem(self.chat_icon, f"Chat {idx}")
            item_data = {
                "chat_privilege": CHAT_PRIVILEGE,
                "chat_type": CHAT_TYPE,
                "chat_setting": CHAT_SETTING,
                "chat_id": idx
            }
            item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.list_widget.addItem(item)

        self.new_chat_button = QPushButton()
        self.new_chat_button.setFixedSize(225, 25)
        self.new_chat_button.setIconSize(QSize(16, 16))
        self.new_chat_button.setIcon(QIcon("./Icons/plus_icon.png"))
        self.new_chat_button.setText("New Chat")

        self.layout.addWidget(self.new_chat_button)

    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item: return

        chat_data = item.data(Qt.ItemDataRole.UserRole)
        chat_privilege = chat_data.get("chat_privilege")
        chat_type = chat_data.get("chat_type")
        chat_id = chat_data.get("chat_id")

        exit_chat_action = None
        manage_members_action = None
        delete_chat_action = None
        block_user_action = None

        menu = QMenu()

        mark_read_action = menu.addAction("Mark as Read")
        menu.addSeparator()

        if chat_type == "p2p":
            block_user_action = menu.addAction("Block User")
        else:
            exit_chat_action = menu.addAction("Exit Chat")
            if chat_privilege == "admin":
                menu.addSeparator()
                manage_members_action = menu.addAction("Manage Members")
                delete_chat_action = menu.addAction("Delete Chat")

        global_pos = self.list_widget.mapToGlobal(position)
        selected_action = menu.exec(global_pos)

        # Checking to see if the item wasn't removed while the context menu was opened
        if not item.listWidget(): return

        if selected_action == mark_read_action:
            # TO BE IMPLEMENTED
            pass
        elif selected_action == block_user_action:
            # TO BE IMPLEMENTED
            pass
        elif selected_action == exit_chat_action:
            self.__exit_chat(chat_id)
        elif selected_action == manage_members_action:
            # TO BE IMPLEMENTED
            pass
        elif selected_action == delete_chat_action:
            self.__delete_chat(chat_id)

    def __remove_chat(self, chat_id):
        # CHAT IDs ARE ALWAYS UNIQUE
        item = self.find_item_by_data("chat_id", chat_id)
        row = self.list_widget.row(*item)
        self.list_widget.takeItem(row)

    def __exit_chat(self, chat_id):
        self.__remove_chat(chat_id)
        # IMPLEMENT REQUESTS TO SERVER

    def __delete_chat(self, chat_id):
        self.__remove_chat(chat_id)
        # IMPLEMENT REQUESTS TO SERVER

    def __manage_members(self):
        return

    def __block_user(self):
        return

    def __mark_read(self):
        return

class LeftPanelMain(QWidget):
    settings_requested = pyqtSignal()
    user_personalization_requested = pyqtSignal()
    chat_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        chat_list = ChatList()
        chat_list.chat_selected.connect(self.chat_selected.emit)

        interactions = LeftPanelInteractions()
        interactions.settings_requested.connect(self.settings_requested.emit)
        interactions.user_personalization_requested.connect(self.user_personalization_requested.emit)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(chat_list)
        layout.addWidget(interactions)
        self.setLayout(layout)

        self.setFixedWidth(225)

class ChatHistory(QWidget):
    def __init__(self):
        super().__init__()

class RightPanelMain(QWidget):
    """
    TO DO:
        - make stacked widgets dynamically update when exiting a group chat
        - on the top add a button widget with the name of the chat to see its members and admins
        - bottom-up list widget (see other ways if it doesn't allow complex formats) for messages
            - complex formats: icon, username, edited flag, timestamp, replied to
        - add text box to send messages
        - add upload file button
        - add send message button
    """

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

class MainScreen(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        left_panel = LeftPanelMain()
        left_panel.settings_requested.connect(self.settings_requested.emit)

        right_panel = RightPanelMain()

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)

class SettingsScreen(QWidget):
    """
    TO DO:
        - implement use-cases
    """

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
        layout.addWidget(self.back_button)
        layout.addWidget(self.label)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("OuiChat")
        self.setBaseSize(900, 600)

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