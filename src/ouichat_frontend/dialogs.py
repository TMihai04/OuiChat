from PyQt6.QtGui import QIcon, QTextOption
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QWidget, QFormLayout, QCheckBox, QSizePolicy, QListWidget,
    QHBoxLayout, QListWidgetItem, QTextEdit, QAbstractItemView, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent

import re

from brain import Brain

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32

LIST_WIDGET_FIXED_WIDTH = 300

class LogInDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.reg_worker = None
        self.login_worker = None

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
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # DEBUG THIS
        self.toggle_password_action = self.password_line_edit.addAction(
            QIcon("./Icons/opened_eye_icon.png"),
            QLineEdit.ActionPosition.TrailingPosition
        )
        # noinspection PyUnresolvedReferences
        self.toggle_password_action.triggered.connect(self.__toggle_password_visibility)

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

        self.log_in_button = QPushButton("Login")
        self.log_in_button.setFixedSize(125, 25)
        self.log_in_button.setAutoDefault(False)
        self.log_in_button.clicked.connect(self.__validate_credentials)
        self.log_in_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.domain_line_edit.returnPressed.connect(self.username_line_edit.setFocus)
        self.username_line_edit.returnPressed.connect(self.password_line_edit.setFocus)
        self.password_line_edit.returnPressed.connect(self.log_in_button.click)
        self.domain_line_edit.installEventFilter(self)
        self.username_line_edit.installEventFilter(self)
        self.password_line_edit.installEventFilter(self)

        self.error_message = QTextEdit()
        self.error_message.setPlainText("")
        self.error_message.setReadOnly(True)
        self.error_message.setFrameShape(QTextEdit.Shape.NoFrame)
        self.error_message.setStyleSheet("background: transparent; color: red;")
        self.error_message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.error_message.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.error_message.document().setDocumentMargin(0)
        self.error_message.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.error_message.setHidden(True)

        layout = QVBoxLayout()
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(form_widget)
        layout.addWidget(self.register_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.log_in_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.setLayout(layout)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                if source == self.domain_line_edit:
                    self.username_line_edit.setFocus()
                    return True
                elif source == self.username_line_edit:
                    self.password_line_edit.setFocus()
                    return True
                elif source == self.password_line_edit:
                    self.domain_line_edit.setFocus()
                    return True

            elif event.key() == Qt.Key.Key_Up:
                if source == self.password_line_edit:
                    self.username_line_edit.setFocus()
                    return True
                elif source == self.username_line_edit:
                    self.domain_line_edit.setFocus()
                    return True
                elif source == self.domain_line_edit:
                    self.password_line_edit.setFocus()
                    return True

        return super().eventFilter(source, event)

    def __set_password_visibility(self, visible: bool):
        if visible:
            self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_action.setIcon(QIcon("./Icons/closed_eye_icon.png"))
        else:
            self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_action.setIcon(QIcon("./Icons/opened_eye_icon.png"))

    def __toggle_password_visibility(self):
        if self.password_line_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_action.setIcon(QIcon("./Icons/closed_eye_icon.png"))
        else:
            self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_action.setIcon(QIcon("./Icons/opened_eye_icon.png"))

    def __resize_text_box(self):
        text_height = int(self.error_message.document().size().height()) + 2
        box_height = self.error_message.height()
        if text_height != box_height:
            self.error_message.setFixedHeight(text_height)
            self.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()

    def __validate_credentials(self):
        self.set_interactions_state(False)

        username = self.username_line_edit.text()
        password = self.password_line_edit.text()
        domain = self.domain_line_edit.text()

        if not domain or domain == "":
            self.set_error_message("Domain must not be empty")
            self.domain_line_edit.setFocus()
            self.set_interactions_state(True)
            return

        if not username or username == "":
            self.set_error_message('Username must not be empty')
            self.username_line_edit.setFocus()
            self.set_interactions_state(True)
            return

        if not password or password == "":
            self.set_error_message('Password must not be empty')
            self.password_line_edit.setFocus()
            self.set_interactions_state(True)
            return

        register = self.register_checkbox.isChecked()

        if register:

            if len(username) < 4 or len(username) > 64:
                self.set_error_message('Username must be between 4 and 64 characters long (inclusive)')
                self.username_line_edit.setFocus()
                self.set_interactions_state(True)
                return

            reg_exp = r"^[a-zA-Z\-_0-9]{4,64}$"
            if re.search(reg_exp, username) is None:
                self.set_error_message('Username contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), hyphens (-), and underscores (_)')
                self.username_line_edit.setFocus()
                self.set_interactions_state(True)
                return

            if len(password) < 8:
                self.set_error_message("Password must be at least 8 characters long")
                self.password_line_edit.setFocus()
                self.set_interactions_state(True)
                return

            alphabet_dict = {
                "lower": 0,
                "upper": 0,
                "digit": 0,
                "special": 0,
            }
            specials = [".", "_", "-", "!", "/", "+", "=", "*"]

            for char in password:
                if re.match(r"[a-z]", char):
                    alphabet_dict["lower"] += 1
                elif re.match(r"[A-Z]", char):
                    alphabet_dict["upper"] += 1
                elif re.match(r"[0-9]", char):
                    alphabet_dict["digit"] += 1
                elif char in specials:
                    alphabet_dict["special"] += 1
                else:
                    self.set_error_message("Password contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), and special characters (._-!/+=*)")
                    self.password_line_edit.setFocus()
                    self.set_interactions_state(True)
                    return

            for key, item in alphabet_dict.items():
                if item == 0:
                    self.set_error_message("Password must contain at least one of: lowercase letter, uppercase letter, digit, special character")
                    self.password_line_edit.setFocus()
                    self.set_interactions_state(True)
                    return

            success, error_msg = self.brain.register_login_user(domain, username, password, False)
            if not success:
                self.set_error_message(error_msg)
                self.set_interactions_state(True)
                return
            else:
                self.set_error_message('')

        logged_users = self.brain.get_logged_users()
        for user in logged_users:
            if user['domain'] == domain and user['username'] == username:
                self.set_error_message('Username already logged in')
                self.set_interactions_state(True)
                return

        success, resp_data = self.brain.register_login_user(domain, username, password, True)
        if not success:
            self.set_error_message(resp_data)
            self.set_interactions_state(True)
            return
        else:
            self.set_error_message('')

        access_token = resp_data.get('access_token', "")
        refresh_token = resp_data.get('refresh_token', "")

        success, resp_data = self.brain.get_current_user_profile(domain, access_token)
        if not success:
            self.set_error_message(resp_data)
            self.set_interactions_state(True)
            return
        else:
            self.set_error_message('')

        db_username = resp_data.get('item', dict()).get('username', "-")
        blacklist = resp_data.get('item', dict()).get('preferences', dict()).get('blacklist', [])

        user_data = {
            "username": db_username,
            "domain": domain,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "blacklist": blacklist,
        }
        success, error_msg = self.brain.add_user(user_data) # also sets it as the current user
        if not success:
            self.set_error_message(error_msg)
            self.set_interactions_state(True)
            return

        self.accept()

    def exec(self):
        self.set_interactions_state(True)
        self.__set_password_visibility(False)
        self.domain_line_edit.setFocus()
        self.set_error_message('')
        self.username_line_edit.clear()
        self.password_line_edit.clear()
        self.domain_line_edit.clear()
        return super().exec()

    def set_interactions_state(self, state: bool):
        self.domain_line_edit.setEnabled(state)
        self.username_line_edit.setEnabled(state)
        self.password_line_edit.setEnabled(state)
        self.log_in_button.setEnabled(state)

    def set_error_message(self, message):
        self.error_message.setPlainText(message)
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if message == '':
            self.error_message.setHidden(True)
        else:
            self.error_message.setHidden(False)
        self.__resize_text_box()

class CustomListWidgetItem(QListWidgetItem):
    def __init__(self):
        super().__init__()

    def __lt__(self, other: QListWidgetItem):
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

class CustomMouseListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

class CustomListWidget(CustomMouseListWidget):
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

        self.list_widget_right = CustomMouseListWidget()
        self.list_widget_right.setIconSize(QSize(32, 32))
        self.list_widget_right.setMinimumHeight(200)
        self.list_widget_right.setFixedWidth(LIST_WIDGET_FIXED_WIDTH)
        self.list_widget_right.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget_right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget_right.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget_right.itemClicked.connect(self.right_item_clicked)

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

        perform_operation_button = QPushButton()
        perform_operation_button.setText(f"{execute_button_text}")
        perform_operation_button.setFixedSize(125, 25)
        perform_operation_button.clicked.connect(self.perform_operation)
        perform_operation_button.setCursor(Qt.CursorShape.PointingHandCursor)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.setFixedSize(125, 25)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_container_layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignRight)
        button_container_layout.addWidget(perform_operation_button, alignment=Qt.AlignmentFlag.AlignLeft)

        dialog_layout.addWidget(grid_container)
        dialog_layout.addWidget(button_container)

        self.adjustSize()
        self.setFixedWidth(self.width())

    def right_item_clicked(self, item: QListWidgetItem):
        right_data = item.data(Qt.ItemDataRole.UserRole)
        right_username = right_data['username']
        for row in range(self.list_widget_left.count()):
            left_item = self.list_widget_left.item(row)
            left_data = left_item.data(Qt.ItemDataRole.UserRole)
            left_username = left_data['username']
            if  right_username == left_username:
                left_item.setCheckState(Qt.CheckState.Unchecked)
                return

    def search_left(self, text):
        search_text = text.lower()
        for row in range(self.list_widget_left.count()):
            item = self.list_widget_left.item(row)
            if search_text == "" or search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def search_right(self, text):
        search_text = text.lower()
        for row in range(self.list_widget_right.count()):
            item = self.list_widget_right.item(row)
            if search_text == "" or search_text in item.text().lower():
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
        self.list_widget_left.blockSignals(True)
        self.list_widget_left.clear()
        self.list_widget_left.blockSignals(False)
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
            success, resp_data = self.brain.add_users_to_chat(self.chat_id, self.domain, users_to_be_added)
            if not success:
                error_dialog = ErrorDialog()
                error_dialog.set_error_message(resp_data)
                error_dialog.exec()
                return

        else:
            success, resp_data = self.brain.create_chatroom(users_to_be_added)
            if not success:
                error_dialog = ErrorDialog()
                error_dialog.set_error_message(resp_data)
                error_dialog.exec()
                return

            self.chat_id = resp_data[0]
            self.domain = resp_data[1]

        self.accept()

    def load_users(self):
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

        self.list_widget_left.sortItems(Qt.SortOrder.AscendingOrder)
        return True

    def exec(self):
        self.clear_list()
        ret = self.load_users()
        if not ret:
            error_dialog = ErrorDialog()
            error_dialog.set_error_message("Could not load domain members!")
            error_dialog.exec()
            return QDialog.DialogCode.Rejected
        return super().exec()

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

        success, resp_data = self.brain.remove_users_from_chat(self.chat_id, self.domain, users_to_be_removed)
        if not success:
            error_dialog = ErrorDialog()
            error_dialog.set_error_message(resp_data)
            error_dialog.exec()
            return

        self.accept()

    def load_users(self):
        ret_list = self.brain.get_chat_users(self.chat_id, self.domain)
        if not ret_list: return False

        current_user_username = self.brain.get_current_user_username()
        chat_creators = self.brain.get_chat_creators(self.chat_id, self.domain)
        show_admins = current_user_username in chat_creators
        users_list = [user['username'] for user in ret_list]

        for username in users_list:
            user_is_admin = self.brain.user_is_admin(self.chat_id, self.domain, username)
            if user_is_admin and not show_admins: continue
            if username == current_user_username: continue

            user_icon = self.brain.get_user_icon_path(username, self.domain)
            item = create_manage_users_item(username, user_icon)
            self.list_widget_left.addItem(item)

        self.list_widget_left.sortItems(Qt.SortOrder.AscendingOrder)
        return True

    def exec(self):
        self.clear_list()
        ret = self.load_users()
        if not ret:
            error_dialog = ErrorDialog()
            error_dialog.set_error_message("Could not load chat members!")
            error_dialog.exec()
            return QDialog.DialogCode.Rejected
        return super().exec()

class ChatDetailsEditDialog(QDialog):
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

        self.apply_button = QPushButton()
        self.apply_button.setText("Apply")
        self.apply_button.setFixedSize(125, 25)
        self.apply_button.clicked.connect(self.apply)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cancel_button = QPushButton()
        self.cancel_button.setText("Cancel")
        self.cancel_button.setFixedSize(125, 25)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_container_layout.addWidget(self.cancel_button)
        button_container_layout.addWidget(self.apply_button)

        self.error_message = QTextEdit()
        self.error_message.setPlainText("")
        self.error_message.setReadOnly(True)
        self.error_message.setFrameShape(QTextEdit.Shape.NoFrame)
        self.error_message.setStyleSheet("background: transparent; color: red;")
        self.error_message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.error_message.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.error_message.document().setDocumentMargin(0)
        self.error_message.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.error_message.setHidden(True)

        dialog_layout.addWidget(self.description_label)
        dialog_layout.addWidget(self.text_edit)
        dialog_layout.addWidget(button_container)
        dialog_layout.addWidget(self.error_message)
        dialog_layout.addStretch()

    def set_error_message(self, message):
        self.error_message.setPlainText(message)
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if message == '':
            self.error_message.setHidden(True)
        else:
            self.error_message.setHidden(False)
        self.__resize_text_box()

    def __resize_text_box(self):
        text_height = int(self.error_message.document().size().height()) + 2
        box_height = self.error_message.height()
        if text_height != box_height:
            self.error_message.setFixedHeight(text_height)
            self.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()

    def set_interactions_state(self, state: bool):
        self.text_edit.setEnabled(state)
        self.apply_button.setEnabled(state)
        self.cancel_button.setEnabled(state)

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

    def exec(self):
        self.set_interactions_state(True)
        self.set_error_message('')
        return super().exec()

class UserDetailsEditDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.description_worker = None

        self.setWindowTitle("Edit User Description")

        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(5, 5, 5, 5)
        dialog_layout.setSpacing(5)
        self.setLayout(dialog_layout)

        self.description_label = QLabel()
        self.description_label.setText("Description:")
        self.description_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.text_edit = QTextEdit()
        self.text_edit.setMinimumSize(QSize(200, 50))
        self.text_edit.setPlaceholderText("Type your description...")

        button_container = QWidget()
        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(5)
        button_container.setLayout(button_container_layout)

        self.apply_button = QPushButton()
        self.apply_button.setText("Apply")
        self.apply_button.setFixedSize(125, 25)
        self.apply_button.clicked.connect(self.apply)
        self.apply_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cancel_button = QPushButton()
        self.cancel_button.setText("Cancel")
        self.cancel_button.setFixedSize(125, 25)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_container_layout.addWidget(self.cancel_button)
        button_container_layout.addWidget(self.apply_button)

        self.error_message = QTextEdit()
        self.error_message.setPlainText("")
        self.error_message.setReadOnly(True)
        self.error_message.setFrameShape(QTextEdit.Shape.NoFrame)
        self.error_message.setStyleSheet("background: transparent; color: red;")
        self.error_message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.error_message.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.error_message.document().setDocumentMargin(0)
        self.error_message.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.error_message.setHidden(True)

        dialog_layout.addWidget(self.description_label)
        dialog_layout.addWidget(self.text_edit)
        dialog_layout.addWidget(button_container)
        dialog_layout.addWidget(self.error_message)
        dialog_layout.addStretch()

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)
        self.set_error_message('')

    def set_error_message(self, message):
        self.error_message.setPlainText(message)
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if message == '':
            self.error_message.setHidden(True)
        else:
            self.error_message.setHidden(False)
        self.__resize_text_box()

    def __resize_text_box(self):
        text_height = int(self.error_message.document().size().height()) + 2
        box_height = self.error_message.height()
        if text_height != box_height:
            self.error_message.setFixedHeight(text_height)
            self.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()

    def set_interactions_state(self, state: bool):
        self.text_edit.setEnabled(state)
        self.apply_button.setEnabled(state)
        self.cancel_button.setEnabled(state)

    def apply(self):
        self.set_interactions_state(False)

        text = self.text_edit.toPlainText()

        if text == "" or text is None:
            self.set_error_message("Description must not be empty")
            self.set_interactions_state(True)
            return

        if len(text) > 128:
            self.set_error_message("Description must be less than 128 characters")
            self.set_interactions_state(True)
            return

        success, error_msg = self.brain.set_current_user_description(text)
        if not success:
            self.set_error_message(error_msg)
            self.set_interactions_state(True)
            return

        self.accept()

    def exec(self):
        self.set_interactions_state(True)
        self.set_error_message('')
        return super().exec()

class RefreshLoginDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        description_label = QLabel()
        description_label.setText("Session timed out. Insert password to renew the session.")
        description_label.setFixedHeight(25)

        password_label = QLabel()
        password_label.setText("Password:")
        password_label.setFixedSize(60, 25)

        self.password_line_edit = QLineEdit()
        self.password_line_edit.setMaxLength(MAX_PASSWORD_LENGTH)
        self.password_line_edit.setPlaceholderText("Password...")
        self.password_line_edit.setMinimumSize(225, 25)
        self.password_line_edit.setMaximumSize(450, 25)
        self.password_line_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(5)

        form_layout.addRow(password_label, self.password_line_edit)

        form_widget.setLayout(form_layout)

        button_container = QWidget()
        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(5)
        button_container.setLayout(button_container_layout)

        self.log_out_button = QPushButton("Log Out")
        self.log_out_button.setFixedSize(100, 25)
        self.log_out_button.setAutoDefault(False)
        self.log_out_button.clicked.connect(self.__logout)
        self.log_out_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.log_in_button = QPushButton("Renew Session")
        self.log_in_button.setFixedSize(100, 25)
        self.log_in_button.setAutoDefault(False)
        self.log_in_button.clicked.connect(self.__validate_credentials)
        self.log_in_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.password_line_edit.returnPressed.connect(self.log_in_button.click)

        button_container_layout.addWidget(self.log_out_button)
        button_container_layout.addWidget(self.log_in_button)

        self.error_message = QTextEdit()
        self.error_message.setPlainText("")
        self.error_message.setReadOnly(True)
        self.error_message.setFrameShape(QTextEdit.Shape.NoFrame)
        self.error_message.setStyleSheet("background: transparent; color: red;")
        self.error_message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.error_message.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.error_message.document().setDocumentMargin(0)
        self.error_message.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.error_message.setHidden(True)

        layout = QVBoxLayout()
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(form_widget)
        layout.addWidget(button_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.setLayout(layout)

    def __resize_text_box(self):
        text_height = int(self.error_message.document().size().height()) + 2
        box_height = self.error_message.height()
        if text_height != box_height:
            self.error_message.setFixedHeight(text_height)
            self.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()

    def set_interactions_state(self, state: bool):
        self.password_line_edit.setEnabled(state)
        self.log_out_button.setEnabled(state)
        self.log_in_button.setEnabled(state)

    def set_error_message(self, message):
        self.error_message.setPlainText(message)
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if message == '':
            self.error_message.setHidden(True)
        else:
            self.error_message.setHidden(False)
        self.__resize_text_box()

    def __validate_credentials(self):
        self.set_interactions_state(False)

        password = self.password_line_edit.text()

        success, resp_data = self.brain.register_login_user(None, None, password, True)
        if not success:
            self.set_error_message(resp_data)
            self.set_interactions_state(True)
            return
        else:
            self.set_error_message('')

        access_token = resp_data.get('access_token')
        refresh_token = resp_data.get('refresh_token')

        self.brain.set_current_user_access_token(access_token)
        self.brain.set_current_user_refresh_token(refresh_token)
        self.accept()

    def __logout(self):
        self.reject()
        QTimer.singleShot(0, self.brain.logout_current_user)

    def exec(self):
        self.password_line_edit.clear()
        self.set_interactions_state(True)
        self.set_error_message('')
        return super().exec()

class ErrorDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Error")

        self.error_message = QTextEdit()
        self.error_message.setPlainText("")
        self.error_message.setReadOnly(True)
        self.error_message.setFrameShape(QTextEdit.Shape.NoFrame)
        self.error_message.setStyleSheet("background: transparent;")
        self.error_message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.error_message.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.error_message.document().setDocumentMargin(0)
        self.error_message.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.ok_button = QPushButton("Ok")
        self.ok_button.setFixedSize(125, 25)
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setCursor(Qt.CursorShape.PointingHandCursor)

        dialog_layout = QVBoxLayout()
        dialog_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        dialog_layout.setContentsMargins(10, 10, 10, 10)
        dialog_layout.setSpacing(5)

        dialog_layout.addWidget(self.error_message, alignment=Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addWidget(self.ok_button, alignment=Qt.AlignmentFlag.AlignCenter)
        dialog_layout.addStretch()

        self.setLayout(dialog_layout)

    def set_error_message(self, message):
        self.error_message.setPlainText(message)
        self.error_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__resize_text_box()

    def __resize_text_box(self):
        text_height = int(self.error_message.document().size().height()) + 2
        box_height = self.error_message.height()
        if text_height != box_height:
            self.error_message.setFixedHeight(text_height)
            self.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()