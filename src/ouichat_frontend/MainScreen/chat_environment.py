from PyQt6.QtWidgets import (
    QPushButton, QVBoxLayout, QLabel, QStackedLayout, QWidget, QHBoxLayout,
    QTextEdit, QSizePolicy, QScrollArea, QBoxLayout
)

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFontMetrics

import time

RIGHT_PANE_MIN_WIDTH = 310

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
        - implement context menu for messages (reply, edit, delete)
        - add spaces between messages
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

    def send_message(self):
        # SEND MESSAGE TO SERVER
        pass

class ChatHistory(QWidget):
    """
    TO DO:
        - finish implementing chat history
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

    def show_chat(self, chat_data: dict | None):
        if chat_data is None:
            self.layout.setCurrentIndex(0)
            return

        for idx in range(self.layout.count()):
            widget = self.layout.widget(idx)
            if isinstance(widget, ChatBubble):
                if widget.chat_id == chat_data['chat_id'] and widget.domain == chat_data['domain']:
                    self.layout.setCurrentIndex(idx)
                    widget.last_access_time = time.time()
                    return

        self.__add_bubble(chat_data['chat_id'], chat_data['domain'])

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
    """
    TO DO:
        - implement send message (without requests initially)
    """
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

    def set_visibility(self, chat_data: dict | None):
        if chat_data is not None:
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

class ChatEnvironment(QWidget):
    """
    TO DO:
        - make stacked widgets dynamically update when exiting a group chat
        - on the top add a button widget with the name of the chat to see its members and admins
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