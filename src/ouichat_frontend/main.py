from PyQt6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QStackedLayout, QWidget
)

from SettingsScreen.settings_screen import SettingsScreen
from login_dialog import LogInDialog
from MainScreen.main_screen import MainScreen

class MainWindow(QMainWindow):
    def __init__(self, initial_user_data: dict, login_dialog):
        super().__init__()

        self.setWindowTitle("OuiChat")

        self.main_layout = QStackedLayout() # ADD ALL THE OTHER TABS HERE (SETTINGS, ETC.)

        main_screen_widget = MainScreen(initial_user_data, login_dialog)
        main_screen_widget.settings_requested.connect(self.go_to_settings)

        settings_screen_widget = SettingsScreen()
        settings_screen_widget.back_requested.connect(self.go_to_main)

        self.main_layout.addWidget(main_screen_widget)
        self.main_layout.addWidget(settings_screen_widget)

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

    def go_to_main(self):
        self.main_layout.setCurrentIndex(0)

    def go_to_settings(self):
        self.main_layout.setCurrentIndex(1)


if __name__ == "__main__":
    app = QApplication([])
    login = LogInDialog()

    if login.exec() == QDialog.DialogCode.Accepted:
        user_data = {
            "username": login.user_data['username'],
            "domain": login.user_data['domain'],
            "icon_path": login.user_data['icon_path'],
            "request_token": login.user_data['token'],
            "refresh_token": "REFRESH_TOKEN " + login.user_data['token'],
        }

        main_window = MainWindow(user_data, login)
        main_window.show()
        app.exec()
    else:
        pass