from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QPushButton, QVBoxLayout, QLineEdit, QLabel, QStackedLayout,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QFormLayout, QMenu, QComboBox, QTextEdit, QSizePolicy,
    QScrollArea, QBoxLayout,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QStandardItemModel, QPixmap, QFontMetrics

from abc import ABC, ABCMeta, abstractmethod

import time

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32
MAX_USERS = 3

LEFT_PANEL_WIDTH = 270
RIGHT_PANE_MIN_WIDTH = 310

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

        self.user_data = {
            "username": "",
            "password": "",
            "token": "",
            "icon_path": "",
            "domain": ""
        }

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
        log_in_button.setAutoDefault(False)
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
            self.username_line_edit.clear()
            self.password_line_edit.clear()
            self.domain_line_edit.clear()

            # IMPLEMENT INFO RETRIEVAL
            self.user_data['username'] = username
            self.user_data['password'] = password
            self.user_data['token'] = ret[1]
            self.user_data['icon_path'] = "./Icons/default_user_icon.png"
            self.user_data['domain'] = domain

            self.accept()
        else:
            self.error_message.setText(ret[1])

class LeftPanelInteractions(QWidget):
    settings_requested = pyqtSignal()
    user_personalization_requested = pyqtSignal()
    user_changed = pyqtSignal(str, str)

    def __init__(self, initial_user_username: str, initial_user_password: str,
                 initial_user_token: str, initial_user_icon_path: str, initial_user_domain: str,
                 login_dialog):
        super().__init__()

        self.login_dialog = login_dialog
        self.previous_user_row = 0

        settings_button = QPushButton()
        settings_button.setFixedSize(40, 40)
        settings_button.setIconSize(QSize(32, 32))
        settings_button.setIcon(QIcon("./Icons/settings_icon.png"))
        settings_button.clicked.connect(self.settings_requested.emit)

        user_profile_button = QPushButton()
        user_profile_button.setFixedSize(40, 40)
        user_profile_button.setIconSize(QSize(32, 32))
        user_profile_button.setIcon(QIcon("./Icons/user_settings_icon.png"))
        user_profile_button.clicked.connect(self.user_personalization_requested.emit)

        user_icon = QIcon(initial_user_icon_path)
        username = initial_user_username
        token = initial_user_token
        password = initial_user_password
        domain = initial_user_domain

        add_user_icon = QIcon("./Icons/plus_icon.png")

        self.users_dropdown = QComboBox()
        self.users_dropdown.setFixedSize(180, 40)
        self.users_dropdown.setIconSize(QSize(32, 32))
        self.dropdown_model = QStandardItemModel()
        self.users_dropdown.setModel(self.dropdown_model)
        self.users_dropdown.addItem(user_icon, f"{username} ({domain})", userData={"token": token,
                                                              "password": password,
                                                              "domain": domain})
        self.users_dropdown.addItem(add_user_icon, "Add User")
        self.users_dropdown.currentIndexChanged.connect(self.handle_users_dropdown)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.users_dropdown)
        layout.addWidget(user_profile_button)
        layout.addWidget(settings_button)

        self.setLayout(layout)

    def handle_users_dropdown(self, row:int):
        num_entries = self.users_dropdown.count()
        if row != num_entries - 1:
            username = self.users_dropdown.itemText(row)
            domain = self.users_dropdown.itemData(row)['domain']
            self.user_changed.emit(username, domain)

        else:
            if self.login_dialog.exec() == QDialog.DialogCode.Accepted:
                user_icon = QIcon(self.login_dialog.user_data['icon_path'])
                username = self.login_dialog.user_data['username']
                token = self.login_dialog.user_data['token']
                password = self.login_dialog.user_data['password']
                domain = self.login_dialog.user_data['domain']

                self.users_dropdown.blockSignals(True)
                self.users_dropdown.insertItem(row, user_icon, f"{username} ({domain})", userData={"token": token,
                                                                           "password": password,
                                                                           "domain": domain})
                self.users_dropdown.blockSignals(False)

                self.users_dropdown.setCurrentIndex(row)
                self.previous_user_row = row

            else:
                self.users_dropdown.blockSignals(True)
                self.users_dropdown.setCurrentIndex(self.previous_user_row)
                self.users_dropdown.blockSignals(False)

        num_entries = self.users_dropdown.count()
        if num_entries == MAX_USERS + 1:
            # entry at `user_count` will always be `Add User`
            self.dropdown_model.item(num_entries - 1).setEnabled(False)
        else:
            self.dropdown_model.item(num_entries - 1).setEnabled(True)


class QABCMeta(type(QWidget), ABCMeta):
    pass

class GenericList(QWidget, ABC, metaclass=QABCMeta):
    entry_selected = pyqtSignal(str, str) # chat_id + domain

    def __init__(self,
                 search_bar_width: int, search_bar_height: int, enable_entry_selection: bool,
                 layout_margins: tuple[int, int, int, int], layout_spacing: int,
                 fixed_width: bool, list_width: int | None, fixed_height: bool, list_height: int | None
                 ):
        super().__init__()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search chat...")
        self.search_bar.setFixedSize(search_bar_width, search_bar_height)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.__search)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        if list_width is not None:
            if fixed_width:
                self.list_widget.setFixedWidth(list_width)
            else:
                self.list_widget.setMinimumWidth(list_width)
        if list_height is not None:
            if fixed_height:
                self.list_widget.setFixedHeight(list_height)
            else:
                self.list_widget.setMinimumHeight(list_height)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        if enable_entry_selection:
            self.list_widget.currentRowChanged.connect(self.emit_selected_id)

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
    def emit_selected_id(self, row: int):
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

    def __init__(self):
        super().__init__(
            search_bar_width=LEFT_PANEL_WIDTH, search_bar_height=25,
            enable_entry_selection=True,
            layout_margins=(0, 0, 0, 0), layout_spacing=5,
            fixed_width=True, list_width=LEFT_PANEL_WIDTH,
            fixed_height=False, list_height=185
        )


        self.chat_icon = QIcon("./Icons/chat_room_icon.png")
        for idx in range(20): # adding 20 chat rooms to the list
            item = QListWidgetItem()
            item.setIcon(self.chat_icon)
            item_data = {
                "chat_privilege": CHAT_PRIVILEGE,
                "chat_type": CHAT_TYPE,
                "chat_setting": CHAT_SETTING,
                "domain": "test.test.ro" if idx < 10 else "test2.test2.ro",
                "chat_id": str(idx)
            }
            item.setText(f"{item_data["chat_id"]} ({item_data["domain"]})")
            item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.list_widget.addItem(item)

        self.new_chat_button = QPushButton()
        self.new_chat_button.setFixedSize(LEFT_PANEL_WIDTH, 25)
        self.new_chat_button.setIconSize(QSize(16, 16))
        self.new_chat_button.setIcon(QIcon("./Icons/plus_icon.png"))
        self.new_chat_button.setText("New Chat")

        self.layout.addWidget(self.new_chat_button)

    def emit_selected_id(self, row: int):
        if row == -1:
            self.entry_selected.emit(None, None)
            return

        item = self.list_widget.item(row)
        chat_data = item.data(Qt.ItemDataRole.UserRole)
        self.entry_selected.emit(chat_data['chat_id'], chat_data['domain'])

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
    chat_selected = pyqtSignal(str, str)

    def __init__(self, initial_user_username: str, initial_user_password: str,
                 initial_user_token: str, initial_user_icon_path: str, initial_user_domain: str,
                 login_dialog):
        super().__init__()

        chat_list = ChatList()
        chat_list.entry_selected.connect(self.chat_selected.emit)

        interactions = LeftPanelInteractions(initial_user_username, initial_user_password,
                                             initial_user_token, initial_user_icon_path, initial_user_domain, login_dialog)
        interactions.settings_requested.connect(self.settings_requested.emit)
        interactions.user_personalization_requested.connect(self.user_personalization_requested.emit)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(chat_list)
        layout.addWidget(interactions)
        self.setLayout(layout)

        self.setFixedWidth(LEFT_PANEL_WIDTH)

class ElidedLabel(QLabel):
    def __init__(self, text: str = ""):
        super().__init__()

        self.full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.update_elided_text()

    def setText(self, text):
        self.full_text = text
        self.update_elided_text()

    def resizeEvent(self, event):
        self.update_elided_text()
        super().resizeEvent(event)

    def update_elided_text(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.full_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)

    def minimumSizeHint(self):
        return QSize(10, super().minimumSizeHint().height())

    def sizeHint(self):
        return QSize(100, super().sizeHint().height())

class ChatMessage(QWidget):
    def __init__(self, message_id: str, sender: str, sender_icon_path: str, was_edited: bool, is_reply: bool,
                 reply_sender: str | None, reply_sender_icon_path: str | None, reply_snip: str | None, timestamp: str,
                 text: str):
        super().__init__()

        self.message_id = message_id

        self.sender = sender
        self.sender_icon_path = sender_icon_path
        sender_icon = QLabel()
        sender_pixmap = QPixmap(sender_icon_path).scaled(32, 32)
        sender_icon.setPixmap(sender_pixmap)

        self.text = text
        self.was_edited = was_edited

        reply_area = QWidget()
        reply_area.setFixedHeight(25)

        if is_reply:
            reply_area_layout = QHBoxLayout()
            reply_area_layout.setContentsMargins(0, 0, 0, 0)
            reply_area_layout.setSpacing(5)
            reply_area.setLayout(reply_area_layout)

            replied_to_label = QLabel()
            replied_to_label.setText("Replied to:")
            replied_to_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            reply_sender_icon = QLabel()
            reply_sender_pixmap = QPixmap(reply_sender_icon_path).scaled(24, 24)
            reply_sender_icon.setPixmap(reply_sender_pixmap)

            replied_to_user_label = QLabel()
            replied_to_user_label.setText(reply_sender)
            replied_to_user_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            reply_snip_label = ElidedLabel()
            reply_snip_label.setText(reply_snip)

            reply_area_layout.addWidget(replied_to_label)
            reply_area_layout.addWidget(reply_sender_icon)
            reply_area_layout.addWidget(replied_to_user_label)
            reply_area_layout.addWidget(reply_snip_label)

        self.message_details = QLabel()
        self.message_details.setFixedHeight(25)
        self.message_details.setText(f"{sender} - {timestamp}{" (Edited)" if was_edited else ""}")
        self.message_details.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.message_text = QLabel()
        self.message_text.setText(self.text)
        self.message_text.setWordWrap(True)

        message_area = QWidget()
        message_area_layout = QVBoxLayout()
        message_area_layout.setContentsMargins(0, 0, 0, 0)
        message_area_layout.setSpacing(5)
        message_area.setLayout(message_area_layout)

        if is_reply:
            message_area_layout.addWidget(reply_area)
        message_area_layout.addWidget(self.message_details)
        message_area_layout.addWidget(self.message_text)
        message_area_layout.addStretch()

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        self.setLayout(top_layout)

        top_layout.addWidget(sender_icon, alignment=Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(message_area, stretch=1)

    def edit_text(self, text):
        self.message_text.setText(text)

        if not self.was_edited:
            old_message_details = self.message_details.text()
            new_message_details = old_message_details + " (Edited)"
            self.message_details.setText(new_message_details)
            self.was_edited = True

class ChatBubble(QScrollArea):
    """
    TO DO:
        - finish implementing chat bubble
        - add dummy messages to see how they get displayed (debug messages if needed)
        - implement context menu for messages (reply, edit, delete)
    """
    def __init__(self, chat_id: str, domain:str, last_access_time: float):
        super().__init__()

        self.chat_id = chat_id
        self.domain = domain
        self.last_access_time = last_access_time

        self.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(5)
        self.container_layout.setDirection(QBoxLayout.Direction.BottomToTop)
        self.container.setLayout(self.container_layout)

        self.setWidget(self.container)

    def load_messages(self, message_count: int, last_loaded_message_id: str | None):

        for idx in range(20):
            is_reply = idx % 2 == 1
            was_edited = idx % 4 == 0 or idx % 4 == 1

            local_time = time.localtime(time.time())
            formated_time = time.strftime("%H:%M:%S %d/%m/%Y", local_time)

            message = ChatMessage(message_id=f"{idx}",
                                  sender=f"TEST_SENDER_{idx}",
                                  sender_icon_path="./Icons/default_user_icon.png",
                                  was_edited=was_edited,
                                  is_reply=is_reply,
                                  reply_sender=f"TEST_REPLY_{idx}",
                                  reply_sender_icon_path=f"./Icons/default_user_icon.png",
                                  reply_snip="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                                  timestamp=formated_time,
                                  text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.")
            self.container_layout.addWidget(message)

        # REQUEST MESSAGES

    def __send_message(self):
        # SEND MESSAGE TO SERVER
        pass

class ChatHistory(QWidget):
    """
    TO DO:
        - finish implementing chat history
        - implement hard limit on the nr of bubbles
        - implement least recently used cache for bubbles to figure which one to remove
    """
    def __init__(self):
        super().__init__()

        self.max_bubbles = 17 # 15 bubbles + 1 screen for no chats + 1 screen for loading messages

        self.layout = QStackedLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        self.setLayout(self.layout)

        no_chats_label = QLabel()
        no_chats_label.setText("Select a chat to vent to.")
        no_chats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.insertWidget(0, no_chats_label)

        loading_messages_label = QLabel()
        loading_messages_label.setText("Loading messages ...")
        loading_messages_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.insertWidget(1, loading_messages_label)

        self.layout.setCurrentIndex(0)

    def show_chat(self, chat_id: str | None, chat_domain: str | None):
        if chat_id is None and chat_domain is None:
            self.layout.setCurrentIndex(0)
            return

        for idx in range(self.layout.count()):
            widget = self.layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == chat_domain:
                    self.layout.setCurrentIndex(idx)
                    widget.last_access_time = time.time()
                    return

        self.__add_bubble(chat_id, chat_domain)

    def remove_chat(self, chat_id: str, chat_domain: str):
        for idx in range(self.layout.count()):
            widget = self.layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == chat_domain:
                    self.layout.removeWidget(widget)
                    return

    def __add_bubble(self, chat_id: str, chat_domain: str):
        bubble_count = self.layout.count()
        if bubble_count >= self.max_bubbles:
            oldest_widget = None
            oldest_access_time = time.time()
            for idx in range(bubble_count):
                widget = self.layout.widget(idx)
                if isinstance(widget, ChatBubble):
                    access_time = widget.last_access_time
                    if access_time < oldest_access_time:
                        oldest_widget = widget
                        oldest_access_time = access_time

            self.layout.removeWidget(oldest_widget)

        current_time = time.time()
        new_bubble = ChatBubble(chat_id, chat_domain, current_time)
        self.layout.insertWidget(2, new_bubble)
        # at index 0 there is a special screen for when there are no chats selected
        # at index 1 there is a special screen for when messages are loading

        self.layout.setCurrentIndex(1)
        new_bubble.load_messages(50, None)
        self.layout.setCurrentIndex(2)

    def add_message(self, chat_id: str, chat_domain:str, message: ChatMessage):
        pass

class ChatTextBox(QTextEdit):
    def __init__(self):
        super().__init__()

        self.init_height = 25
        self.max_height = 73

        self.setPlaceholderText("Start typing...")
        self.setFixedHeight(self.init_height)
        self.setMinimumWidth(50)

    def __send_message(self):
        message = self.toPlainText().strip()
        if message:
            # IMPLEMENT SEND MESSAGE REQUESTS
            # MAKE SURE TO DELETE MESSAGE ONLY IF MESSAGE WAS SENT SUCCESSFULLY
            self.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.__send_message()
                event.accept()
        else:
            super().keyPressEvent(event)

class MessageWindow(QWidget):
    def __init__(self):
        super().__init__()

        upload_file_button = QPushButton()
        upload_file_button.setFixedSize(40, 40)
        upload_file_button.setIconSize(QSize(32, 32))
        upload_file_button.setIcon(QIcon("./Icons/upload_file_icon.png"))
        upload_file_button.clicked.connect(self.__upload_file)

        send_message_button = QPushButton()
        send_message_button.setFixedSize(40, 40)
        send_message_button.setIconSize(QSize(32, 32))
        send_message_button.setIcon(QIcon("./Icons/send_message_icon.png"))
        send_message_button.clicked.connect(self.__send_message)

        self.text_box = ChatTextBox()
        self.text_box.setMinimumWidth(200)
        self.text_box.textChanged.connect(self.__resize_text_box)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(upload_file_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.text_box)
        layout.addWidget(send_message_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setVisible(False) # initially not visible due to no chat being selected

    def set_visibility(self, chat_id: str, domain: str):
        if chat_id != "" and domain != "":
            self.setVisible(True)
        else:
            self.setVisible(False)

    def __resize_text_box(self):
        text_height = int(self.text_box.document().size().height())
        box_height = self.text_box.height()

        if text_height > self.text_box.max_height: return
        else:
            if text_height != box_height:
                self.text_box.setFixedHeight(text_height)

    def __upload_file(self):
        pass

    def __send_message(self):
        pass

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

        self.chat_history = ChatHistory()
        self.message_window = MessageWindow()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_window, alignment=Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setMinimumWidth(RIGHT_PANE_MIN_WIDTH)

class MainScreen(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, initial_user_username: str, initial_user_password: str,
                 initial_user_token: str, initial_user_icon_path: str, initial_user_domain: str,
                 login_dialog):
        super().__init__()

        left_panel = LeftPanelMain(initial_user_username, initial_user_password,
                                   initial_user_token, initial_user_icon_path, initial_user_domain, login_dialog)

        right_panel = RightPanelMain()
        left_panel.chat_selected.connect(right_panel.message_window.set_visibility)

        left_panel.settings_requested.connect(self.settings_requested.emit)
        left_panel.chat_selected.connect(right_panel.chat_history.show_chat)

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
    def __init__(self, initial_user_username: str, initial_user_password: str,
                 initial_user_token: str, initial_user_icon_path: str, initial_user_domain: str,
                 login_dialog):
        super().__init__()

        self.setWindowTitle("OuiChat")

        self.main_layout = QStackedLayout() # ADD ALL THE OTHER TABS HERE (SETTINGS, ETC.)

        main_screen_widget = MainScreen(initial_user_username, initial_user_password,
                                        initial_user_token, initial_user_icon_path, initial_user_domain, login_dialog)
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
        main_window = MainWindow(login.user_data['username'], login.user_data['password'],
                                 login.user_data['token'], login.user_data['icon_path'], login.user_data['domain'],
                                 login)
        main_window.show()
        app.exec()
    else:
        pass