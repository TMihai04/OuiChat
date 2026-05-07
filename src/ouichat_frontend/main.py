from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QStackedLayout, QWidget
)

from SettingsScreen.settings_screen import SettingsScreen
from login_dialog import LogInDialog
from MainScreen.main_screen import MainScreen
from ouichat_frontend.brain import Brain

class MainWindow(QMainWindow):
    def __init__(self, brain: Brain, login_dialog):
        super().__init__()

        self.brain = brain

        self.setWindowTitle("OuiChat")

        self.main_layout = QStackedLayout() # ADD ALL THE OTHER TABS HERE (SETTINGS, ETC.)

        main_screen_widget = MainScreen(brain, login_dialog)
        self.brain.main_window_settings_requested.connect(self.go_to_settings)

        settings_screen_widget = SettingsScreen(brain)
        self.brain.main_window_comms_requested.connect(self.go_to_comms)

        # user_settings_widget = UserSettings()
        # self.brain.main_window_user_settings_requested.connect(self.go_to_user_settings)

        self.main_layout.addWidget(main_screen_widget)
        self.main_layout.addWidget(settings_screen_widget)

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

    def go_to_comms(self):
        self.main_layout.setCurrentIndex(0)

    def go_to_settings(self):
        self.main_layout.setCurrentIndex(1)

    def go_to_user_settings(self):
        self.main_layout.setCurrentIndex(2)


if __name__ == "__main__":
    app = QApplication([])
    app_brain = Brain()
    login = LogInDialog(app_brain)

    if login.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow(app_brain, login)
        main_window.show()
        app.exec()
    else:
        pass