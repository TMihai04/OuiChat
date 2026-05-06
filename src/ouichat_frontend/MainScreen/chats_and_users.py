from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QComboBox
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QStandardItemModel

from ouichat_frontend.brain import Brain

MAX_USERS = 3

LEFT_PANEL_WIDTH = 270

# TO BE IMPLEMENTED IN SOME OTHER WAY
CHAT_TYPE = "chatroom" # {"p2p", "chatroom"}
CHAT_SETTING = "rw" # {"ro", "rw"}

class LeftPanelInteractions(QWidget):
    user_changed = pyqtSignal(dict)

    def __init__(self, brain: Brain, login_dialog):
        super().__init__()

        self.brain = brain
        self.login_dialog = login_dialog
        self.previous_user_row = 0

        settings_button = QPushButton()
        settings_button.setFixedSize(40, 40)
        settings_button.setIconSize(QSize(32, 32))
        settings_button.setIcon(QIcon("./Icons/settings_icon.png"))
        settings_button.clicked.connect(self.brain.main_window_settings_requested.emit)

        user_profile_button = QPushButton()
        user_profile_button.setFixedSize(40, 40)
        user_profile_button.setIconSize(QSize(32, 32))
        user_profile_button.setIcon(QIcon("./Icons/user_settings_icon.png"))
        user_profile_button.clicked.connect(self.brain.main_window_user_settings_requested.emit)

        user_icon = QIcon(self.brain.get_current_user_icon())
        username = self.brain.get_current_user_username()
        domain = self.brain.get_current_user_domain()

        add_user_icon = QIcon("./Icons/plus_icon.png")

        self.users_dropdown = QComboBox()
        self.users_dropdown.setFixedSize(180, 40)
        self.users_dropdown.setIconSize(QSize(32, 32))
        self.dropdown_model = QStandardItemModel()
        self.users_dropdown.setModel(self.dropdown_model)
        self.users_dropdown.addItem(user_icon, f"{username} ({domain})")
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
            item_text =  self.users_dropdown.itemText(row)
            item_text = item_text[::-1].split("( ", maxsplit=1) # inverting the text so that our separator (initially ' (' and now '( ') is the first
            username = item_text[1][::-1] # gets the username
            domain = item_text[0][:0:-1] # gets the domain and removes the trailing parentheses
            self.brain.interaction_panel_current_user_changed.emit(username, domain)

        else:
            if self.login_dialog.exec() == QDialog.DialogCode.Accepted:
                self.users_dropdown.blockSignals(True)
                current_user_icon_path = self.brain.get_current_user_icon()
                current_user_icon = QIcon(current_user_icon_path)
                current_user_username = self.brain.get_current_user_username()
                current_user_domain = self.brain.get_current_user_domain()
                self.users_dropdown.insertItem(row, current_user_icon, f"{current_user_username} ({current_user_domain})")
                self.users_dropdown.blockSignals(False)

                self.users_dropdown.setCurrentIndex(row)
                self.previous_user_row = row

            else:
                self.users_dropdown.blockSignals(True)
                self.users_dropdown.setCurrentIndex(self.previous_user_row)
                self.users_dropdown.blockSignals(False)

        num_entries = self.users_dropdown.count()
        if num_entries == MAX_USERS + 1:
            # entry at `idx = MAX_USERS` will always be `Add User`
            self.dropdown_model.item(num_entries - 1).setEnabled(False)
        else:
            self.dropdown_model.item(num_entries - 1).setEnabled(True)

class ChatList(QWidget):
    """
    TO DO:
        - implement the context menus
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.brain.interaction_panel_current_user_changed.connect(self.handle_current_user_changed)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search chat...")
        self.search_bar.setFixedSize(LEFT_PANEL_WIDTH, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setFixedWidth(LEFT_PANEL_WIDTH)
        self.list_widget.setMinimumHeight(185)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.currentRowChanged.connect(self.emit_selected_chat_id_and_domain)

        self.widget_layout = QVBoxLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.widget_layout.addWidget(self.search_bar)
        self.widget_layout.addWidget(self.list_widget)
        self.setLayout(self.widget_layout)

        self.set_chats()
        self.search("")

        self.new_chat_button = QPushButton()
        self.new_chat_button.setFixedSize(LEFT_PANEL_WIDTH, 25)
        self.new_chat_button.setIconSize(QSize(16, 16))
        self.new_chat_button.setIcon(QIcon("./Icons/plus_icon.png"))
        self.new_chat_button.setText("New Chat")

        self.widget_layout.addWidget(self.new_chat_button)

    def find_chat_by_id_and_domain(self, chat_id: str, domain: str):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            chat_name = item.text()
            chat_domain = item_data["domain"]
            if chat_name == chat_id and chat_domain == domain:
                return item
        return None

    def set_chats(self):
        chat_ids = self.brain.get_chat_ids()
        chat_domains = self.brain.get_chat_domains()
        chat_icons = self.brain.get_chat_icons()
        num_chats = len(chat_ids)
        for idx in range(num_chats):
            self.add_chat(chat_ids[idx], chat_domains[idx], chat_icons[idx])

    def add_chat(self, chat_id: str, chat_domain: str, icon_path: str):
        item = QListWidgetItem()
        item.setIcon(QIcon(icon_path))
        item.setText(f"{chat_id}")
        item.setData(Qt.ItemDataRole.UserRole, {"domain": chat_domain})
        item.setHidden(True) # initially all chats are hidden
        self.list_widget.addItem(item)

    def handle_current_user_changed(self):
        self.list_widget.setCurrentRow(-1)
        self.list_widget.verticalScrollBar().setValue(0)
        self.search("")

    def search(self, text: str):
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            chat_id = item.text()
            chat_domain = item.data(Qt.ItemDataRole.UserRole)['domain']
            chat_user_usernames = self.brain.get_chat_user_usernames(chat_id, chat_domain)
            if chat_domain == current_user_domain and current_user_username in chat_user_usernames:
                if text == "" or text in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                item.setHidden(True)

    def emit_selected_chat_id_and_domain(self, row: int):
        if row == -1:
            self.brain.interaction_panel_chat_selected.emit("", "")
            return

        item = self.list_widget.item(row)
        chat_id = item.text()
        chat_domain = item.data(Qt.ItemDataRole.UserRole)['domain']
        self.brain.interaction_panel_chat_selected.emit(chat_id, chat_domain)

    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item: return

        chat_id = item.text()
        chat_domain = item.data(Qt.ItemDataRole.UserRole)['domain']
        chat_type = self.brain.get_chat_type(chat_id, chat_domain)
        user_is_admin = self.brain.user_is_admin(chat_id, chat_domain, self.brain.get_current_user_username())

        exit_chat_action = None
        delete_chat_action = None
        block_user_action = None

        menu = QMenu()

        mark_read_action = menu.addAction("Mark as Read")

        if chat_type == "p2p":
            menu.addSeparator()
            block_user_action = menu.addAction("Block User")
        else:
            menu.addSeparator()
            exit_chat_action = menu.addAction("Exit Chat")
            if user_is_admin:
                menu.addSeparator()
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
            self.__exit_chat(item)
        elif selected_action == delete_chat_action:
            self.__delete_chat(item)

    def __remove_chat(self, entry: QListWidgetItem):
        row = self.list_widget.row(entry)
        self.list_widget.takeItem(row)

    def __exit_chat(self, entry: QListWidgetItem):
        self.__remove_chat(entry)
        # IMPLEMENT REQUESTS TO SERVER

    def __delete_chat(self, entry: QListWidgetItem):
        self.__remove_chat(entry)
        # IMPLEMENT REQUESTS TO SERVER

    def __manage_members(self):
        return

    def __block_user(self):
        return

    def __mark_read(self):
        return

class ChatsAndUsersPanel(QWidget):
    def __init__(self, brain: Brain, login_dialog):
        super().__init__()

        chat_list = ChatList(brain)

        interactions = LeftPanelInteractions(brain, login_dialog)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(chat_list)
        layout.addWidget(interactions)
        self.setLayout(layout)

        self.setFixedWidth(LEFT_PANEL_WIDTH)