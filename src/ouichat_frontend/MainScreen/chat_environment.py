from PyQt6.QtWidgets import (
    QPushButton, QVBoxLayout, QLabel, QStackedLayout, QWidget, QHBoxLayout,
    QTextEdit, QSizePolicy, QScrollArea, QLineEdit, QListWidget, QAbstractItemView, QListWidgetItem, QMenu
)

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QFontMetrics, QEnterEvent

import time

from ouichat_frontend.brain import Brain
from ouichat_frontend.socket_manager import message_args_to_dict

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
    """
    TO DO:
        - FINISH IMPLEMENTING CONTEXT MENU WITHOUT REQUESTS
    """
    remove_requested = pyqtSignal(str)

    def __init__(self, brain: Brain, chat_id: str, domain: str,
                 message_id: str, sender: str, sender_icon_path: str, was_edited: bool, is_reply: bool,
                 reply_sender: str | None, reply_sender_icon_path: str | None, reply_snip: str | None, timestamp: str,
                 text: str):
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
            replied_to_user_label.setText(f"{reply_sender}:")
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
        delete = object
        edit = object

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
            self.brain.set_reply(True, self.sender, self.sender_icon_path, self.text)
            # SHOW SOME MESSAGE WITH WHO YOU'RE REPLYING TO

        elif selected_action == edit:
            self.brain.set_edit(True, self.message_id, self.sender, self.sender_icon_path, self.text)
            self.brain.set_textbox_text.emit(self.text)

        elif selected_action == delete:
            print("delete")
            # MAKE REQUESTS AND REMOVE MESSAGE ONLY ON UPDATE FROM SERVER
            pass
    
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
        self.container.setLayout(self.container_layout)

        self.scroll_bar = self.verticalScrollBar()
        # IDK why it gives a PyUnresolvedReferences here, but we'll roll with it
        # noinspection PyUnresolvedReferences
        self.scroll_bar.rangeChanged.connect(self.__scroll_to_bottom)
        # noinspection PyUnresolvedReferences
        self.scroll_bar.valueChanged.connect(self.__height_changed)

        self.setWidget(self.container)

        self.load_old_messages(None)

    def __scroll_to_bottom(self, _: int, max_value: int):
        self.scroll_bar.setValue(max_value)

    def __height_changed(self, value: int):
        if value == 0:
            oldest_message = self.container_layout.itemAt(0)
            if oldest_message is None:
                self.load_old_messages(None)

    def load_old_messages(self, oldest_message_id: str | None):
        messages = self.brain.load_messages(self.chat_id, self.domain, oldest_message_id)
        self.add_messages(messages, 0)

    def add_messages(self, messages: list, starting_position: int = -1):
        # -1 --> ADD TO THE PEAK

        if starting_position == -1:
            position = self.container_layout.count()
        else:
            position = starting_position

        for message in messages:
            message_widget = ChatMessage(
                brain = self.brain,
                chat_id = message['chat_id'],
                domain = message['domain'],
                message_id = message['message_id'],
                sender = message['sender'],
                sender_icon_path = message['sender_icon_path'],
                was_edited = message['was_edited'],
                is_reply = message['is_reply'],
                reply_sender = message['reply_sender'],
                reply_sender_icon_path = message['reply_sender_icon_path'],
                reply_snip = message['reply_snip'],
                timestamp = message['timestamp'],
                text = message['text']
            )
            self.container_layout.insertWidget(position, message_widget)
            position += 1

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

        chat_users = self.brain.get_chat_users(self.chat_id, self.domain)
        self.initialize_members(chat_users)

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
        - make edit description tag appear only for admins
    """
    def __init__(self, brain: Brain, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain
        self.chat_id = chat_id
        self.domain = domain

        self.back_button = QPushButton()
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(30, 30)
        self.back_button.setIcon(QIcon("./Icons/close_icon.png"))
        self.back_button.clicked.connect(self.brain.chat_details_back_requested.emit)

        chat_icon = QPushButton()
        chat_icon.setIconSize(QSize(64, 64))
        chat_icon.setFixedSize(70, 70)
        chat_icon_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        chat_icon.setIcon(QIcon(chat_icon_path))

        chat_description_label = QLabel()
        chat_description_label.setText('Description:')

        chat_description_text = QLabel()
        chat_description = self.brain.get_chat_description(self.chat_id, self.domain)
        chat_description_text.setText(chat_description)
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

        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if chat_type == 'chatroom':
            self.chat_members_list = ChatMembersList(brain, chat_id, domain)

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

            current_user_username = self.brain.get_current_user_username()
            current_user_domain = self.brain.get_current_user_domain()
            self.update_button_visibility(current_user_username, current_user_domain)

            self.brain.current_user_changed.connect(self.update_button_visibility)

        self.setWidget(self.container)
        self.setWidgetResizable(True)

    def update_button_visibility(self, username: str, domain: str):

        chat_type = self.brain.get_chat_type(self.chat_id, self.domain)
        if chat_type == 'p2p': return

        if domain == self.domain:
            self.button_container.setVisible(self.brain.user_is_admin(self.chat_id, domain, username))
        else:
            self.button_container.setVisible(False)

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

        self.chat_details_button = QPushButton()
        self.chat_details_button.setText(f"{chat_id}")
        chat_icon_path = self.brain.get_chat_icon_path(self.chat_id, self.domain)
        self.chat_details_button.setIcon(QIcon(chat_icon_path))
        self.chat_details_button.setFixedHeight(25)
        self.chat_details_button.clicked.connect(self.brain.chat_chat_details_requested.emit)

        self.widget_layout.addWidget(self.chat_details_button)
        self.widget_layout.addWidget(self.chat_messages)

    def add_messages(self, messages: list[ChatMessage]):
        self.chat_messages.add_messages(messages)

class ChatBubble(QWidget):
    def __init__(self, brain: Brain, chat_id: str, domain: str):
        super().__init__()

        self.brain = brain

        self.chat_id = chat_id
        self.domain = domain
        self.last_access_time = time.time()

        self.chat = Chat(brain, chat_id, domain)
        self.brain.chat_chat_details_requested.connect(self.display_chat_details)

        self.chat_details_widget = ChatDetails(brain, chat_id, domain)
        self.brain.chat_details_back_requested.connect(self.display_chat)

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)
        self.setLayout(self.widget_layout)

        self.widget_layout.addWidget(self.chat)
        self.widget_layout.addWidget(self.chat_details_widget)
        self.widget_layout.setCurrentIndex(0)
    
    def display_chat_details(self):
        self.widget_layout.setCurrentIndex(1)
        self.brain.change_textbox_visibility.emit(False)

    def display_chat(self):
        self.widget_layout.setCurrentIndex(0)
        self.brain.change_textbox_visibility.emit(True)

    def add_messages(self, messages: list[ChatMessage]):
        self.chat.add_messages(messages)

class ChatHistory(QWidget):
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.max_bubbles = Brain.MAX_CHAT_BUBBLES + 1 # 1 screen for no chats

        self.widget_layout = QStackedLayout()
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(5)

        self.setLayout(self.widget_layout)

        no_chats_label = QLabel()
        no_chats_label.setText("Select a chat to vent to.")
        no_chats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widget_layout.insertWidget(0, no_chats_label)

        self.widget_layout.setCurrentIndex(0)

        self.brain.chat_selected.connect(self.show_chat)
        self.brain.current_user_changed.connect(self.handle_current_user_change)
        self.brain.add_new_messages.connect(self.add_messages)

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

        new_bubble = ChatBubble(self.brain, chat_id, domain)
        # at index 0 there is a special screen for when there are no chats selected
        self.widget_layout.insertWidget(1, new_bubble)
        self.widget_layout.setCurrentIndex(1)

    def add_messages(self, messages: list):
        sorted_messages = dict()
        for message in messages:
            if (message['chat_id'], message['domain']) not in sorted_messages.keys():
                sorted_messages[(message['chat_id'], message['domain'])] = [message]
            else :
                sorted_messages[(message['chat_id'], message['domain'])].append(message)

        for idx in range(self.widget_layout.count()):
            widget = self.widget_layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if (widget.chat_id, widget.domain) in sorted_messages.keys():
                    widget.add_messages(sorted_messages[(widget.chat_id, widget.domain)])

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
            self.context_snip_label.setText(f"{reply_details['reply_snip']}:")
            self.setVisible(True)
        elif edit_details['is_edit']:
            self.context_label.setText("Editing:")
            self.context_sender_icon.setPixmap(QPixmap(edit_details['sender_icon_path']).scaled(24, 24))
            self.context_user_label.setText(f"{edit_details['sender']}:")
            self.context_snip_label.setText(f"{edit_details['message_snip']}:")
            self.setVisible(True)
        else:
            self.setVisible(False)

class MessageWindow(QWidget):
    """
    TO DO:
        - implement send_message with requests
        - implement upload_file with requests
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        self.setLayout(top_layout)

        context_widget = MessageContext(brain)

        bottom_widget = QWidget()

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        bottom_widget.setLayout(bottom_layout)

        upload_file_button = QPushButton()
        upload_file_button.setFixedSize(40, 40)
        upload_file_button.setIconSize(QSize(32, 32))
        upload_file_button.setIcon(QIcon("./Icons/upload_file_icon.png"))
        upload_file_button.clicked.connect(self.upload_file)

        send_message_button = QPushButton()
        send_message_button.setFixedSize(40, 40)
        send_message_button.setIconSize(QSize(32, 32))
        send_message_button.setIcon(QIcon("./Icons/send_message_icon.png"))
        send_message_button.clicked.connect(self.send_message)

        self.text_box = ChatTextBox(brain)
        self.text_box.setMinimumWidth(200)

        bottom_layout.addWidget(upload_file_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        bottom_layout.addWidget(self.text_box)
        bottom_layout.addWidget(send_message_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        top_layout.addWidget(context_widget)
        top_layout.addWidget(bottom_widget)

        self.setVisible(False) # initially not visible due to no chat being selected

        self.brain.textbox_text_changed.connect(self.__resize_text_box)
        self.brain.send_message.connect(self.send_message)
        self.brain.change_textbox_visibility.connect(self.set_visibility_bool)
        self.brain.chat_selected.connect(self.set_visibility_str)

    def set_visibility_bool(self, is_visible: bool):
        self.setVisible(is_visible)

    def set_visibility_str(self, chat_id: str, domain: str):
        self.setVisible(chat_id != "" and domain != "")

    def __resize_text_box(self):
        text_height = int(self.text_box.document().size().height())
        box_height = self.text_box.height()

        if text_height > self.text_box.max_height: return
        else:
            if text_height != box_height:
                self.text_box.setFixedHeight(text_height)

    def send_message(self):

        # SEND MESSAGE REQUEST
        # ON RESPONSE = OK, CLEAR THE TEXTBOX AND SET REPLY DETAILS AND EDIT DETAILS TO NONE

        text = self.text_box.toPlainText().strip()
        if text == "": return

        current_chat_id = self.brain.get_current_chat_id()
        current_chat_domain = self.brain.get_current_chat_domain()
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        current_user_icon_path = self.brain.get_current_user_icon()

        if current_chat_domain != current_user_domain: return

        edit_details = self.brain.get_edit_details()

        if edit_details['is_edit']:
            # process different requests
            self.brain.set_edit(False)
            self.brain.message_context_changed.emit()

        reply_details = self.brain.get_reply_details()

        # MAKE REQUEST
        # ONLY ADD AND DISPLAY MESSAGE ON SERVER UPDATE

        local_time = time.localtime(time.time())
        formated_time = time.strftime("%H:%M:%S %d/%m/%Y", local_time)

        message = message_args_to_dict(
            chat_id = current_chat_id,
            domain = current_chat_domain,
            message_id = "NEWLY_SENT_MESSAGE",
            sender = current_user_username,
            sender_icon_path = current_user_icon_path,
            was_edited = False,
            is_reply = reply_details['is_reply'],
            reply_sender = reply_details['reply_sender'],
            reply_sender_icon_path = reply_details['reply_sender_icon_path'],
            reply_snip = reply_details['reply_snip'],
            timestamp = formated_time,
            text = text
        )

        self.brain.add_new_messages.emit([message])
        self.brain.set_edit(False)
        self.brain.set_reply(False)
        self.brain.message_context_changed.emit()
        self.text_box.clear()

    def upload_file(self):
        pass

class ChatEnvironment(QWidget):
    """
    TO DO:
        - verify and refine implementation for p2p chats
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain

        self.chat_history = ChatHistory(brain)
        self.message_window = MessageWindow(brain)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.message_window, alignment=Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)
        self.setMinimumWidth(RIGHT_PANE_MIN_WIDTH)