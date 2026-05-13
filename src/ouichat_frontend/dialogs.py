from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QWidget, QFormLayout, QCheckBox, QSizePolicy, QListWidget,
    QHBoxLayout, QListWidgetItem, QTextEdit, QAbstractItemView, QGridLayout
)

from PyQt6.QtCore import Qt, QSize

from ouichat_frontend.brain import Brain

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32

LIST_WIDGET_FIXED_WIDTH = 300

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
                "blacklist": ["fifo3"]
            }

            self.brain.add_user(user_data) # also sets it as the current user

            self.accept()

        else:
            self.error_message.setText(ret[1])

class CustomListWidgetItem(QListWidgetItem):
    def __init__(self):
        super().__init__()

    def __lt__(self, other: QListWidgetItem):
        self_is_checked = self.checkState() == Qt.CheckState.Checked
        other_is_checked = other.checkState() == Qt.CheckState.Checked

        if self_is_checked != other_is_checked:
            return self_is_checked

        return self.text().lower() < other.text().lower()

def create_manage_users_item(username: str, icon_path: str):
    icon = QIcon(icon_path)
    item = CustomListWidgetItem()
    item.setText(username)
    item.setIcon(icon)
    item_data = {
        "username": username,
    }
    item.setData(Qt.ItemDataRole.UserRole, item_data)
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
    item.setCheckState(Qt.CheckState.Unchecked)
    return item

class CustomListWidget(QListWidget):
    def __init__(self):
        super().__init__()

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            super().mouseReleaseEvent(event)
            return

        old_state = item.checkState()
        super().mouseReleaseEvent(event)
        if old_state == item.checkState():
            if old_state == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)

class UsersDialog(QDialog):
    def __init__(self, brain: Brain, left_desc_label_text: str, execute_button_text: str):
        super().__init__()

        self.brain = brain
        self.chat_id = None
        self.domain = None

        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(5, 5, 5, 5)
        dialog_layout.setSpacing(5)
        self.setLayout(dialog_layout)

        grid_container = QWidget()
        grid_container_layout = QGridLayout()
        grid_container_layout.setContentsMargins(0, 0, 0, 0)
        grid_container_layout.setSpacing(5)
        grid_container.setLayout(grid_container_layout)

        """ LEFT SIDE """
        top_container_left = QWidget()
        top_container_left_layout = QHBoxLayout()
        top_container_left_layout.setContentsMargins(0, 0, 0, 0)
        top_container_left_layout.setSpacing(5)
        top_container_left.setLayout(top_container_left_layout)

        left_desc_label = QLabel()
        left_desc_label.setText(f"{left_desc_label_text}:")
        left_desc_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.search_bar_left = QLineEdit()
        self.search_bar_left.setPlaceholderText("Search user...")
        self.search_bar_left.setFixedSize(200, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar_left.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar_left.textChanged.connect(self.search_left)

        top_container_left_layout.addWidget(left_desc_label, alignment=Qt.AlignmentFlag.AlignLeft)
        top_container_left_layout.addWidget(self.search_bar_left, alignment=Qt.AlignmentFlag.AlignRight)

        self.list_widget_left = CustomListWidget()
        self.list_widget_left.setIconSize(QSize(32, 32))
        self.list_widget_left.setMinimumHeight(200)
        self.list_widget_left.setFixedWidth(LIST_WIDGET_FIXED_WIDTH)
        self.list_widget_left.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget_left.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget_left.itemChanged.connect(self.handle_item_toggled)

        """ RIGHT SIDE """
        top_container_right = QWidget()
        top_container_right_layout = QHBoxLayout()
        top_container_right_layout.setContentsMargins(0, 0, 0, 0)
        top_container_right_layout.setSpacing(5)
        top_container_right.setLayout(top_container_right_layout)

        selected_users_label = QLabel()
        selected_users_label.setText("Selected Users:")
        selected_users_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.search_bar_right = QLineEdit()
        self.search_bar_right.setPlaceholderText("Search user...")
        self.search_bar_right.setFixedSize(200, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar_right.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar_right.textChanged.connect(self.search_right)

        top_container_right_layout.addWidget(selected_users_label, alignment=Qt.AlignmentFlag.AlignLeft)
        top_container_right_layout.addWidget(self.search_bar_right, alignment=Qt.AlignmentFlag.AlignRight)

        self.list_widget_right = CustomListWidget()
        self.list_widget_right.setIconSize(QSize(32, 32))
        self.list_widget_right.setMinimumHeight(200)
        self.list_widget_right.setFixedWidth(LIST_WIDGET_FIXED_WIDTH)
        self.list_widget_right.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget_right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget_right.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        grid_container_layout.addWidget(top_container_left, 0, 0)
        grid_container_layout.addWidget(self.list_widget_left, 1, 0)
        grid_container_layout.addWidget(top_container_right, 0, 1)
        grid_container_layout.addWidget(self.list_widget_right, 1, 1)

        grid_container_layout.setColumnStretch(0, 1)
        grid_container_layout.setColumnStretch(1, 1)

        button_container = QWidget()
        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(20)
        button_container.setLayout(button_container_layout)

        add_members_button = QPushButton()
        add_members_button.setText(f"{execute_button_text}")
        add_members_button.setFixedSize(125, 25)
        add_members_button.clicked.connect(self.perform_operation)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.setFixedSize(125, 25)
        cancel_button.clicked.connect(self.reject)

        button_container_layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignRight)
        button_container_layout.addWidget(add_members_button, alignment=Qt.AlignmentFlag.AlignLeft)

        dialog_layout.addWidget(grid_container)
        dialog_layout.addWidget(button_container)

        self.adjustSize()
        self.setFixedWidth(self.width())

    def search_left(self, text):
        for row in range(self.list_widget_left.count()):
            item = self.list_widget_left.item(row)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def search_right(self, text):
        for row in range(self.list_widget_right.count()):
            item = self.list_widget_right.item(row)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def handle_item_toggled(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data["username"]

        if item.checkState() == Qt.CheckState.Checked:
            right_item = QListWidgetItem()
            right_item.setText(username)
            right_item.setIcon(item.icon())
            right_item_data = {
                "username": username
            }
            right_item.setData(Qt.ItemDataRole.UserRole, right_item_data)
            self.list_widget_right.addItem(right_item)
            self.list_widget_right.sortItems(Qt.SortOrder.AscendingOrder)

        else:
            for row in range(self.list_widget_right.count()):
                right_item = self.list_widget_right.item(row)
                right_item_data = right_item.data(Qt.ItemDataRole.UserRole)
                right_username = right_item_data["username"]
                if right_username == username:
                    self.list_widget_right.takeItem(row)
                    return

    def clear_list(self):
        self.list_widget_left.clear()
        self.list_widget_right.clear()

    def reset_chat_details(self):
        self.chat_id = None
        self.domain = None

    def set_chat_details(self, chat_id: str, domain: str):
        self.chat_id = chat_id
        self.domain = domain

    def get_chat_details(self):
        return {
            "chat_id": self.chat_id,
            "domain": self.domain
        }

    def perform_operation(self):
        pass

class AddUsersDialog(UsersDialog):
    def __init__(self, brain: Brain):
        super().__init__(brain, "Add Users", "Add Users")

    def perform_operation(self):
        users_to_be_added = []
        for row in range(self.list_widget_right.count()):
            item = self.list_widget_right.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            username = item_data["username"]
            users_to_be_added.append(username)

        if self.chat_id is not None and self.domain is not None:
            ret = self.brain.add_users_to_chat(self.chat_id, self.domain, users_to_be_added)
            if not ret[0]:
                error_message = ret[1]
                # ERROR WINDOW POPUP
                return

        else:
            ret = self.brain.create_chatroom(users_to_be_added)
            if not ret[0]:
                error_message = ret[1]
                # ERROR WINDOW POPUP
                return
            self.chat_id = ret[1]
            self.domain = ret[2]

        self.accept()

    def load_users(self):
        self.clear_list()

        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        available_users = self.brain.get_domain_users(current_user_domain)
        if available_users is None: return False

        users_list = []
        if self.chat_id is not None and self.domain is not None:
            ret_list = self.brain.get_chat_users(self.chat_id, self.domain)
            if ret_list: users_list = ret_list

        users_list = [user["username"] for user in users_list] if users_list else []

        for user in available_users:
            username = user['username']
            if self.brain.user_is_blocked(username): continue
            if username in users_list: continue
            if username == current_user_username: continue

            user_icon = self.brain.get_user_icon_path(username, current_user_domain)
            item = create_manage_users_item(username, user_icon)
            self.list_widget_left.addItem(item)

        return True

class RemoveUsersDialog(UsersDialog):
    def __init__(self, brain: Brain):
        super().__init__(brain, "Remove Users", "Remove Users")

    def perform_operation(self):
        users_to_be_removed = []

        for row in range(self.list_widget_right.count()):
            item = self.list_widget_right.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            username = item_data["username"]
            users_to_be_removed.append(username)

        ret = self.brain.remove_users_from_chat(self.chat_id, self.domain, users_to_be_removed)
        if not ret[0]:
            error_message = ret[1]
            # ERROR WINDOW POPUP
            return

        self.accept()

    def load_users(self):
        self.clear_list()

        ret_list = self.brain.get_chat_users(self.chat_id, self.domain)
        if not ret_list: return False

        current_user_username = self.brain.get_current_user_username()
        chat_creator = self.brain.get_chat_creator(self.chat_id, self.domain)
        show_admins = current_user_username == chat_creator
        users_list = [user['username'] for user in ret_list]

        for username in users_list:
            user_is_admin = self.brain.user_is_admin(self.chat_id, self.domain, username)
            if user_is_admin and not show_admins: continue
            if username == current_user_username: continue

            user_icon = self.brain.get_user_icon_path(username, self.domain)
            item = create_manage_users_item(username, user_icon)
            self.list_widget_left.addItem(item)

        return True

class TextEditDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.edited_field = None
        self.chat_id = None
        self.domain = None

        self.setWindowTitle("Edit Chat Details")

        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(5, 5, 5, 5)
        dialog_layout.setSpacing(5)
        self.setLayout(dialog_layout)

        self.description_label = QLabel()
        self.description_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.text_edit = QTextEdit()
        self.text_edit.setMinimumSize(QSize(200, 50))

        button_container = QWidget()
        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(5)
        button_container.setLayout(button_container_layout)

        apply_button = QPushButton()
        apply_button.setText("Apply")
        apply_button.setFixedSize(125, 25)
        apply_button.clicked.connect(self.apply)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.setFixedSize(125, 25)
        cancel_button.clicked.connect(self.reject)

        button_container_layout.addWidget(cancel_button)
        button_container_layout.addWidget(apply_button)

        dialog_layout.addWidget(self.description_label)
        dialog_layout.addWidget(self.text_edit)
        dialog_layout.addWidget(button_container)

    def apply(self):
        # PROCESS REQUEST USING BRAIN
        text = self.text_edit.toPlainText()
        if self.edited_field == "name":
            self.brain.set_chat_display_name(self.chat_id, self.domain, text)

        elif self.edited_field == "description":
            self.brain.set_chat_description(self.chat_id, self.domain, text)

        self.accept()

    def set_chat_details(self, chat_id: str, domain: str):
        self.chat_id = chat_id
        self.domain = domain

    def set_edited_field(self, edited_field: str):
        self.edited_field = edited_field

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)

    def set_text_hint(self, text: str):
        self.text_edit.setPlaceholderText(text)

    def set_label_text(self, text: str):
        self.description_label.setText(text)