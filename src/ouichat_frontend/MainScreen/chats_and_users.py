from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit,
    QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QMenu, QComboBox, QApplication
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QStandardItemModel, QPixmap, QPainter, QMouseEvent

from dialogs import LogInDialog, AddUsersDialog, ErrorDialog
from brain import Brain

MAX_USERS = 3

LEFT_PANEL_WIDTH = 270

class LeftPanelInteractions(QWidget):
    user_changed = pyqtSignal(dict)

    def __init__(self, app: QApplication, brain: Brain, login_dialog: LogInDialog):
        super().__init__()

        self.app = app

        self.brain = brain
        self.brain.user_updated.connect(self.handle_user_updated)
        self.brain.logout_user.connect(self.logout_user)
        self.brain.select_previous_user.connect(self.select_previous_user)

        self.login_dialog = login_dialog
        self.previous_user_row = 0

        settings_button = QPushButton()
        settings_button.setFixedSize(40, 40)
        settings_button.setIconSize(QSize(32, 32))
        settings_button.setIcon(QIcon("./Icons/settings_icon.png"))
        settings_button.clicked.connect(self.brain.main_window_settings_requested.emit)
        settings_button.setCursor(Qt.CursorShape.PointingHandCursor)

        user_profile_button = QPushButton()
        user_profile_button.setFixedSize(40, 40)
        user_profile_button.setIconSize(QSize(32, 32))
        user_profile_button.setIcon(QIcon("./Icons/user_settings_icon.png"))
        user_profile_button.clicked.connect(self.brain.main_window_user_settings_requested.emit)
        user_profile_button.setCursor(Qt.CursorShape.PointingHandCursor)

        user_icon = QIcon(self.brain.get_current_user_icon())
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()

        add_user_icon = QIcon("./Icons/plus_icon.png")

        self.users_dropdown = QComboBox()
        self.users_dropdown.setFixedSize(180, 40)
        self.users_dropdown.setIconSize(QSize(32, 32))
        self.dropdown_model = QStandardItemModel()
        self.users_dropdown.setModel(self.dropdown_model)
        self.users_dropdown.addItem(user_icon, f"{current_user_username} ({current_user_domain})",
                                    {"username": current_user_username,
                                     "domain": current_user_domain}
                                    )
        self.users_dropdown.addItem(add_user_icon, "Add User")
        self.users_dropdown.currentIndexChanged.connect(self.handle_users_dropdown)
        self.users_dropdown.setCursor(Qt.CursorShape.PointingHandCursor)
        self.users_dropdown.view().setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.users_dropdown)
        layout.addWidget(user_profile_button)
        layout.addWidget(settings_button)

        self.setLayout(layout)

    def select_previous_user(self):
        target_row = self.previous_user_row
        self.users_dropdown.blockSignals(True)
        self.users_dropdown.setCurrentIndex(target_row)
        self.users_dropdown.blockSignals(False)
        self.previous_user_row = -1
        self.handle_users_dropdown(target_row)

    def logout_user(self, username: str, domain: str):
        for row in range(self.users_dropdown.count() - 1):
            item_data = self.users_dropdown.itemData(row)
            if item_data['username'] == username and item_data['domain'] == domain:
                self.users_dropdown.blockSignals(True)
                self.users_dropdown.removeItem(row)
                self.users_dropdown.blockSignals(False)
                self.previous_user_row = row - 1 if row > 0 else 0
                break

    def handle_user_updated(self, username: str, domain: str):
        logged_users = self.brain.get_logged_users()

        for user in logged_users:
            if user['username'] == username and user['domain'] == domain:
                self.update_user(user['username'], user['domain'])
                return

    def update_user(self, username: str, domain: str):
        for idx in range(self.users_dropdown.count()):
            item_data = self.users_dropdown.itemData(idx)
            if item_data is None: continue
            if item_data['username'] == username and item_data['domain'] == domain:
                user_icon = self.brain.get_user_icon_path(username, domain)
                self.users_dropdown.setItemIcon(idx, QIcon(user_icon))
                return

    def handle_users_dropdown(self, row:int):
        self.brain.set_current_user_last_seen_time_current_chat()

        num_entries = self.users_dropdown.count()
        if row != num_entries - 1:
            if row == self.previous_user_row: return
            item_data =  self.users_dropdown.itemData(row)
            success, error_msg = self.brain.set_current_user(item_data['username'], item_data['domain'])
            if not success:
                error_dialog = ErrorDialog()
                error_dialog.set_error_message(error_msg)
                error_dialog.exec()
                return

            self.previous_user_row = row

        else:
            if self.login_dialog.exec() == QDialog.DialogCode.Accepted:
                self.users_dropdown.blockSignals(True)
                current_user_icon_path = self.brain.get_current_user_icon()
                current_user_icon = QIcon(current_user_icon_path)
                current_user_username = self.brain.get_current_user_username()
                current_user_domain = self.brain.get_current_user_domain()
                self.users_dropdown.insertItem(row, current_user_icon, f"{current_user_username} ({current_user_domain})",
                                               {"username": current_user_username,
                                                "domain": current_user_domain})
                self.users_dropdown.setCurrentIndex(row)
                self.previous_user_row = row
                self.users_dropdown.blockSignals(False)

            else:
                if self.users_dropdown.count() == 1:
                    self.app.quit()
                    return

                self.users_dropdown.blockSignals(True)
                self.users_dropdown.setCurrentIndex(self.previous_user_row)
                self.users_dropdown.blockSignals(False)

        num_entries = self.users_dropdown.count()
        if num_entries == MAX_USERS + 1:
            # entry at `idx = MAX_USERS` will always be `Add User`
            self.dropdown_model.item(num_entries - 1).setEnabled(False)
        else:
            self.dropdown_model.item(num_entries - 1).setEnabled(True)

def get_icon_with_badge(icon_path: str, has_unread: bool):
    base_pixmap = QPixmap(icon_path).scaled(32, 32)
    if not has_unread:
        return QIcon(base_pixmap)

    painter = QPainter(base_pixmap)
    badge_path = "./Icons/new_messages_icon.png"
    badge_pixmap = QPixmap(badge_path).scaled(16, 16)
    x_pos = base_pixmap.width() - badge_pixmap.width()
    y_pos = base_pixmap.height() - badge_pixmap.height()
    painter.drawPixmap(x_pos, y_pos, badge_pixmap)
    painter.end()
    return QIcon(base_pixmap)

class CustomListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

class CustomListWidgetItem(QListWidgetItem):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

    def __lt__(self, other: QListWidgetItem):
        left_item_data = self.data(Qt.ItemDataRole.UserRole)
        left_chat_id = left_item_data['chat_id']
        left_domain = left_item_data['domain']
        left_last_message_timestamp = self.brain.get_last_message_timestamp(left_chat_id, left_domain) or 0

        right_item_data = other.data(Qt.ItemDataRole.UserRole)
        right_chat_id = right_item_data['chat_id']
        right_domain = right_item_data['domain']
        right_last_message_timestamp = self.brain.get_last_message_timestamp(right_chat_id, right_domain) or 0

        if left_last_message_timestamp != right_last_message_timestamp:
            return left_last_message_timestamp < right_last_message_timestamp
        else:
            return self.text().lower() > other.text().lower()

class ChatList(QWidget):
    def __init__(self, brain: Brain, add_users_dialog: AddUsersDialog):
        super().__init__()

        self.add_users_dialog = add_users_dialog

        self.brain = brain
        self.brain.current_user_changed.connect(self.handle_current_user_changed)
        self.brain.chat_updated.connect(self.update_chat)
        self.brain.user_updated.connect(self.update_user_chat)
        self.brain.last_seen_time_updated.connect(self.handle_last_seen_time_update)
        self.brain.chats_added.connect(self.add_chats)
        self.brain.select_chat.connect(self.select_chat)
        self.brain.timestamps_updated.connect(self.sort_items)
        self.brain.remove_domain.connect(self.remove_domain_chats)
        self.brain.remove_chats.connect(self.remove_chats_by_dict)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search chat...")
        self.search_bar.setFixedSize(LEFT_PANEL_WIDTH, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.search)

        self.list_widget = CustomListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setFixedWidth(LEFT_PANEL_WIDTH)
        self.list_widget.setMinimumHeight(185)
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
        self.new_chat_button.setFixedHeight(37)
        self.new_chat_button.setIconSize(QSize(16, 16))
        self.new_chat_button.setIcon(QIcon("./Icons/plus_icon.png"))
        self.new_chat_button.setText("New Chat")
        self.new_chat_button.clicked.connect(self.create_chat)
        self.new_chat_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.widget_layout.addWidget(self.new_chat_button)

    def remove_chats_by_dict(self, chats: dict):
        domain = chats['domain']
        for row in reversed(range(self.list_widget.count())):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['chat_id'] in chats['chat_ids'] and item_data['domain'] == domain:
                is_selected = item.isSelected()
                if is_selected:
                    self.list_widget.setCurrentRow(-1)
                removed_item = self.list_widget.takeItem(row)
                if removed_item: del removed_item

    def update_user_chat(self, username: str, domain: str):
        current_user_username = self.brain.get_current_user_username()
        if username == current_user_username: return
        chat_id = self.brain.p2p_chat_exists(current_user_username, username, domain)
        if chat_id is None: return
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['chat_id'] == chat_id and item_data['domain'] == domain:
                self.__set_entry_characteristics(item, item_data['chat_id'], item_data['domain'])
                return

    def create_chat(self):
        if self.add_users_dialog.isVisible():
            self.add_users_dialog.raise_()
            self.add_users_dialog.activateWindow()
            return

        self.add_users_dialog.reset_chat_details()
        ret = self.add_users_dialog.exec()
        if ret == QDialog.DialogCode.Accepted:
            chat_details = self.add_users_dialog.get_chat_details()
            chat_id = chat_details['chat_id'] if chat_details['chat_id'] is not None else ""
            domain = chat_details['domain'] if chat_details['domain'] is not None else ""
            self.brain.select_chat.emit(chat_id, domain)

    def find_chat_by_id_and_domain(self, chat_id: str, domain: str):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            item_chat_id = item_data['chat_id']
            item_domain = item_data["domain"]
            if item_chat_id == chat_id and item_domain == domain:
                return item
        return None

    def sort_items(self):
        self.list_widget.blockSignals(True)
        self.list_widget.sortItems(Qt.SortOrder.DescendingOrder)
        self.list_widget.blockSignals(False)

    def set_chats(self):
        chats_data = self.brain.get_chats()
        for chat in chats_data:
            self.add_chat(chat['chat_id'], chat['domain'])
        self.sort_items()

    def set_unread_icon(self,  item: QListWidgetItem, chat_id: str, chat_domain: str, has_unread: bool = False):
        icon_path = self.brain.get_chat_icon_path(chat_id, chat_domain)
        item.setIcon(get_icon_with_badge(icon_path, has_unread))

    def __set_entry_characteristics(self, item: QListWidgetItem, chat_id: str, chat_domain: str):
        current_user_last_seen_time = self.brain.get_current_user_last_seen_time(chat_id, chat_domain)
        chat_last_message_timestamp = self.brain.get_last_message_timestamp(chat_id, chat_domain)

        has_unread = False
        if current_user_last_seen_time and chat_last_message_timestamp:
            current_chat_id = self.brain.get_current_chat_id()
            current_chat_domain = self.brain.get_current_chat_domain()
            chat_currently_selected = current_chat_id == chat_id and current_chat_domain == chat_domain
            has_unread = chat_last_message_timestamp > current_user_last_seen_time and not chat_currently_selected

        icon_path = self.brain.get_chat_icon_path(chat_id, chat_domain)
        item.setIcon(get_icon_with_badge(icon_path, has_unread))
        name = self.brain.get_chat_display_name(chat_id, chat_domain)
        item.setText(f"{name}")

    def select_chat(self, chat_id: str, domain: str):
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['chat_id'] == chat_id and item_data['domain'] == domain:
                self.list_widget.setCurrentRow(idx)
                return

        self.list_widget.setCurrentRow(-1)

    def add_chats(self, chats: list):
        for chat in chats:
            self.add_chat(chat['chat_id'], chat['domain'])
        self.sort_items()
        search_text = self.search_bar.text()
        self.search(search_text)

    def add_chat(self, chat_id: str, chat_domain: str):
        item = CustomListWidgetItem(self.brain)
        self.__set_entry_characteristics(item, chat_id, chat_domain)
        item.setData(Qt.ItemDataRole.UserRole,
                     {
                         "chat_id": chat_id,
                         "domain": chat_domain,
                     })
        item.setHidden(True) # initially all chats are hidden
        self.list_widget.addItem(item)

    def handle_current_user_changed(self):
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentRow(-1)
        self.list_widget.verticalScrollBar().setValue(0)
        self.list_widget.blockSignals(False)

        self.brain.chat_selected.emit("", "")

        current_user_domain = self.brain.get_current_user_domain()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['domain'] == current_user_domain:
                self.__set_entry_characteristics(item, item_data['chat_id'], item_data['domain'])

        self.search("")

    def update_chat(self, chat_id: str, domain: str):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['chat_id'] == chat_id and item_data['domain'] == domain:
                self.__set_entry_characteristics(item, item_data["chat_id"], item_data["domain"])

    def handle_last_seen_time_update(self, chat_id: str, domain: str):
        current_user_domain = self.brain.get_current_user_domain()

        if current_user_domain != domain: return # update for a chat that is not in the same domain as the user

        current_user_last_seen_time = self.brain.get_current_user_last_seen_time(chat_id, domain)
        if current_user_last_seen_time is None: return # update for a chat in the same domain as the user but the user isn't a member of the chat

        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['chat_id'] == chat_id and item_data['domain'] == domain:
                chat_last_message_timestamp = self.brain.get_last_message_timestamp(chat_id, domain)
                if chat_last_message_timestamp is None: return

                current_chat_id = self.brain.get_current_chat_id()
                current_chat_domain = self.brain.get_current_chat_domain()

                chat_currently_selected = current_chat_id == chat_id and current_chat_domain == domain

                has_unread = chat_last_message_timestamp > current_user_last_seen_time and not chat_currently_selected
                self.set_unread_icon(item, chat_id, domain, has_unread)

    def search(self, text: str):
        text = text.lower()
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            chat_id = item_data['chat_id']
            chat_domain = item_data['domain']
            chat_user_usernames = self.brain.get_chat_user_usernames(chat_id, chat_domain)
            if chat_domain == current_user_domain and current_user_username in chat_user_usernames:
                if text == "" or text in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                item.setHidden(True)

    def emit_selected_chat_id_and_domain(self, row: int):
        self.brain.set_current_user_last_seen_time_current_chat()

        if row == -1:
            self.brain.chat_selected.emit("", "")
            return

        item = self.list_widget.item(row)
        item_data = item.data(Qt.ItemDataRole.UserRole)
        chat_id = item_data['chat_id']
        chat_domain = item_data['domain']

        self.brain.set_current_user_last_seen_time(chat_id, chat_domain)
        self.set_unread_icon(item, chat_id, chat_domain, False)

        self.brain.chat_selected.emit(chat_id, chat_domain)

    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item: return

        current_user_username = self.brain.get_current_user_username()

        item_data = item.data(Qt.ItemDataRole.UserRole)
        chat_id = item_data['chat_id']
        chat_domain = item_data['domain']
        chat_type = self.brain.get_chat_type(chat_id, chat_domain)
        user_is_admin = self.brain.user_is_admin(chat_id, chat_domain, current_user_username)

        other_user_username = None
        if chat_type == "direct":
            chat_usernames = self.brain.get_chat_user_usernames(chat_id, chat_domain)
            other_user_username = chat_usernames[0] if chat_usernames[0] != current_user_username else chat_usernames[1]

        exit_chat_action = object()
        delete_chat_action = object()
        block_user_action = object()
        unblock_user_action = object()

        menu = QMenu()

        mark_read_action = menu.addAction("Mark as Read")

        if chat_type == "direct":
            other_user_is_blocked = self.brain.user_is_blocked(other_user_username)
            if not other_user_is_blocked:
                menu.addSeparator()
                block_user_action = menu.addAction("Block User")
            else:
                menu.addSeparator()
                unblock_user_action = menu.addAction("Unblock User")
        else:
            menu.addSeparator()
            exit_chat_action = menu.addAction("Exit Chat")
            if user_is_admin:
                menu.addSeparator()
                delete_chat_action = menu.addAction("Delete Chat")

        global_pos = self.list_widget.mapToGlobal(position)

        previous_row = self.list_widget.currentRow()
        self.list_widget.blockSignals(True)

        selected_action = menu.exec(global_pos)

        # the list widgets auto selects the first widget if no widget was selected and a context menu appeared
        if self.list_widget.currentRow() != previous_row:
            self.list_widget.setCurrentRow(previous_row)
        self.list_widget.blockSignals(False)

        # Checking to see if the item wasn't removed while the context menu was opened
        if not item.listWidget(): return

        if selected_action == mark_read_action:
            self.__mark_read(item)

        elif selected_action == block_user_action:
            self.__change_block_status(item, True)

        elif selected_action == unblock_user_action:
            self.__change_block_status(item, False)

        elif selected_action == exit_chat_action:
            self.__exit_chat(item)

        elif selected_action == delete_chat_action:
            self.__delete_chat(item)

    def __change_block_status(self, item: QListWidgetItem, status: bool):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        chat_id = item_data['chat_id']
        domain = item_data['domain']

        current_user_username = self.brain.get_current_user_username()

        chat_usernames = self.brain.get_chat_user_usernames(chat_id, domain)
        other_user_username = chat_usernames[0] if chat_usernames[0] != current_user_username else chat_usernames[1]

        if status:
            success, error_msg = self.brain.block_user(other_user_username)
            if not success:
                error_dialog = ErrorDialog()
                error_dialog.set_error_message(error_msg)
                error_dialog.exec()
                return
        else:
            success, error_msg = self.brain.unblock_user(other_user_username)
            if not success:
                error_dialog = ErrorDialog()
                error_dialog.set_error_message(error_msg)
                error_dialog.exec()
                return

        user_is_reachable = self.brain.user_is_reachable(other_user_username)
        user_is_blocked = self.brain.user_is_blocked(other_user_username)

        setting = "ro" if not user_is_reachable or user_is_blocked else "rw"

        self.brain.set_chat_setting(chat_id, domain, setting)

        current_chat_id = self.brain.get_current_chat_id()
        current_chat_domain = self.brain.get_current_chat_domain()
        if current_chat_id == chat_id and current_chat_domain == domain:
            self.brain.chat_selected.emit(current_chat_id, current_chat_domain)

    def __remove_chat_from_list(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        removed_item = self.list_widget.takeItem(row)
        if removed_item: del removed_item

    def __exit_chat(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)

        current_chat_id = self.brain.get_current_chat_id()
        current_chat_domain = self.brain.get_current_chat_domain()
        if current_chat_id == item_data['chat_id'] and current_chat_domain == item_data['domain']:
            self.list_widget.setCurrentRow(-1)

        current_user_username = self.brain.get_current_user_username()
        self.brain.remove_users_from_chat(item_data['chat_id'], item_data['domain'], [current_user_username])
        self.search(self.search_bar.text())
        # IMPLEMENT REQUESTS TO SERVER

    def __delete_chat(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)

        current_chat_id = self.brain.get_current_chat_id()
        current_chat_domain = self.brain.get_current_chat_domain()
        if current_chat_id == item_data['chat_id'] and current_chat_domain == item_data['domain']:
            self.list_widget.setCurrentRow(-1)

        self.__remove_chat_from_list(item)
        self.brain.remove_chat_by_id_and_domain(item_data['chat_id'], item_data['domain'])
        self.search(self.search_bar.text())
        # IMPLEMENT REQUESTS TO SERVER

    def __mark_read(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        chat_id = item_data['chat_id']
        domain = item_data['domain']

        self.brain.set_current_user_last_seen_time(chat_id, domain)
        self.set_unread_icon(item, chat_id, domain, False)

    def remove_domain_chats(self, domain: str):
        for row in reversed(range(self.list_widget.count())):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if domain == item_data['domain']:
                is_selected = item.isSelected()
                if is_selected:
                    self.list_widget.setCurrentRow(-1)
                removed_item = self.list_widget.takeItem(row)
                if removed_item: del removed_item

class ChatsAndUsersPanel(QWidget):
    def __init__(self, app: QApplication, brain: Brain, login_dialog: LogInDialog, add_users_dialog: AddUsersDialog):
        super().__init__()

        chat_list = ChatList(brain, add_users_dialog)

        interactions = LeftPanelInteractions(app, brain, login_dialog)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(chat_list)
        layout.addWidget(interactions)
        self.setLayout(layout)

        self.setFixedWidth(LEFT_PANEL_WIDTH)