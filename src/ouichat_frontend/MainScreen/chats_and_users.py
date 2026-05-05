from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QComboBox
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QStandardItemModel

from abc import ABC, ABCMeta, abstractmethod

MAX_USERS = 3

LEFT_PANEL_WIDTH = 270

# TO BE IMPLEMENTED IN SOME OTHER WAY
CHAT_PRIVILEGE = "admin" # {"default", "admin"}
CHAT_TYPE = "chatroom" # {"p2p", "chatroom"}
CHAT_SETTING = "rw" # {"ro", "rw"}

class LeftPanelInteractions(QWidget):
    settings_requested = pyqtSignal()
    user_personalization_requested = pyqtSignal()
    user_changed = pyqtSignal(dict)

    def __init__(self, initial_user_data: dict, login_dialog):
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

        user_icon = QIcon(initial_user_data['icon_path'])
        username = initial_user_data['username']
        domain = initial_user_data['domain']

        add_user_icon = QIcon("./Icons/plus_icon.png")

        self.users_dropdown = QComboBox()
        self.users_dropdown.setFixedSize(180, 40)
        self.users_dropdown.setIconSize(QSize(32, 32))
        self.dropdown_model = QStandardItemModel()
        self.users_dropdown.setModel(self.dropdown_model)
        self.users_dropdown.addItem(user_icon, f"{username} ({domain})", userData=initial_user_data)
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
            item_data =  self.users_dropdown.itemData(row)
            self.user_changed.emit(item_data)

        else:
            if self.login_dialog.exec() == QDialog.DialogCode.Accepted:
                user_icon_path = self.login_dialog.user_data['icon_path']
                user_icon = QIcon(self.login_dialog.user_data['icon_path'])
                username = self.login_dialog.user_data['username']
                token = self.login_dialog.user_data['token']
                domain = self.login_dialog.user_data['domain']

                current_user_data = {
                    "username": username,
                    "domain": domain,
                    "icon_path": user_icon_path,
                    "request_token": token,
                    "refresh_token": "REFRESH_TOKEN " + token,
                }

                self.users_dropdown.blockSignals(True)
                self.users_dropdown.insertItem(row, user_icon, f"{username} ({domain})", userData=current_user_data)
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
    entry_selected = pyqtSignal(object) # chat_id + domain

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
        self.search_bar.textChanged.connect(self.search)

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

    def add_entry(self):
        # TO BE IMPLEMENTED
        pass

    @abstractmethod
    def search(self, text):
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
    """

    def __init__(self):
        super().__init__(
            search_bar_width=LEFT_PANEL_WIDTH, search_bar_height=25,
            enable_entry_selection=True,
            layout_margins=(0, 0, 0, 0), layout_spacing=5,
            fixed_width=True, list_width=LEFT_PANEL_WIDTH,
            fixed_height=False, list_height=185
        )

        self.current_user_data = None

        self.chat_icon = QIcon("./Icons/chat_room_icon.png")
        for idx in range(20): # adding 20 chat rooms to the list
            item = QListWidgetItem()
            item.setIcon(self.chat_icon)
            item_data = {
                "chat_privilege": CHAT_PRIVILEGE,
                "chat_type": CHAT_TYPE,
                "chat_setting": CHAT_SETTING,
                "domain": "test.test.ro" if idx < 10 else "test2.test2.ro",
                "chat_id": str(idx),
                "users": [{"username": "fifo",
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
            item.setText(f"{item_data["chat_id"]}")
            item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.list_widget.addItem(item)

        self.new_chat_button = QPushButton()
        self.new_chat_button.setFixedSize(LEFT_PANEL_WIDTH, 25)
        self.new_chat_button.setIconSize(QSize(16, 16))
        self.new_chat_button.setIcon(QIcon("./Icons/plus_icon.png"))
        self.new_chat_button.setText("New Chat")

        self.layout.addWidget(self.new_chat_button)

    def handle_user_change(self, data: dict):
        self.current_user_data = data
        self.list_widget.setCurrentRow(-1)
        self.__set_visibility()

    def __current_user_in_list(self, users_list: list):
        for item in users_list:
            if self.current_user_data["username"] == item["username"]:
                return True
        return False

    def __set_visibility(self):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data["domain"] == self.current_user_data["domain"] and self.__current_user_in_list(item_data["users"]):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def search(self, text):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data["domain"] == self.current_user_data["domain"] and self.__current_user_in_list(item_data["users"]):
                if text == "" or text in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                item.setHidden(True)

    def emit_selected_id(self, row: int):
        if row == -1:
            self.entry_selected.emit(None)
            return

        item = self.list_widget.item(row)
        chat_data = item.data(Qt.ItemDataRole.UserRole)
        self.entry_selected.emit(chat_data)

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

class ChatsAndUsersPanel(QWidget):
    settings_requested = pyqtSignal()
    user_personalization_requested = pyqtSignal()
    chat_selected = pyqtSignal(object)

    def __init__(self, initial_user_data:dict, login_dialog):
        super().__init__()

        chat_list = ChatList()
        interactions = LeftPanelInteractions(initial_user_data, login_dialog)

        chat_list.entry_selected.connect(self.chat_selected.emit)
        chat_list.handle_user_change(initial_user_data)

        interactions.settings_requested.connect(self.settings_requested.emit)
        interactions.user_personalization_requested.connect(self.user_personalization_requested.emit)
        interactions.user_changed.connect(chat_list.handle_user_change)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(chat_list)
        layout.addWidget(interactions)
        self.setLayout(layout)

        self.setFixedWidth(LEFT_PANEL_WIDTH)