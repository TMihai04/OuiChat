from PyQt6.QtCore import QObject, pyqtSignal

class Brain(QObject):
    chat_added = pyqtSignal(dict)
    chat_removed = pyqtSignal(dict)

    user_added = pyqtSignal(dict)
    user_removed = pyqtSignal(dict)
    interaction_panel_current_user_changed = pyqtSignal(dict)

    main_window_settings_requested = pyqtSignal()
    main_window_comms_requested = pyqtSignal()
    main_window_user_settings_requested = pyqtSignal()

    interaction_panel_chat_selected = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()

        self.users_list = []
        self.chats_list = []

        self.current_user = None

    def get_current_user(self):
        return self.current_user

    def get_current_user_username(self):
        return self.current_user["username"]

    def get_current_user_domain(self):
        return self.current_user["domain"]

    def get_current_user_icon(self):
        return self.current_user["icon_path"]

    def add_user(self, user_data: dict):
        self.users_list.append(user_data)
        self.current_user = user_data
        self.interaction_panel_current_user_changed.emit(user_data)

    def remove_user(self, user_data: dict):
        self.users_list.remove(user_data)

    def find_users(self, key_val_pairs: dict):
        found_users = []
        for user in self.users_list:
            for key in key_val_pairs.keys():
                if user[key] != key_val_pairs[key]:
                    break
            found_users.append(user)
        return found_users

    def remove_user_by_username_and_domain(self, username: str, domain: str):
        user = self.find_users({
            "username": username,
            "domain": domain
        })[0]
        self.remove_user(user)

    def get_chat_ids(self):
        return map(lambda chat: chat['chat_id'], self.chats_list)

    def get_chat_icons(self):
        return map(lambda chat: chat['icon_pah'], self.chats_list)

    def get_chat_domains(self):
        return map(lambda chat: chat['domain'], self.chats_list)

    def get_chat_user_usernames(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return map(lambda user: user['username'], chat['users'])

    def get_chat_type(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return chat['chat_type']

    def user_is_admin(self, chat_id: str, domain: str, username: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        for user in chat['users']:
            if user['username'] == username:
                return user['is_admin']
        return False

    def add_chat(self, chat_data: dict):
        if not self.chat_exists(chat_data):
            self.chats_list.append(chat_data)

    def remove_chat(self, chat_data: dict):
        self.chats_list.remove(chat_data)

    def chat_exists(self, chat_data: dict):
        for chat in self.chats_list:
            if chat["chat_id"] == chat_data["chat_id"] and chat["domain"] == chat_data["domain"]:
                return True
        return False

    def find_chats(self, key_val_pairs: dict):
        found_chats = []
        for chat in self.chats_list:
            for key in key_val_pairs.keys():
                if chat[key] != key_val_pairs[key]:
                    break
            found_chats.append(chat)
        return found_chats

    def remove_chat_by_username_and_domain(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        self.remove_chat(chat)