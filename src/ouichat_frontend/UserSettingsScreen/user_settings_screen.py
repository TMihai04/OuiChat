from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QTextOption
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QTextEdit, QSizePolicy

from PIL import Image
import os
import time

from ouichat_frontend.brain import Brain
from ouichat_frontend.dialogs import UserDetailsEditDialog

class UserSettingsScreen(QWidget):
    """
    TO DO:
        - add 'Log out' button
        - implement logout logic (with user removals, chat removals, cleanup, etc.)
    """
    def __init__(self, brain: Brain):
        super().__init__()

        self.brain = brain
        self.brain.user_updated.connect(self.update_user_details)
        self.brain.current_user_changed.connect(self.update_user_details)

        self.text_edit_dialog = UserDetailsEditDialog(brain)

        screen_layout = QVBoxLayout()
        screen_layout.setContentsMargins(10, 10, 10, 10)
        screen_layout.setSpacing(5)
        self.setLayout(screen_layout)

        self.back_button = QPushButton()
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setFixedSize(30, 30)
        self.back_button.setIcon(QIcon("./Icons/close_icon.png"))
        self.back_button.clicked.connect(self.brain.main_window_comms_requested.emit)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.user_icon = QPushButton()
        self.user_icon.setIconSize(QSize(64, 64))
        self.user_icon.setFixedSize(64, 64)
        user_icon_path = self.brain.get_current_user_icon()
        self.user_icon.setIcon(QIcon(user_icon_path))
        self.user_icon.clicked.connect(self.change_user_icon)
        self.user_icon.setStyleSheet("background: transparent; border: none; ")

        self.username = QLabel()
        username = self.brain.get_current_user_username()
        self.username.setText(username)
        self.username.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        user_description_label = QLabel()
        user_description_label.setText('Description:')

        self.user_description_text = QTextEdit()
        user_description = self.brain.get_current_user_description()
        self.user_description_text.setPlainText(user_description)
        self.user_description_text.setReadOnly(True)
        self.user_description_text.setFrameShape(QTextEdit.Shape.NoFrame)
        self.user_description_text.setStyleSheet("background: transparent;")
        self.user_description_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.user_description_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.user_description_text.document().setDocumentMargin(0)
        self.user_description_text.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.change_user_description_button = QPushButton()
        self.change_user_description_button.setIcon(QIcon("./Icons/edit_icon.png"))
        self.change_user_description_button.setFixedSize(20, 20)
        self.change_user_description_button.setIconSize(QSize(16, 16))
        self.change_user_description_button.clicked.connect(self.edit_description)
        self.change_user_description_button.setCursor(Qt.CursorShape.PointingHandCursor)

        user_description = QWidget()
        user_description_layout = QVBoxLayout()
        user_description_layout.setContentsMargins(5, 0, 5, 5)
        user_description_layout.setSpacing(5)
        user_description.setLayout(user_description_layout)

        user_description_layout.addWidget(user_description_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        user_description_layout.addWidget(self.user_description_text, alignment=Qt.AlignmentFlag.AlignTop)
        user_description_layout.addWidget(self.change_user_description_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        screen_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        screen_layout.addWidget(self.user_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        screen_layout.addWidget(self.username, alignment=Qt.AlignmentFlag.AlignCenter)
        screen_layout.addWidget(user_description)
        screen_layout.addStretch()

    def update_user_details(self, username: str, domain: str):
        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()
        if username != current_user_username or domain != current_user_domain: return

        current_user_icon = self.brain.get_current_user_icon()
        self.user_icon.setIcon(QIcon(current_user_icon))

        self.username.setText(current_user_username)

        current_user_description = self.brain.get_current_user_description()
        self.user_description_text.setPlainText(current_user_description)
        self.__resize_description_box()

    def __resize_description_box(self):
        text_height = int(self.user_description_text.document().size().height()) + 2
        box_height = self.user_description_text.height()
        if text_height != box_height:
            self.user_description_text.setFixedHeight(text_height)

    def showEvent(self, event):
        super().showEvent(event)
        self.__resize_description_box()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__resize_description_box()

    def edit_description(self):
        if self.text_edit_dialog.isVisible():
            self.text_edit_dialog.raise_()
            self.text_edit_dialog.activateWindow()
            return

        current_user_description = self.brain.get_current_user_description()
        self.text_edit_dialog.set_text(current_user_description)
        self.text_edit_dialog.exec()

    def change_user_icon(self):
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

        current_user_username = self.brain.get_current_user_username()
        current_user_domain = self.brain.get_current_user_domain()

        save_dir = "./Cache/UserIcons"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        new_file_path = f"{save_dir}/{current_user_username}_{current_user_domain}_{int(time.time())}.png"

        resized_copy.save(new_file_path, "PNG")

        old_file_path = self.brain.get_current_user_icon()

        self.brain.set_current_user_icon_path(new_file_path)

        if old_file_path != "./Icons/default_user_icon.png":
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError:
                    pass