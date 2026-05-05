from PyQt6.QtWidgets import (
    QPushButton, QVBoxLayout, QLabel, QStackedLayout, QWidget, QHBoxLayout,
    QTextEdit, QSizePolicy, QScrollArea, QLineEdit, QListWidget, QAbstractItemView, QListWidgetItem
)

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFontMetrics

import time

RIGHT_PANE_MIN_WIDTH = 310
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

class ChatMessagesArea(QScrollArea):
    """
    TO DO:
        - implement context menu for messages (reply, edit, delete)
    """
    def __init__(self):
        super().__init__()

        self.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 5, 0, 10)
        self.container_layout.setSpacing(20)
        self.container.setLayout(self.container_layout)

        self.scroll_bar = self.verticalScrollBar()
        # noinspection PyUnresolvedReferences
        # IDK why it gives a PyUnresolvedReferences here, but we'll roll with it
        self.scroll_bar.rangeChanged.connect(self.__scroll_to_bottom)

        self.setWidget(self.container)

    def __scroll_to_bottom(self, _: int, max_value: int):
        self.scroll_bar.setValue(max_value)

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

    def add_message(self, message: ChatMessage):
        self.container_layout.addWidget(message)

class ChatMembersList(QWidget):
    def __init__(self, initial_members: list):
        super().__init__()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search member...")
        self.search_bar.setFixedSize(MEMBERS_SEARCH_BAR_WIDTH, 25)
        search_icon = QIcon("Icons/search_icon.png")
        self.search_bar.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)
        self.search_bar.textChanged.connect(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(32, 32))
        self.list_widget.setMinimumHeight(200)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no vertical scrollbar
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no horizontal scrollbar
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.widget_layout = QVBoxLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.widget_layout.addWidget(self.search_bar, alignment=Qt.AlignmentFlag.AlignRight)
        self.widget_layout.addWidget(self.list_widget)
        self.setLayout(self.widget_layout)

        self.initialize_members(initial_members)

    def search(self, text):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if text == "" or text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def initialize_members(self, members: list):
        for member in members:
            self.add_entry(member['username'], member['icon_path'], member['is_admin'])

    def add_entry(self, username: str, user_icon_path: str, is_admin: bool):
        item = QListWidgetItem()
        item.setIcon(QIcon(user_icon_path))
        item.setText(f"{username}{" (Admin)" if is_admin else ""}")
        item.setData(Qt.ItemDataRole.UserRole, {"username": username, "is_admin": is_admin})
        self.list_widget.addItem(item)

class ChatDetails(QScrollArea):
    """
    TO DO:
        - add 'remove members' button dialog
        - add 'add members' button dialog
    """
    back_requested = pyqtSignal()

    def __init__(self, chat_details: dict, current_username: str):
        super().__init__()

        self.chat_type = chat_details['chat_type']

        self.back_button = QPushButton()
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(30, 30)
        self.back_button.setIcon(QIcon("./Icons/close_icon.png"))
        self.back_button.clicked.connect(self.back_requested)

        chat_icon = QPushButton()
        chat_icon.setIconSize(QSize(64, 64))
        chat_icon.setFixedSize(70, 70)
        chat_icon.setIcon(QIcon(chat_details['icon_path']))

        chat_description_label = QLabel()
        chat_description_label.setText('Description:')

        chat_description_text = QLabel()
        chat_description_text.setText(chat_details['chat_description'])
        chat_description_text.setWordWrap(True)

        change_chat_description_button = QPushButton()
        change_chat_description_button.setIcon(QIcon("./Icons/edit_icon.png"))
        change_chat_description_button.setFixedSize(20, 20)
        change_chat_description_button.setIconSize(QSize(16, 16))

        chat_description = QWidget()
        chat_description_layout = QVBoxLayout()
        chat_description_layout.setContentsMargins(5, 0, 5, 5)
        chat_description_layout.setSpacing(5)
        chat_description.setLayout(chat_description_layout)

        chat_description_layout.addWidget(chat_description_label, alignment=Qt.AlignmentFlag.AlignLeft)
        chat_description_layout.addWidget(chat_description_text)
        chat_description_layout.addWidget(change_chat_description_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(5, 0, 5, 5)
        self.container_layout.setSpacing(5)
        self.container.setLayout(self.container_layout)

        self.container_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.container_layout.addWidget(chat_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(chat_description)

        if chat_details['chat_type'] == 'chatroom':
            self.chat_members_list = ChatMembersList(chat_details['users'])

            add_members_button = QPushButton()
            add_members_button.setIcon(QIcon("./Icons/plus_icon.png"))
            add_members_button.setText("Add members")
            add_members_button.setFixedWidth(130)

            remove_members_button = QPushButton()
            remove_members_button.setIcon(QIcon("./Icons/minus_icon.png"))
            remove_members_button.setText("Remove members")
            remove_members_button.setFixedWidth(130)

            self.button_container = QWidget()
            button_container_layout = QHBoxLayout()
            button_container_layout.setContentsMargins(0, 0, 0, 0)
            button_container_layout.setSpacing(5)
            self.button_container.setLayout(button_container_layout)

            button_container_layout.addWidget(add_members_button)
            button_container_layout.addWidget(remove_members_button)

            self.container_layout.addWidget(self.chat_members_list)
            self.container_layout.addWidget(self.button_container)

            self.update_button_visibility(current_username)

        self.setWidget(self.container)
        self.setWidgetResizable(True)

    def update_button_visibility(self, username: str):
        if self.chat_type == 'p2p': return

        for row in range(self.chat_members_list.list_widget.count()):
            member = self.chat_members_list.list_widget.item(row)
            member_data = member.data(Qt.ItemDataRole.UserRole)
            if member_data['username'] == username:
                self.button_container.setVisible(member_data['is_admin'])
                return

        self.button_container.setVisible(False)

class Chat(QWidget):
    chat_details_requested = pyqtSignal()

    def __init__(self, chat_details: dict):
        super().__init__()

        self.widget_layout = QVBoxLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)
        self.setLayout(self.widget_layout)

        self.chat_messages = ChatMessagesArea()

        self.chat_details_button = QPushButton()
        self.chat_details_button.setText(f"{chat_details['chat_id']} ({chat_details['domain']})")
        self.chat_details_button.setIcon(QIcon(chat_details["icon_path"]))
        self.chat_details_button.setFixedHeight(25)
        self.chat_details_button.clicked.connect(self.chat_details_requested.emit)

        self.widget_layout.addWidget(self.chat_details_button)
        self.widget_layout.addWidget(self.chat_messages)

class ChatBubble(QWidget):
    change_textbox_visibility = pyqtSignal(bool)

    def __init__(self, chat_details: dict, last_access_time: float, current_username: str):
        super().__init__()

        self.chat_details = chat_details
        self.last_access_time = last_access_time

        self.chat = Chat(chat_details)
        self.chat.chat_details_requested.connect(self.display_chat_details)

        self.chat_details_widget = ChatDetails(chat_details, current_username)
        self.chat_details_widget.back_requested.connect(self.display_chat)

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)
        self.setLayout(self.widget_layout)

        self.widget_layout.addWidget(self.chat)
        self.widget_layout.addWidget(self.chat_details_widget)
        self.widget_layout.setCurrentIndex(0)

    def handle_user_changed(self):
        self.display_chat()

    def display_chat_details(self):
        self.widget_layout.setCurrentIndex(1)
        self.change_textbox_visibility.emit(False)

    def display_chat(self):
        self.widget_layout.setCurrentIndex(0)
        self.change_textbox_visibility.emit(True)

class ChatHistory(QWidget):
    change_textbox_visibility = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.current_user = None
        self.max_bubbles = 17 # 15 bubbles + 1 screen for no chats + 1 screen for loading messages

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.setLayout(self.widget_layout)

        no_chats_label = QLabel()
        no_chats_label.setText("Select a chat to vent to.")
        no_chats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widget_layout.insertWidget(0, no_chats_label)

        loading_messages_label = QLabel()
        loading_messages_label.setText("Loading messages ...")
        loading_messages_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widget_layout.insertWidget(1, loading_messages_label)

        self.widget_layout.setCurrentIndex(0)

    def get_current_chat_details(self):
        current_chat_idx = self.widget_layout.currentIndex()
        current_widget = self.widget_layout.widget(current_chat_idx)
        if isinstance(current_widget, ChatBubble):
            return current_widget.chat_details
        return None

    def show_chat(self, chat_data: dict | None):
        current_chat_idx = self.widget_layout.currentIndex()
        current_widget = self.widget_layout.widget(current_chat_idx)
        if isinstance(current_widget, ChatBubble):
            current_widget.display_chat()

        if chat_data is None: return

        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_details['chat_id'] == chat_data['chat_id'] and widget.chat_details['domain'] == chat_data['domain']:
                    self.widget_layout.setCurrentIndex(idx)
                    widget.last_access_time = time.time()
                    return

        self.__add_bubble(chat_data)

    def remove_chat(self, chat_id: str, chat_domain: str):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_details['chat_id'] == chat_id and widget.chat_details['domain'] == chat_domain:
                    self.widget_layout.removeWidget(widget)
                    return

    def set_current_user(self, user_data: dict):
        self.current_user = user_data
        self.widget_layout.setCurrentIndex(0)

    def update_member_management_visibility(self, user_data: dict):
        username = user_data['username']
        bubble_count = self.widget_layout.count()
        for idx in range(bubble_count):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                widget.chat_details_widget.update_button_visibility(username)

    def __add_bubble(self, chat_details: dict):
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

        current_time = time.time()
        new_bubble = ChatBubble(chat_details, current_time, self.current_user['username'])
        new_bubble.change_textbox_visibility.connect(self.change_textbox_visibility.emit)
        self.widget_layout.insertWidget(2, new_bubble)
        # at index 0 there is a special screen for when there are no chats selected
        # at index 1 there is a special screen for when messages are loading

        self.widget_layout.setCurrentIndex(1)
        new_bubble.chat.chat_messages.load_messages(50, None)
        self.widget_layout.setCurrentIndex(2)

    def add_message(self, chat_id: str, chat_domain:str, message: ChatMessage):
        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_details['chat_id'] == chat_id and widget.chat_details['domain'] == chat_domain:
                    widget.chat.chat_messages.add_message(message)

class ChatTextBox(QTextEdit):
    """
    TO DO:
        - implement send message (without requests initially)
    """
    send_message = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.init_height = 25
        self.max_height = 73

        self.setPlaceholderText("Start typing...")
        self.setFixedHeight(self.init_height)
        self.setMinimumWidth(50)

    def get_text(self):
        message = self.toPlainText().strip()
        if message:
            return message
        return None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_message.emit()
                self.clear()
                event.accept()
        else:
            super().keyPressEvent(event)

class MessageWindow(QWidget):
    send_message = pyqtSignal()
    upload_file = pyqtSignal()

    def __init__(self):
        super().__init__()

        upload_file_button = QPushButton()
        upload_file_button.setFixedSize(40, 40)
        upload_file_button.setIconSize(QSize(32, 32))
        upload_file_button.setIcon(QIcon("./Icons/upload_file_icon.png"))
        upload_file_button.clicked.connect(self.upload_file.emit)

        send_message_button = QPushButton()
        send_message_button.setFixedSize(40, 40)
        send_message_button.setIconSize(QSize(32, 32))
        send_message_button.setIcon(QIcon("./Icons/send_message_icon.png"))
        send_message_button.clicked.connect(self.emit_send_message)

        self.text_box = ChatTextBox()
        self.text_box.setMinimumWidth(200)
        self.text_box.textChanged.connect(self.__resize_text_box)
        self.text_box.send_message.connect(self.send_message.emit)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(upload_file_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.text_box)
        layout.addWidget(send_message_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setVisible(False) # initially not visible due to no chat being selected

    def set_visibility_bool(self, is_visible: bool):
        self.setVisible(is_visible)

    def set_visibility_dict(self, chat_data: dict | None):
        self.setVisible(chat_data is not None)

    def __resize_text_box(self):
        text_height = int(self.text_box.document().size().height())
        box_height = self.text_box.height()

        if text_height > self.text_box.max_height: return
        else:
            if text_height != box_height:
                self.text_box.setFixedHeight(text_height)

    def emit_send_message(self):
        self.send_message.emit()
        self.text_box.clear()

class ChatEnvironment(QWidget):
    """
    TO DO:
        - make chat bubbles disappear when exiting a group chat
    """

    def __init__(self):
        super().__init__()

        self.chat_history = ChatHistory()
        self.message_window = MessageWindow()
        self.message_window.send_message.connect(self.__send_message)
        self.message_window.upload_file.connect(self.__upload_file)

        self.chat_history.change_textbox_visibility.connect(self.message_window.set_visibility_bool)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_window, alignment=Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setMinimumWidth(RIGHT_PANE_MIN_WIDTH)

    def __send_message(self):
        text = self.message_window.text_box.get_text()
        if text is None: return
        current_user = self.chat_history.current_user

        chat_details = self.chat_history.get_current_chat_details()

        # MAKE REQUESTS

        message_id = "NEWLY_SENT_MESSAGE"
        sender = current_user['username']
        sender_icon_path = current_user['icon_path']
        was_edited = False
        is_reply = False
        reply_sender = None
        reply_sender_icon_path = None
        reply_snip = None
        local_time = time.localtime(time.time())
        formated_time = time.strftime("%H:%M:%S %d/%m/%Y", local_time)

        new_message = ChatMessage(
            message_id=message_id,
            sender=sender,
            sender_icon_path=sender_icon_path,
            was_edited=was_edited,
            is_reply=is_reply,
            reply_sender=reply_sender,
            reply_sender_icon_path=reply_sender_icon_path,
            reply_snip=reply_snip,
            timestamp=formated_time,
            text=text,
        )
        self.chat_history.add_message(chat_details['chat_id'], chat_details['domain'], new_message)

    def __upload_file(self):
        pass