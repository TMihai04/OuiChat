from typing import Callable, Coroutine, Any

from PyQt6.QtGui import QIcon, QTextOption
from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QWidget, QFormLayout, QCheckBox, QSizePolicy, QListWidget,
    QHBoxLayout, QListWidgetItem, QTextEdit, QAbstractItemView, QGridLayout
)

from PyQt6.QtCore import Qt, QSize, QThread, QEventLoop, pyqtSignal

import aiohttp
import asyncio

from brain import Brain
from socket_manager import handle_error, get_resp_dict, MAX_REQUESTS, REQUEST_TIMEOUT

MAX_USERNAME_LENGTH = 16
MAX_PASSWORD_LENGTH = 32

LIST_WIDGET_FIXED_WIDTH = 300

async def register_request(domain: str, username: str, password: str):
    register_json = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/register", data=register_json) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(False, 'Cannot establish a connection with the server.')

async def login_request(domain: str, username: str, password: str):
    login_json = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/login", data=login_json) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 'Cannot establish a connection with the server.')

class CredentialsRequestWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, username: str, password: str, request: Callable[[str, str, str], Coroutine[Any, Any, dict]]):
        super().__init__()

        self.domain = domain
        self.username = username
        self.password = password
        self.request = request

    def run(self):
        resp = asyncio.run(self.request(self.domain, self.username, self.password))
        self.finished.emit(resp)

async def get_current_user_profile_request(domain: str, access_token: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"http://{domain}/users/me", headers=headers) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 'Cannot establish a connection with the server.')

class CurrentUserProfileWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str):
        super().__init__()

        self.domain = domain
        self.access_token = access_token

    def run(self):
        resp = asyncio.run(get_current_user_profile_request(domain=self.domain, access_token=self.access_token))
        self.finished.emit(resp)

class LogInDialog(QDialog):
    """
    TO DO:
        - when clicking enter in a field it selects the next field
        - when clicking enter in the last field it hits the login button
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.reg_worker = None
        self.login_worker = None
        self.worker_response = None

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

        self.log_in_button = QPushButton("Login")
        self.log_in_button.setFixedSize(125, 25)
        self.log_in_button.setAutoDefault(False)
        self.log_in_button.clicked.connect(self.__validate_credentials)
        self.log_in_button.setCursor(Qt.CursorShape.PointingHandCursor)

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

        register = self.register_checkbox.isChecked()

        if register:
            self.reg_worker = CredentialsRequestWorker(domain, username, password, register_request)

            register_loop = QEventLoop()
            self.worker_response = dict()

            def catch_response(resp):
                self.worker_response = resp
                register_loop.quit()

            self.reg_worker.finished.connect(catch_response)
            self.reg_worker.start()
            register_loop.exec()

            self.reg_worker.deleteLater()
            is_error = self.worker_response.get('is_error')
            if is_error:
                self.set_error_message(self.worker_response.get('field'))
                self.__resize_text_box()
                self.set_interactions_state(True)
                return
            else:
                self.set_error_message('')

        self.login_worker = CredentialsRequestWorker(domain, username, password, login_request)

        login_loop = QEventLoop()
        self.worker_response = dict()

        def catch_response(resp):
            self.worker_response = resp
            login_loop.quit()

        self.login_worker.finished.connect(catch_response)
        self.login_worker.start()
        login_loop.exec()

        self.login_worker.deleteLater()
        is_error = self.worker_response.get('is_error')

        if is_error:
            self.set_error_message(self.worker_response.get('field'))
            self.__resize_text_box()
            self.set_interactions_state(True)
            return

        access_token = self.worker_response.get('field').get('access_token', "")
        refresh_token = self.worker_response.get('field').get('refresh_token', "")

        self.current_user_profile_worker = CurrentUserProfileWorker(domain, access_token)

        current_user_profile_loop = QEventLoop()
        self.worker_response = dict()

        def catch_response(resp):
            self.worker_response = resp
            current_user_profile_loop.quit()

        self.current_user_profile_worker.finished.connect(catch_response)
        self.current_user_profile_worker.start()
        current_user_profile_loop.exec()

        self.current_user_profile_worker.deleteLater()
        is_error = self.worker_response.get('is_error')

        if is_error:
            self.set_error_message(self.worker_response.get('field'))
            self.__resize_text_box()
            self.set_interactions_state(True)
            return

        db_username = self.worker_response.get('field').get('item').get('username', "-")
        blacklist = self.worker_response.get('field').get('item').get('preferences', dict()).get('blacklist', [])

        self.username_line_edit.clear()
        self.password_line_edit.clear()
        self.domain_line_edit.clear()

        user_data = {
            "username": db_username,
            "domain": domain,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "blacklist": blacklist,
        }
        self.brain.add_user(user_data) # also sets it as the current user

        self.set_interactions_state(True)
        self.accept()

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

        self.list_widget_left.sortItems(Qt.SortOrder.AscendingOrder)
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

        self.list_widget_left.sortItems(Qt.SortOrder.AscendingOrder)
        return True

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

        apply_button = QPushButton()
        apply_button.setText("Apply")
        apply_button.setFixedSize(125, 25)
        apply_button.clicked.connect(self.apply)
        apply_button.setCursor(Qt.CursorShape.PointingHandCursor)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.setFixedSize(125, 25)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

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

class UserDetailsEditDialog(QDialog):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

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

        apply_button = QPushButton()
        apply_button.setText("Apply")
        apply_button.setFixedSize(125, 25)
        apply_button.clicked.connect(self.apply)
        apply_button.setCursor(Qt.CursorShape.PointingHandCursor)

        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.setFixedSize(125, 25)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_container_layout.addWidget(cancel_button)
        button_container_layout.addWidget(apply_button)

        dialog_layout.addWidget(self.description_label)
        dialog_layout.addWidget(self.text_edit)
        dialog_layout.addWidget(button_container)

    def set_text(self, text: str):
        self.text_edit.setPlainText(text)

    def apply(self):
        # PROCESS REQUEST USING BRAIN
        text = self.text_edit.toPlainText()
        self.brain.set_current_user_description(text)

        self.accept()