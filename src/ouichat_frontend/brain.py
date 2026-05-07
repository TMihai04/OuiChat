from PyQt6.QtCore import QObject, pyqtSignal

from .MainScreen.chat_environment import ChatMessage
from socket_manager import SocketManager

class Brain(QObject):
    chat_added = pyqtSignal(dict)
    chat_removed = pyqtSignal(dict)

    user_added = pyqtSignal(dict)
    user_removed = pyqtSignal(dict)
    current_user_changed = pyqtSignal(str, str)
    chat_selected = pyqtSignal(str, str)
    change_textbox_visibility = pyqtSignal(bool)
    textbox_text_changed = pyqtSignal(str)

    chat_details_back_requested = pyqtSignal()
    chat_chat_details_requested = pyqtSignal()

    add_new_messages = pyqtSignal(str, str, list[ChatMessage])

    send_message = pyqtSignal()

    main_window_settings_requested = pyqtSignal()
    main_window_comms_requested = pyqtSignal()
    main_window_user_settings_requested = pyqtSignal()

    MAX_CHAT_BUBBLES = 15

    def __init__(self):
        super().__init__()

        self.socket_manager = SocketManager()

        self.users_list = []
        self.chats_list = []

        self.current_user = None
        self.current_chat = None

        self.is_reply = False
        self.reply_user = None
        self.reply_user_icon_path = None
        self.reply_snip = None

        self.is_edit = False
        self.edit_message_id = None

        self.chat_selected.connect(self.set_current_chat)

    def load_messages(self, chat_id: str, domain: str, oldest_message_id: str = None, message_nr: int = 50):
        messages = self.socket_manager.request_messages(chat_id, domain, oldest_message_id, message_nr)
        for message in messages:
            message.brain = self
        return messages

    def set_edit(self, is_edit: bool, message_id: str = None):
        self.is_edit = is_edit
        self.edit_message_id = message_id

    def get_edit_details(self):
        return {
            "is_edit": self.is_edit,
            "edit_message_id": self.edit_message_id,
        }

    def set_reply(self, is_reply: bool, reply_user: str = None, reply_user_icon_path: str = None, reply_snip: str = None):
        self.is_reply = is_reply
        self.reply_user = reply_user
        self.reply_user_icon_path = reply_user_icon_path
        self.reply_snip = reply_snip

    def get_reply_details(self):
        return {
            "is_reply": self.is_reply,
            "reply_user": self.reply_user,
            "reply_user_icon_path": self.reply_user_icon_path,
            "reply_snip": self.reply_snip
        }

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
        self.current_user_changed.emit(user_data['username'], user_data['domain'])

        chats = self.socket_manager.request_chats(user_data['username'], user_data['domain'])
        self.add_chats(chats)

    def remove_user(self, user_data: dict):
        self.users_list.remove(user_data)

    def find_users(self, key_val_pairs: dict):
        found_users = []
        for user in self.users_list:
            for key in key_val_pairs.keys():
                if user[key] != key_val_pairs[key]:
                    break
            else:
                found_users.append(user)
        return found_users

    def remove_user_by_username_and_domain(self, username: str, domain: str):
        user = self.find_users({
            "username": username,
            "domain": domain
        })[0]
        self.remove_user(user)

    def set_current_chat(self, chat_id: str, domain: str):
        if chat_id == "" and domain == "":
            self.current_chat = None
            return

        self.current_chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]

    def get_chat_ids(self):
        return list(map(lambda chat: chat['chat_id'], self.chats_list))

    def get_chat_icons(self):
        return list(map(lambda chat: chat['icon_path'], self.chats_list))

    def get_chat_domains(self):
        return list(map(lambda chat: chat['domain'], self.chats_list))

    def get_chat_user_usernames(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return list(map(lambda user: user['username'], chat['users']))

    def get_current_chat_id(self):
        return self.current_chat['chat_id']

    def get_current_chat_domain(self):
        return self.current_chat['domain']

    def get_chat_icon_path(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return chat['icon_path']

    def get_chat_type(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return chat['chat_type']

    def get_chat_description(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return chat['chat_description']

    def get_chat_users(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        return chat['users']

    def user_is_admin(self, chat_id: str, domain: str, username: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        for user in chat['users']:
            if user['username'] == username:
                return user['is_admin']
        return False

    def add_chats(self, chat_data: list[dict]):
        for chat in chat_data:
            if not self.chat_exists(chat):
                self.chats_list.append(chat)

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
            else:
                found_chats.append(chat)
        return found_chats

    def remove_chat_by_username_and_domain(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })[0]
        self.remove_chat(chat)