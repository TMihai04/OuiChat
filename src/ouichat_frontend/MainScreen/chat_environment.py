import random

from PyQt6.QtWidgets import (
    QPushButton, QVBoxLayout, QLabel, QStackedLayout, QWidget, QHBoxLayout, QFileDialog,
    QTextEdit, QSizePolicy, QScrollArea, QLineEdit, QListWidget, QAbstractItemView, QListWidgetItem, QMenu
)

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QFontMetrics, QEnterEvent, QTextOption

import time
import os
from PIL import Image

from ouichat_frontend.dialogs import AddUsersDialog, RemoveUsersDialog, ChatDetailsEditDialog
from ouichat_frontend.brain import Brain
from ouichat_frontend.socket_manager import message_args_to_dict

RIGHT_PANE_MIN_WIDTH = 310
DOWNLOAD_WIDGET_WIDTH = 250
MEMBERS_SEARCH_BAR_WIDTH = 200

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
        metrics = QFontMetrics(self.font())
        text_width = metrics.horizontalAdvance(self.full_text)
        return QSize(text_width, super().sizeHint().height())

class DownloadAttachmentBubble(QWidget):
    def __init__(self, brain: Brain, file_id: int, file_path: str):
        super().__init__()

        self.brain = brain

        self.file_id = file_id

        self.setFixedHeight(32)
        self.setFixedWidth(DOWNLOAD_WIDGET_WIDTH)
        self.setObjectName("DownloadFileWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("#DownloadFileWidget { background-color: #2D2D2D; border-radius: 5px; }")

        self.full_file_path = file_path
        self.file_path = os.path.basename(file_path)
        self.file_extension = os.path.splitext(self.file_path)[1].lower()

        widget_layout = QHBoxLayout()
        widget_layout.setContentsMargins(2, 0, 2, 0)
        widget_layout.setSpacing(5)
        self.setLayout(widget_layout)

        file_icon = QLabel()
        file_icon_path = "./Icons/file_uploaded_icon.png"
        file_icon.setPixmap(QPixmap(file_icon_path).scaled(32, 32))

        path_label = ElidedLabel()
        path_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        path_label.setText(self.file_path)

        remove_button = QPushButton()
        remove_button.setFixedSize(32, 32)
        remove_button.setIcon(QIcon("./Icons/download_file_icon.png"))
        remove_button.setIconSize(QSize(32, 32))
        remove_button.clicked.connect(self.download_file)
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)

        widget_layout.addWidget(file_icon)
        widget_layout.addWidget(path_label, stretch=1)
        widget_layout.addWidget(remove_button)

    def download_file(self):
        self.brain.download_files([self.file_id])

class ChatMessage(QWidget):
    """
    TO DO:
        - implement context menu with requests
        - IT WORKS TO SEND MESSAGES WITH ONLY FILES BUT IF YOU EDIT THE TEXT OF THAT MESSAGE
            THE MESSAGE IN THE TEXT DOESN'T SHOW
    """
    def __init__(self, brain: Brain, chat_id: str, domain: str,
                 message_id: str, sender: str, was_edited: bool, is_reply: bool,
                 reply_sender: str | None, reply_snip: str | None, timestamp: str,
                 text: str, uploaded_files: list | None = None):
        super().__init__()

        self.brain = brain

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ChatMessage")
        self.setStyleSheet("#ChatMessage { background-color: transparent; border-radius: 5px; }")

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.chat_id = chat_id
        self.domain = domain
        self.message_id = message_id

        self.sender = sender
        self.sender_icon = QLabel()
        sender_icon_path = self.brain.get_user_icon_path(sender, domain)
        sender_pixmap = QPixmap(sender_icon_path).scaled(32, 32)
        self.sender_icon.setPixmap(sender_pixmap)
        self.reply_sender = reply_sender
        self.reply_sender_icon = None

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

            self.reply_sender_icon = QLabel()
            reply_sender_icon_path = self.brain.get_user_icon_path(reply_sender, domain)
            reply_sender_pixmap = QPixmap(reply_sender_icon_path).scaled(24, 24)
            self.reply_sender_icon.setPixmap(reply_sender_pixmap)

            replied_to_user_label = QLabel()
            replied_to_user_label.setText(f"{reply_sender}:")
            replied_to_user_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            reply_snip_label = ElidedLabel()
            reply_snip_label.setText(reply_snip)

            reply_area_layout.addWidget(replied_to_label)
            reply_area_layout.addWidget(self.reply_sender_icon)
            reply_area_layout.addWidget(replied_to_user_label)
            reply_area_layout.addWidget(reply_snip_label)

        self.message_details = QLabel()
        self.message_details.setFixedHeight(25)
        self.message_details.setText(f"{sender} - {timestamp}{" (Edited)" if was_edited else ""}")
        self.message_details.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.message_text = QTextEdit()
        self.message_text.setPlainText(text)
        self.message_text.setReadOnly(True)
        self.message_text.setFrameShape(QTextEdit.Shape.NoFrame)
        self.message_text.setStyleSheet("background: transparent;")
        self.message_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.message_text.document().setDocumentMargin(0)
        self.message_text.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        if text == "":
            self.message_text.setHidden(True)

        message_area = QWidget()
        message_area_layout = QVBoxLayout()
        message_area_layout.setContentsMargins(0, 0, 0, 0)
        message_area_layout.setSpacing(5)
        message_area.setLayout(message_area_layout)

        if is_reply:
            message_area_layout.addWidget(reply_area)
        message_area_layout.addWidget(self.message_details)
        message_area_layout.addWidget(self.message_text)

        if uploaded_files:
            self.uploaded_files = uploaded_files
            files_container = QWidget()
            files_container_layout = QVBoxLayout()
            files_container_layout.setContentsMargins(0, 0, 0, 0)
            files_container_layout.setSpacing(5)
            files_container.setLayout(files_container_layout)

            for file_data in uploaded_files:
                bubble = DownloadAttachmentBubble(brain, file_data['file_id'], file_data['file_name'])
                files_container_layout.addWidget(bubble)

            message_area_layout.addWidget(files_container)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        self.setLayout(top_layout)

        top_layout.addWidget(self.sender_icon, alignment=Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(message_area, stretch=1)

    def set_sender_icon(self, icon_path: str):
        pixmap = QPixmap(icon_path).scaled(32, 32)
        self.sender_icon.setPixmap(pixmap)

    def set_reply_sender_icon(self, icon_path: str):
        if self.reply_sender is None: return
        pixmap = QPixmap(icon_path).scaled(24, 24)
        self.reply_sender_icon.setPixmap(pixmap)

    def __resize_text_box(self):
        text_height = int(self.message_text.document().size().height()) + 2
        box_height = self.message_text.height()
        if text_height != box_height:
            self.message_text.setFixedHeight(text_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_text_box()

    def edit_text(self, text):
        self.message_text.setPlainText(text)
        self.message_text.setHidden(text == "")

        if not self.was_edited:
            old_message_details = self.message_details.text()
            new_message_details = old_message_details + " (Edited)"
            self.message_details.setText(new_message_details)
            self.was_edited = True

        self.__resize_text_box()
    
    def show_context_menu(self, position):
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()

        user_is_sender = self.sender == current_user_username and self.domain == current_user_domain

        if current_user_domain == self.domain:
            user_is_admin = self.brain.user_is_admin(self.chat_id, self.domain, current_user_username)
        else:
            user_is_admin = False

        menu = QMenu()

        reply = menu.addAction("Reply")
        delete = object()
        edit = object()


        if user_is_admin:
            menu.addSeparator()
            delete = menu.addAction("Delete Message")
        if user_is_sender:
            menu.addSeparator()
            edit = menu.addAction("Edit Message")

        global_pos = self.mapToGlobal(position)
        selected_action = menu.exec(global_pos)

        try:
            self.objectName()
        except RuntimeError:
            return

        parent = self.parentWidget()
        if parent is None or parent.layout() is None or parent.layout().indexOf(self) == -1:
            return

        if selected_action == reply:
            sender_icon_path = self.brain.get_user_icon_path(self.sender, self.domain)
            self.brain.set_reply(True, self.sender, sender_icon_path, self.message_text.toPlainText())

        elif selected_action == edit:
            sender_icon_path = self.brain.get_user_icon_path(self.sender, self.domain)
            self.brain.set_edit(True, self.message_id, self.sender, sender_icon_path, self.message_text.toPlainText())
            self.brain.set_textbox_text.emit(self.message_text.toPlainText())

        elif selected_action == delete:
            message_data = {
                (self.chat_id, self.domain): [self.message_id],
            }
            self.brain.remove_messages.emit(message_data)
    
    def enterEvent(self, event: QEnterEvent):
        self.setStyleSheet("#ChatMessage { background-color: #2D2D2D; border-radius: 5px; }")
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self.setStyleSheet("#ChatMessage { background-color: transparent; border-radius: 5px; }")
        super().leaveEvent(event)

class ChatMessagesArea(QScrollArea):
    def __init__(self, brain: Brain, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain

        self.chat_id = chat_id
        self.domain = domain

        self.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 5, 0, 10)
        self.container_layout.setSpacing(20)
        self.container_layout.addStretch(1)
        self.container.setLayout(self.container_layout)

        self.scroll_bar = self.verticalScrollBar()
        # IDK why it gives a PyUnresolvedReferences here, but we'll roll with it
        # noinspection PyUnresolvedReferences
        self.scroll_bar.valueChanged.connect(self.__height_changed)
        # noinspection PyUnresolvedReferences
        self.scroll_bar.rangeChanged.connect(self.__range_changed)

        self.setWidget(self.container)

        self.was_at_bottom = True

        self.load_old_messages(None)

    def update_user(self, username: str, domain: str):
        for idx in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(idx).widget()
            if isinstance(widget, ChatMessage):
                if widget.sender == username:
                    icon_path = self.brain.get_user_icon_path(username, domain)
                    widget.set_sender_icon(icon_path)
                if widget.reply_sender == username:
                    icon_path = self.brain.get_user_icon_path(username, domain)
                    widget.set_reply_sender_icon(icon_path)


    def __height_changed(self, value: int):
        self.was_at_bottom = value >= self.scroll_bar.maximum() - 20

        if value == 0:
            oldest_message = self.container_layout.itemAt(0)
            if oldest_message.spacerItem() is not None:
                self.load_old_messages(None)
            else:
                oldest_message = oldest_message.widget()
                if isinstance(oldest_message, ChatMessage):
                    self.load_old_messages(oldest_message.message_id)

    def __range_changed(self, _: int, max_value: int):
        if self.was_at_bottom:
            self.scroll_bar.setValue(max_value)

    def load_old_messages(self, oldest_message_id: str | None):
        messages = self.brain.load_messages(self.chat_id, self.domain, oldest_message_id)
        self.add_messages(messages, 0)

        if oldest_message_id is None:
            self.scroll_bar.setValue(self.scroll_bar.maximum())

    def add_messages(self, messages: list, starting_position: int = -1):
        # -1 --> ADD TO THE PEAK

        if starting_position == -1:
            position = self.container_layout.count() - 1
        else:
            position = starting_position

        for message in messages:
            local_time = time.localtime(message['timestamp'])
            formatted_time = time.strftime("%H:%M:%S %d/%m/%Y", local_time)
            message_widget = ChatMessage(
                brain = self.brain,
                chat_id = message['chat_id'],
                domain = message['domain'],
                message_id = message['message_id'],
                sender = message['sender'],
                was_edited = message['was_edited'],
                is_reply = message['is_reply'],
                reply_sender = message['reply_sender'],
                reply_snip = message['reply_snip'],
                timestamp = formatted_time,
                text = message['text'],
                uploaded_files = message['uploaded_files']
            )
            self.container_layout.insertWidget(position, message_widget)
            position += 1

    def remove_messages(self, messages: list[str]):
        for row in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(row).widget()
            if isinstance(widget, ChatMessage):
                if widget.message_id in messages:
                    self.container_layout.removeWidget(widget)
                    widget.deleteLater()

    def edit_message(self, message_id: str, text: str):
        for row in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(row).widget()
            if isinstance(widget, ChatMessage):
                if widget.message_id == message_id:
                    widget.edit_text(text)
                    return

class CustomListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def wheelEvent(self, event):
        super().wheelEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

class CustomListWidgetItem(QListWidgetItem):
    def __init__(self):
        super().__init__()

    def __lt__(self, other: QListWidgetItem):
        return self.text().lower() < other.text().lower()

class ChatMembersList(QWidget):
    def __init__(self, brain: Brain, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain
        self.chat_id = chat_id
        self.domain = domain

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search member...")
        self.search_bar.setFixedSize(MEMBERS_SEARCH_BAR_WIDTH, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.search)

        self.list_widget = CustomListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setMinimumHeight(200)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.widget_layout = QVBoxLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.widget_layout.addWidget(self.search_bar, alignment=Qt.AlignmentFlag.AlignRight)
        self.widget_layout.addWidget(self.list_widget)
        self.setLayout(self.widget_layout)

        chat_users = self.brain.get_chat_users(self.chat_id, self.domain)
        self.add_members_dicts(chat_users)

    def show_context_menu(self, position):
        current_user_domain = self.brain.get_current_user_domain()
        if current_user_domain != self.domain: return

        current_user_username = self.brain.get_current_user_username()
        user_is_admin = self.brain.user_is_admin(self.chat_id, self.domain, current_user_username)
        if not user_is_admin: return

        item = self.list_widget.itemAt(position)
        if not item: return

        item_data = item.data(Qt.ItemDataRole.UserRole)
        selected_user_username = item_data['username']
        selected_user_is_admin = item_data['is_admin']

        chat_creator = self.brain.get_chat_creator(self.chat_id, self.domain)
        if selected_user_is_admin and current_user_username != chat_creator: return
        if selected_user_username == current_user_username: return
        if chat_creator == selected_user_username: return

        make_admin = object()
        remove_admin = object()

        menu = QMenu()

        if selected_user_is_admin:
            remove_admin = menu.addAction("Remove Admin")
        else:
            make_admin = menu.addAction("Make Admin")

        global_pos = self.list_widget.mapToGlobal(position)
        selected_action = menu.exec(global_pos)

        # Checking to see if the item wasn't removed while the context menu was opened
        if not item.listWidget(): return

        if selected_action == remove_admin:
            self.__remove_admin(item)

        elif selected_action == make_admin:
            self.__make_admin(item)

    def __make_admin(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']
        self.change_member_admin_status_display(username, True)
        self.brain.change_admin_status(self.chat_id, self.domain, username, True)

    def __remove_admin(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']
        self.change_member_admin_status_display(username, False)
        self.brain.change_admin_status(self.chat_id, self.domain, username, False)

    def change_member_admin_status_display(self, username: str, is_admin: bool):
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if username == item_data['username']:
                if is_admin and not item_data['is_admin']:
                    item.setText(f"{username} (Admin)")
                    item_data['is_admin'] = is_admin
                    item.setData(Qt.ItemDataRole.UserRole, item_data)
                elif not is_admin and item_data['is_admin']:
                    item.setText(username)
                    item_data['is_admin'] = is_admin
                    item.setData(Qt.ItemDataRole.UserRole, item_data)

    def search(self, text):
        text = text.lower()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def add_members_dicts(self, members: list):
        for member in members:
            member_icon = self.brain.get_user_icon_path(member['username'], self.domain)
            self.add_entry(member['username'], member_icon, member['is_admin'])
        self.list_widget.sortItems(Qt.SortOrder.AscendingOrder)

    def add_members_usernames(self, usernames: list):
        for username in usernames:
            user_icon = self.brain.get_user_icon_path(username, self.domain)
            is_admin = self.brain.user_is_admin(self.chat_id, self.domain, username)
            self.add_entry(username, user_icon, is_admin)
        self.list_widget.sortItems(Qt.SortOrder.AscendingOrder)

    def remove_members_usernames(self, usernames: list):
        for row in reversed(range(self.list_widget.count())):
            item = self.list_widget.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            username = item_data['username']
            if username in usernames:
                self.list_widget.takeItem(row)

    def add_entry(self, username: str, user_icon_path: str, is_admin: bool):
        item = CustomListWidgetItem()
        item.setIcon(QIcon(user_icon_path))
        item.setText(f"{username}{" (Admin)" if is_admin else ""}")
        item.setData(Qt.ItemDataRole.UserRole, {"username": username, "is_admin": is_admin})
        self.list_widget.addItem(item)

    def update_user(self, username: str, domain: str):
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['username'] == username:
                user_icon = self.brain.get_user_icon_path(username, domain)
                icon = QIcon(user_icon)
                item.setIcon(icon)
                return


class ChatDetails(QScrollArea):
    chat_history_requested = pyqtSignal()

    def __init__(self, brain: Brain, text_dialog: ChatDetailsEditDialog, add_users_dialog: AddUsersDialog,
                 remove_users_dialog: RemoveUsersDialog, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain
        self.text_edit_dialog = text_dialog
        self.add_users_dialog = add_users_dialog
        self.remove_users_dialog = remove_users_dialog
        self.chat_id = chat_id
        self.domain = domain

        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)

        self.back_button = QPushButton()
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(30, 30)
        self.back_button.setIcon(QIcon("./Icons/close_icon.png"))
        self.back_button.clicked.connect(self.chat_history_requested.emit)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.chat_icon = QPushButton()
        self.chat_icon.setIconSize(QSize(64, 64))
        self.chat_icon.setFixedSize(64, 64)
        chat_icon_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        self.chat_icon.setIcon(QIcon(chat_icon_path))
        self.chat_icon.clicked.connect(self.change_chat_icon)
        self.chat_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.chat_icon.setStyleSheet("background: transparent; border: none; ")

        chat_name_container = QWidget()
        chat_name_container_layout = QHBoxLayout()
        chat_name_container_layout.setContentsMargins(0, 0, 0, 0)
        chat_name_container_layout.setSpacing(5)
        chat_name_container.setLayout(chat_name_container_layout)

        self.chat_name = QLabel()
        chat_name = self.brain.get_chat_display_name(self.chat_id, self.domain)
        self.chat_name.setText(chat_name)
        self.chat_name.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        if chat_type == "chatroom":

            self.edit_name_button = QPushButton()
            self.edit_name_button.setIcon(QIcon("./Icons/edit_icon.png"))
            self.edit_name_button.setFixedSize(20, 20)
            self.edit_name_button.setIconSize(QSize(16, 16))
            self.edit_name_button.clicked.connect(self.edit_name)
            self.edit_name_button.setCursor(Qt.CursorShape.PointingHandCursor)

            chat_name_container_layout.addWidget(self.chat_name, alignment=Qt.AlignmentFlag.AlignRight)
            chat_name_container_layout.addWidget(self.edit_name_button, alignment=Qt.AlignmentFlag.AlignLeft)
        else:
            chat_name_container_layout.addWidget(self.chat_name, alignment=Qt.AlignmentFlag.AlignCenter)

        chat_description_label = QLabel()
        chat_description_label.setText('Description:')

        self.chat_description_text = QTextEdit()
        chat_description = self.brain.get_chat_description(self.chat_id, self.domain)
        self.chat_description_text.setPlainText(chat_description)
        self.chat_description_text.setReadOnly(True)
        self.chat_description_text.setFrameShape(QTextEdit.Shape.NoFrame)
        self.chat_description_text.setStyleSheet("background: transparent;")
        self.chat_description_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_description_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.chat_description_text.document().setDocumentMargin(0)
        self.chat_description_text.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        chat_description = QWidget()
        chat_description_layout = QVBoxLayout()
        chat_description_layout.setContentsMargins(5, 0, 5, 5)
        chat_description_layout.setSpacing(5)
        chat_description.setLayout(chat_description_layout)

        chat_description_layout.addWidget(chat_description_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        chat_description_layout.addWidget(self.chat_description_text, alignment=Qt.AlignmentFlag.AlignTop)

        if chat_type == "chatroom":
            self.change_chat_description_button = QPushButton()
            self.change_chat_description_button.setIcon(QIcon("./Icons/edit_icon.png"))
            self.change_chat_description_button.setFixedSize(20, 20)
            self.change_chat_description_button.setIconSize(QSize(16, 16))
            self.change_chat_description_button.clicked.connect(self.edit_description)
            self.change_chat_description_button.setCursor(Qt.CursorShape.PointingHandCursor)
            chat_description_layout.addWidget(self.change_chat_description_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignCenter)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(5, 0, 5, 5)
        self.container_layout.setSpacing(5)
        self.container.setLayout(self.container_layout)

        self.container_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.container_layout.addWidget(self.chat_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(chat_name_container, alignment=Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(chat_description)

        if chat_type == 'chatroom':
            self.chat_members_list = ChatMembersList(brain, chat_id, domain)

            add_members_button = QPushButton()
            add_members_button.setIcon(QIcon("./Icons/plus_icon.png"))
            add_members_button.setText("Add members")
            add_members_button.setFixedWidth(130)
            add_members_button.clicked.connect(self.add_members)
            add_members_button.setCursor(Qt.CursorShape.PointingHandCursor)

            remove_members_button = QPushButton()
            remove_members_button.setIcon(QIcon("./Icons/minus_icon.png"))
            remove_members_button.setText("Remove members")
            remove_members_button.setFixedWidth(130)
            remove_members_button.clicked.connect(self.remove_members)
            remove_members_button.setCursor(Qt.CursorShape.PointingHandCursor)

            self.button_container = QWidget()
            button_container_layout = QHBoxLayout()
            button_container_layout.setContentsMargins(0, 0, 0, 0)
            button_container_layout.setSpacing(5)
            self.button_container.setLayout(button_container_layout)

            button_container_layout.addWidget(add_members_button)
            button_container_layout.addWidget(remove_members_button)

            self.container_layout.addWidget(self.chat_members_list)
            self.container_layout.addWidget(self.button_container)

            self.brain.current_user_changed.connect(self.update_description)

        self.container_layout.addStretch()

        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        self.update_description(current_user_username, current_user_domain)
        self.brain.chat_updated.connect(self.handle_chat_description_change)

        self.setWidget(self.container)
        self.setWidgetResizable(True)

    def change_chat_icon(self):
        """
        TO DO:
            - currently, the os blocks the file from being removed due to it being loaded in memory.
                A solution for this is to add the path to a cleanup list, and when the app closes, delete
                the files in the cleanup list.
                Another solution is to save the file path in a separate file and, on app startup, when no widgets
                are loaded, delete the files in the cleanup list.
        """
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self,  # Parent widget
            "Select Image",  # Dialog Title
            "",  # Starting directory ("" = last visited)
            "Images (*.png *.jpg *.jpeg)"  # File filters
        )

        if not file_path:
            return

        with Image.open(file_path) as original_image:
            image_copy = original_image.copy()

        new_width = 64
        new_height = 64
        resized_copy = image_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)

        save_dir = "./Cache/ChatIcons"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        new_file_path = f"{save_dir}/{self.chat_id}_{int(time.time())}.png"

        resized_copy.save(new_file_path, "PNG")

        old_file_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)

        self.brain.set_chat_icon_path(self.chat_id, self.domain, new_file_path)

        if old_file_path != "./Icons/chat_room_icon.png":
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError:
                    pass

    def add_members(self):
        if self.add_users_dialog.isVisible():
            self.add_users_dialog.raise_()
            self.add_users_dialog.activateWindow()
            return

        self.add_users_dialog.set_chat_details(self.chat_id, self.domain)
        ret = self.add_users_dialog.load_users()
        if not ret:
            error_msg = "Could not load chatroom members!"
            # ERROR WINDOW POPUP
            return

        self.add_users_dialog.exec()

    def remove_members(self):
        if self.remove_users_dialog.isVisible():
            self.remove_users_dialog.raise_()
            self.remove_users_dialog.activateWindow()
            return

        self.remove_users_dialog.set_chat_details(self.chat_id, self.domain)
        ret = self.remove_users_dialog.load_users()
        if not ret:
            error_msg = "Could not load chatroom members!"
            # ERROR WINDOW POPUP
            return

        self.remove_users_dialog.exec()

    def __resize_description_box(self):
        text_height = int(self.chat_description_text.document().size().height()) + 2
        box_height = self.chat_description_text.height()
        if text_height != box_height:
            self.chat_description_text.setFixedHeight(text_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_description_box()

    def edit_name(self):
        if self.text_edit_dialog.isVisible():
            self.text_edit_dialog.raise_()
            self.text_edit_dialog.activateWindow()
            return

        self.text_edit_dialog.set_chat_details(self.chat_id, self.domain)
        self.text_edit_dialog.set_edited_field("name")
        self.text_edit_dialog.set_text_hint("Type chat name...")
        current_name = self.chat_name.text()
        self.text_edit_dialog.set_text(current_name)
        self.text_edit_dialog.set_label_text("Change Chat Name:")
        self.text_edit_dialog.exec()

    def edit_description(self):
        if self.text_edit_dialog.isVisible():
            self.text_edit_dialog.raise_()
            self.text_edit_dialog.activateWindow()
            return

        self.text_edit_dialog.set_chat_details(self.chat_id, self.domain)
        self.text_edit_dialog.set_edited_field("description")
        self.text_edit_dialog.set_text_hint("Type chat description...")
        current_name = self.chat_description_text.toPlainText()
        self.text_edit_dialog.set_text(current_name)
        self.text_edit_dialog.set_label_text("Change Chat Description:")
        self.text_edit_dialog.exec()

    def update_user(self, username: str, domain: str):
        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if chat_type == 'p2p':
            self.update_labels()
        else:
            self.chat_members_list.update_user(username, domain)

    def update_labels(self):
        chat_icon_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        self.chat_icon.setIcon(QIcon(chat_icon_path))
        chat_name = self.brain.get_chat_display_name(self.chat_id, self.domain)
        self.chat_name.setText(chat_name)
        chat_description = self.brain.get_chat_description(self.chat_id, self.domain)
        self.chat_description_text.setText(chat_description)
        self.__resize_description_box()

    def handle_chat_description_change(self, chat_id: str, domain: str):
        if self.chat_id == chat_id and self.domain == domain:
            self.update_labels()

    def update_description(self, username: str, domain: str):
        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if chat_type == 'p2p':
            # no member management buttons
            if self.domain == domain:
                self.update_labels()
            return

        if domain == self.domain:
            user_is_admin = self.brain.user_is_admin(self.chat_id, domain, username)
            self.button_container.setVisible(user_is_admin)
            self.change_chat_description_button.setVisible(user_is_admin)
            self.edit_name_button.setVisible(user_is_admin)
            self.chat_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not user_is_admin)
            if user_is_admin:
                self.chat_icon.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.chat_icon.setCursor(Qt.CursorShape.ArrowCursor)

        else:
            self.button_container.setVisible(False)
            self.change_chat_description_button.setVisible(False)
            self.edit_name_button.setVisible(False)

    def add_users_usernames(self, usernames: list):
        self.chat_members_list.add_members_usernames(usernames)

    def remove_users_usernames(self, usernames: list):
        self.chat_members_list.remove_members_usernames(usernames)

class Chat(QWidget):
    chat_details_requested = pyqtSignal()

    def __init__(self, brain: Brain, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain
        self.chat_id = chat_id
        self.domain = domain

        self.widget_layout = QVBoxLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)
        self.setLayout(self.widget_layout)

        self.chat_messages = ChatMessagesArea(brain, chat_id, domain)

        button_container = QWidget()
        button_container_layout = QHBoxLayout()
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(5)
        button_container.setLayout(button_container_layout)

        self.chat_details_button = QPushButton()
        chat_name = self.brain.get_chat_display_name(self.chat_id, self.domain)
        self.chat_details_button.setText(chat_name)
        chat_icon_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        self.chat_details_button.setIcon(QIcon(chat_icon_path))
        self.chat_details_button.setFixedHeight(25)
        self.chat_details_button.clicked.connect(self.chat_details_requested.emit)
        self.chat_details_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.back_button = QPushButton()
        self.back_button.setFixedSize(25, 25)
        self.back_button.setIcon(QIcon("./Icons/left_arrow_icon.png"))
        self.back_button.clicked.connect(self.go_to_users_tab)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)

        button_container_layout.addWidget(self.back_button)
        button_container_layout.addWidget(self.chat_details_button)

        self.widget_layout.addWidget(button_container)
        self.widget_layout.addWidget(self.chat_messages)

        self.brain.current_user_changed.connect(self.__handle_current_user_change)
        self.brain.chat_updated.connect(self.__handle_chat_update)

    def __reload_chat_details(self):
        chat_name = self.brain.get_chat_display_name(self.chat_id, self.domain)
        self.chat_details_button.setText(chat_name)
        chat_icon = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        self.chat_details_button.setIcon(QIcon(chat_icon))

    def update_user(self, username: str, domain: str):
        self.__reload_chat_details()
        self.chat_messages.update_user(username, domain)

    def go_to_users_tab(self):
        self.brain.select_chat.emit("", "")

    def __handle_chat_update(self, chat_id: str, domain: str):
        if self.chat_id == chat_id and self.domain == domain:
            self.__reload_chat_details()

    def __handle_current_user_change(self, _: str, domain: str):
        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if domain == self.domain and chat_type == 'p2p':
            self.__reload_chat_details()

    def add_messages(self, messages: list):
        self.chat_messages.add_messages(messages)

    def remove_messages(self, messages: list[str]):
        self.chat_messages.remove_messages(messages)

    def edit_message(self, message_id: str, text: str):
        self.chat_messages.edit_message(message_id, text)

class ChatBubble(QWidget):
    def __init__(self, brain: Brain, text_dialog: ChatDetailsEditDialog, add_users_dialog: AddUsersDialog,
                 remove_users_dialog: RemoveUsersDialog, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain

        self.chat_id = chat_id
        self.domain = domain
        self.last_access_time = time.time()

        self.chat = Chat(brain, chat_id, domain)
        self.chat.chat_details_requested.connect(self.display_chat_details)

        self.chat_details_widget = ChatDetails(brain, text_dialog, add_users_dialog, remove_users_dialog, chat_id, domain)
        self.chat_details_widget.chat_history_requested.connect(self.display_chat)

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)
        self.setLayout(self.widget_layout)

        self.widget_layout.addWidget(self.chat)
        self.widget_layout.addWidget(self.chat_details_widget)
        self.widget_layout.setCurrentIndex(0)

    def update_user(self, username: str, domain: str):
        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if chat_type == 'p2p':
            self.chat.update_user(username, domain)
        self.chat_details_widget.update_user(username, domain)

    def display_chat_details(self):
        self.widget_layout.setCurrentIndex(1)
        self.brain.change_textbox_visibility.emit(False)

    def display_chat(self):
        self.widget_layout.setCurrentIndex(0)
        self.brain.change_textbox_visibility.emit(True)

    def add_messages(self, messages: list):
        self.chat.add_messages(messages)

    def remove_messages(self, messages: list):
        self.chat.remove_messages(messages)

    def edit_message(self, message_id: str, text: str):
        self.chat.edit_message(message_id, text)

    def add_users_usernames(self, usernames: list):
        self.chat_details_widget.add_users_usernames(usernames)

    def remove_users_usernames(self, usernames: list):
        self.chat_details_widget.remove_users_usernames(usernames)

class UsersList(QListWidget):
    def __init__(self, brain: Brain):
        super().__init__()
        self.setMouseTracking(True)

        self.brain = brain
        self.brain.current_user_changed.connect(self.handle_user_change)
        self.brain.user_updated.connect(self.handle_user_updated)

        self.setIconSize(QSize(32, 32))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.itemClicked.connect(self.handle_item_clicked_changed)

        self.initialize()

    def handle_user_updated(self, username: str, domain: str):
        for idx in range(self.count()):
            item = self.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['username'] == username and item_data['domain'] == domain:
                user_icon = self.brain.get_user_icon_path(username, domain)
                icon = QIcon(user_icon)
                item.setIcon(icon)
                return

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def initialize(self):
        current_user_domain = self.brain.get_current_user_domain()
        domain_users = self.brain.get_domain_users(current_user_domain)
        self.add_users(current_user_domain, domain_users)

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item: return

        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']

        cu_blacklist = self.brain.get_current_user_blacklist()

        block_user = object()
        unblock_user = object()

        menu = QMenu()

        if username in cu_blacklist:
            unblock_user = menu.addAction("Unblock User")
        else:
            block_user = menu.addAction("Block User")

        global_pos = self.mapToGlobal(position)
        selected_action = menu.exec(global_pos)

        # Checking to see if the item wasn't removed while the context menu was opened
        if not item.listWidget(): return

        if selected_action == unblock_user:
            self.__unblock_user(item)

        elif selected_action == block_user:
            self.__block_user(item)

    def __block_user(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']
        self.brain.block_user(username)

    def __unblock_user(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']
        self.brain.unblock_user(username)

    def handle_item_clicked_changed(self, item: QListWidgetItem):
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()

        item_data = item.data(Qt.ItemDataRole.UserRole)
        username = item_data['username']
        domain = item_data['domain']
        if domain != current_user_domain: return

        chat_id = self.brain.p2p_chat_exists(current_user_username, username, domain)
        if chat_id is None:
            cu_blacklist = self.brain.get_current_user_blacklist()
            if username not in cu_blacklist:
                ret = self.brain.create_p2p_chat(username, domain)
                if not ret[0]:
                    error_message = ret[1]
                    # ERROR WINDOW POPUP
                    return
                chat_id = ret[1]
            else:
                return

        self.brain.select_chat.emit(chat_id, domain)

    def handle_user_change(self, username: str, domain: str):
        domain_users = self.brain.get_domain_users(domain)
        if domain_users:
            self.add_users(domain, domain_users)

        for idx in range(self.count()):
            item = self.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['username'] == username and item_data['domain'] == domain:
                item.setHidden(True)
            elif item_data['domain'] == domain:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def remove_user(self, username: str, domain: str):
        for idx in range(self.count()):
            item = self.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['username'] == username and item_data['domain'] == domain:
                self.takeItem(idx)
                return

    def __user_already_in_list(self, username: str, domain: str):
        for idx in range(self.count()):
            item = self.item(idx)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data['username'] == username and item_data['domain'] == domain:
                return True
        return False

    def add_users(self, domain: str, users: list):
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        for user in users:
            if self.__user_already_in_list(user['username'], domain): continue

            item = CustomListWidgetItem()
            item.setText(user['username'])
            icon_path = self.brain.get_user_icon_path(user['username'], domain)
            item.setIcon(QIcon(icon_path))
            item_data = {
                "username": user['username'],
                "domain": domain
            }
            item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.addItem(item)
            if user['username'] == current_user_username and domain == current_user_domain:
                item.setHidden(True)
            else:
                item.setHidden(False)

        self.sortItems(Qt.SortOrder.AscendingOrder)

class UsersTab(QWidget):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(5)
        self.setLayout(tab_layout)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search user...")
        self.search_bar.setFixedSize(MEMBERS_SEARCH_BAR_WIDTH, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.search)

        self.users_list = UsersList(brain)

        tab_layout.addWidget(self.search_bar)
        tab_layout.addWidget(self.users_list)

    def search(self, text):
        text = text.lower()
        for row in range(self.users_list.count()):
            item = self.users_list.item(row)
            item_data = item.data(Qt.ItemDataRole.UserRole)
            username = item_data['username']
            user_domain = item_data['domain']
            current_user_username = self.brain.get_current_user_username()
            current_user_domain = self.brain.get_current_user_domain()
            if user_domain == current_user_domain and current_user_username != username:
                if text == "" or text in item.text():
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                item.setHidden(True)

class ChatHistory(QWidget):
    def __init__(self, brain: Brain, add_users_dialog: AddUsersDialog):
        super().__init__()

        self.brain = brain

        self.text_dialog = ChatDetailsEditDialog(brain)
        self.add_users_dialog = add_users_dialog
        self.remove_users_dialog = RemoveUsersDialog(brain)

        self.max_bubbles = Brain.MAX_CHAT_BUBBLES + 1 # 1 screen for no chats

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.setLayout(self.widget_layout)

        users_tab = UsersTab(brain)
        self.widget_layout.insertWidget(0, users_tab)

        self.widget_layout.setCurrentIndex(0)

        self.brain.chat_selected.connect(self.show_chat)
        self.brain.current_user_changed.connect(self.handle_current_user_change)
        self.brain.user_updated.connect(self.handle_user_updated)
        self.brain.add_new_messages.connect(self.add_messages)
        self.brain.remove_messages.connect(self.remove_messages)
        self.brain.message_edited.connect(self.edit_message)
        self.brain.removed_members_from_chat.connect(self.remove_users)
        self.brain.added_members_to_chat.connect(self.add_users)

    def handle_user_updated(self, username: str, domain: str):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.domain != domain: continue
                user_in_chat = self.brain.user_is_in_chat(widget.chat_id, widget.domain, username)
                if user_in_chat:
                    widget.update_user(username, domain)

    def add_users(self, chat_id: str, domain: str, users: list):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == domain:
                    widget.add_users_usernames(users)
                    return

    def remove_users(self, chat_id: str, domain: str, users: list):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == domain:
                    widget.remove_users_usernames(users)
                    return

    def show_chat(self, chat_id: str, domain: str):
        current_chat_idx = self.widget_layout.currentIndex()
        current_widget = self.widget_layout.widget(current_chat_idx)
        if isinstance(current_widget, ChatBubble):
            current_widget.display_chat()
            current_widget.chat_details_widget.verticalScrollBar().setValue(0)

        if chat_id == "" and domain == "":
            self.widget_layout.setCurrentIndex(0)
            return

        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == domain:
                    self.widget_layout.setCurrentIndex(idx)
                    widget.last_access_time = time.time()
                    return

        self.__add_bubble(chat_id, domain)

    def remove_chat(self, chat_id: str, chat_domain: str):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == chat_domain:
                    self.widget_layout.removeWidget(widget)
                    widget.deleteLater()
                    return

    def handle_current_user_change(self):
        self.widget_layout.setCurrentIndex(0)

    def __add_bubble(self, chat_id: str, domain: str):
        bubble_count = self.widget_layout.count()
        if bubble_count >= self.max_bubbles:
            oldest_widget = None
            oldest_access_time = time.time()
            for idx in range(bubble_count):
                widget = self.widget_layout.widget(idx)
                if isinstance(widget, ChatBubble):
                    access_time = widget.last_access_time
                    if access_time < oldest_access_time:
                        oldest_widget = widget
                        oldest_access_time = access_time

            self.widget_layout.removeWidget(oldest_widget)
            oldest_widget.deleteLater()

        new_bubble = ChatBubble(self.brain, self.text_dialog, self.add_users_dialog, self.remove_users_dialog,chat_id, domain)
        # at index 0 there is a special screen for when there are no chats selected
        self.widget_layout.insertWidget(1, new_bubble)
        self.widget_layout.setCurrentIndex(1)

    def add_messages(self, messages: dict):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if (widget.chat_id, widget.domain) in messages.keys():
                    widget.add_messages(messages[(widget.chat_id, widget.domain)])

    def edit_message(self, chat_id: str, domain: str, message_id: str, text: str):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_id and widget.domain == domain:
                    widget.edit_message(message_id, text)

    def remove_messages(self, messages: dict):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if (widget.chat_id, widget.domain) in messages.keys():
                    widget.remove_messages(messages[(widget.chat_id, widget.domain)])

class ChatTextBox(QTextEdit):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.init_height = 25
        self.max_height = 73

        self.setPlaceholderText("Start typing...")
        self.setFixedHeight(self.init_height)
        self.setMinimumWidth(50)

        self.brain.set_textbox_text.connect(self.set_text)

    def set_text(self, text):
        self.setPlainText(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.brain.send_message.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

class MessageContext(QWidget):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.brain.chat_selected.connect(self.reset_context)
        self.brain.clear_message_context.connect(self.reset_context)

        self.setFixedHeight(25)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        self.context_label = QLabel()
        self.context_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.context_sender_icon = QLabel()

        self.context_user_label = QLabel()
        self.context_user_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.context_snip_label = ElidedLabel()

        exit_context_button = QPushButton()
        exit_context_button.setFixedSize(24, 24)
        exit_context_button.setIconSize(QSize(24, 24))
        exit_context_button.setIcon(QIcon("./Icons/close_icon.png"))
        exit_context_button.clicked.connect(self.reset_context)
        exit_context_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(exit_context_button)
        layout.addWidget(self.context_label)
        layout.addWidget(self.context_sender_icon)
        layout.addWidget(self.context_user_label)
        layout.addWidget(self.context_snip_label)

        self.brain.message_context_changed.connect(self.context_changed)

        self.setVisible(False)

    def reset_context(self):
        self.brain.set_reply(False)
        self.brain.set_edit(False)
        self.brain.message_context_changed.emit()

    def context_changed(self):
        reply_details = self.brain.get_reply_details()
        edit_details = self.brain.get_edit_details()
        if reply_details['is_reply']:
            self.context_label.setText("Replying to:")
            self.context_sender_icon.setPixmap(QPixmap(reply_details['reply_sender_icon_path']).scaled(24, 24))
            self.context_user_label.setText(f"{reply_details['reply_sender']}:")
            self.context_snip_label.setText(f"{reply_details['reply_snip']}")
            self.setVisible(True)
        elif edit_details['is_edit']:
            self.context_label.setText("Editing:")
            self.context_sender_icon.setPixmap(QPixmap(edit_details['sender_icon_path']).scaled(24, 24))
            self.context_user_label.setText(f"{edit_details['sender']}:")
            self.context_snip_label.setText(f"{edit_details['message_snip']}")
            self.setVisible(True)
        else:
            self.setVisible(False)

class AttachmentBubble(QWidget):
    def __init__(self, brain: Brain, file_path: str):
        super().__init__()

        self.brain = brain

        self.setFixedHeight(25)
        self.setObjectName("FileWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("#FileWidget { background-color: #2D2D2D; border-radius: 5px; }")

        self.full_file_path = file_path
        self.file_path = os.path.basename(file_path)
        self.file_extension = os.path.splitext(self.file_path)[1].lower()

        widget_layout = QHBoxLayout()
        widget_layout.setContentsMargins(2, 0, 2, 0)
        widget_layout.setSpacing(5)
        self.setLayout(widget_layout)

        file_icon = QLabel()
        file_icon_path = "./Icons/file_uploaded_icon.png"
        file_icon.setPixmap(QPixmap(file_icon_path).scaled(24, 24))

        path_label = ElidedLabel()
        path_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        path_label.setMinimumWidth(30)
        path_label.setMaximumWidth(100)
        path_label.setText(self.file_path)

        remove_button = QPushButton()
        remove_button.setFixedSize(20, 20)
        remove_button.setIcon(QIcon("./Icons/close_icon.png"))
        remove_button.setIconSize(QSize(20, 20))
        remove_button.clicked.connect(self.emit_removed_file)
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)

        widget_layout.addWidget(file_icon)
        widget_layout.addWidget(path_label)
        widget_layout.addWidget(remove_button)

    def emit_removed_file(self):
        self.brain.upload_context_files_removed.emit([self.full_file_path])

class AttachmentContext(QScrollArea):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.brain.upload_context_files_removed.connect(self.remove_files)
        self.brain.upload_context_files_added.connect(self.add_files)
        self.brain.clear_message_context.connect(self.clear_files)
        self.brain.chat_selected.connect(self.clear_files)
        self.brain.clear_staged_files.connect(self.clear_files)

        self.setFixedHeight(37)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.container_layout = QHBoxLayout()
        self.container_layout.setContentsMargins(5, 0, 5, 0)
        self.container_layout.setSpacing(5)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container.setLayout(self.container_layout)
        self.container_layout.addStretch()

        self.setWidget(container)
        self.setVisible(False)

        self.staged_files = []

    def add_files(self, file_paths: list):
        for file_path in file_paths:
            if file_path in self.staged_files: continue
            self.staged_files.append(file_path)
            attachment = AttachmentBubble(self.brain, file_path)
            idx = self.container_layout.count() - 1
            self.container_layout.insertWidget(idx, attachment)

        self.setVisible(len(self.staged_files) > 0)

    def remove_files(self, file_paths: list):
        for idx in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(idx).widget()
            if isinstance(item, AttachmentBubble):
                file_path = item.full_file_path
                if file_path in file_paths:
                    self.staged_files.remove(file_path)
                    self.container_layout.removeWidget(item)
                    item.deleteLater()

        self.setVisible(len(self.staged_files) > 0)

    def clear_files(self):
        for idx in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(idx).widget()
            if isinstance(item, AttachmentBubble):
                self.container_layout.removeWidget(item)
                item.deleteLater()

        self.staged_files.clear()
        self.setVisible(False)

    def get_staged_files(self):
        return self.staged_files

class MessageWindow(QWidget):
    """
    TO DO:
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.brain.message_context_changed.connect(self.handle_context_change)

        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        self.setLayout(top_layout)

        context_widget = MessageContext(brain)
        self.upload_context_widget = AttachmentContext(brain)
        bottom_widget = QWidget()

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        bottom_widget.setLayout(bottom_layout)

        self.upload_file_button = QPushButton()
        self.upload_file_button.setFixedSize(40, 40)
        self.upload_file_button.setIconSize(QSize(32, 32))
        self.upload_file_button.setIcon(QIcon("./Icons/upload_file_icon.png"))
        self.upload_file_button.clicked.connect(self.upload_file)
        self.upload_file_button.setCursor(Qt.CursorShape.PointingHandCursor)

        send_message_button = QPushButton()
        send_message_button.setFixedSize(40, 40)
        send_message_button.setIconSize(QSize(32, 32))
        send_message_button.setIcon(QIcon("./Icons/send_message_icon.png"))
        send_message_button.clicked.connect(self.send_message)
        send_message_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.text_box = ChatTextBox(brain)
        self.text_box.setMinimumWidth(200)

        bottom_layout.addWidget(self.upload_file_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        bottom_layout.addWidget(self.text_box)
        bottom_layout.addWidget(send_message_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        top_layout.addWidget(context_widget)
        top_layout.addWidget(self.upload_context_widget)
        top_layout.addWidget(bottom_widget)

        self.setVisible(False) # initially not visible due to no chat being selected

        self.text_box.textChanged.connect(self.__resize_text_box)
        self.brain.send_message.connect(self.send_message)
        self.brain.change_textbox_visibility.connect(self.set_visibility_bool)
        self.brain.chat_selected.connect(self.set_visibility_str)

    def handle_context_change(self):
        edit_details = self.brain.get_edit_details()
        if edit_details['is_edit']:
            self.upload_file_button.setEnabled(False)
        else:
            self.upload_file_button.setEnabled(True)

    def set_visibility_bool(self, is_visible: bool):
        current_chat_setting = self.brain.get_current_chat_setting()
        if current_chat_setting is None:
            self.setVisible(False)
        else:
            self.setVisible(current_chat_setting == "rw" and is_visible)

    def set_visibility_str(self, chat_id: str, domain: str):
        current_chat_setting = self.brain.get_current_chat_setting()
        if current_chat_setting is None:
            self.setVisible(False)
        else:
            self.setVisible(current_chat_setting == "rw" and chat_id != "" and domain != "")

    def __resize_text_box(self):
        old_height = self.text_box.height()
        text_height = int(self.text_box.document().size().height()) + 2 # prevents character clipping
        new_height = min(text_height, self.text_box.max_height)
        if old_height != new_height:
            self.text_box.setFixedHeight(new_height)

    def resizeEvent(self, event):
        self.__resize_text_box()
        super().resizeEvent(event)

    def send_message(self):

        # SEND MESSAGE REQUEST
        # ON RESPONSE = OK, CLEAR THE TEXTBOX AND SET REPLY DETAILS AND EDIT DETAILS TO NONE

        text = self.text_box.toPlainText().strip()
        staged_files = self.upload_context_widget.get_staged_files()
        if text == "" and len(staged_files) == 0: return

        current_chat_id = self.brain.get_current_chat_id()
        current_chat_domain = self.brain.get_current_chat_domain()
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        current_user_icon_path = self.brain.get_current_user_icon()

        if current_chat_domain != current_user_domain: return

        edit_details = self.brain.get_edit_details()

        if edit_details['is_edit']:
            # process different requests
            self.brain.message_edited.emit(current_chat_id, current_chat_domain, edit_details['edit_message_id'], text)

            self.brain.set_edit(False)
            self.brain.message_context_changed.emit()
            self.text_box.clear()
            self.brain.clear_message_context.emit()
            return

        reply_details = self.brain.get_reply_details()

        # MAKE REQUEST
        # ONLY ADD AND DISPLAY MESSAGE ON SERVER UPDATE

        files = self.brain.upload_files(staged_files)

        message = message_args_to_dict(
            chat_id = current_chat_id,
            domain = current_chat_domain,
            message_id = str(int(random.random() * 10000)),
            sender = current_user_username,
            was_edited = False,
            is_reply = reply_details['is_reply'],
            reply_sender = reply_details['reply_sender'],
            reply_snip = reply_details['reply_snip'],
            timestamp = time.time(),
            text = text,
            files = files
        )

        self.brain.add_new_messages.emit({
            (current_chat_id, current_chat_domain): [message]
        })
        self.text_box.clear()
        self.brain.clear_message_context.emit()

    def upload_file(self):
        file_paths, selected_filter = QFileDialog.getOpenFileNames(
            self,  # Parent widget
            "Select Files to Upload",  # Dialog Title
            "",  # Starting directory ("" = last visited)
            "All Files (*);;Images (*.png *.jpg *.jpeg);;Documents (*.pdf *.txt)"  # File filters
        )

        if not file_paths:
            return

        self.brain.upload_context_files_added.emit(file_paths)

class ChatEnvironment(QWidget):
    def __init__(self, brain: Brain, add_users_dialog: AddUsersDialog):
        super().__init__()

        self.brain = brain

        self.chat_history = ChatHistory(brain, add_users_dialog)
        self.message_window = MessageWindow(brain)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_window, alignment=Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setMinimumWidth(RIGHT_PANE_MIN_WIDTH)