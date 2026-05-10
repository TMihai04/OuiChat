from PyQt6.QtCore import QObject, pyqtSignal

import time

from socket_manager import SocketManager

def get_users_username(users: list):
    return list(map(lambda user: user['username'], users))

def get_user_details_from_chat_users(username: str, users: list):
    for user in users:
        if user['username'] == username:
            return user
    return None

class Brain(QObject):
    chat_added = pyqtSignal(dict)
    chat_removed = pyqtSignal(dict)

    user_added = pyqtSignal(dict)
    user_removed = pyqtSignal(dict)
    current_user_changed = pyqtSignal(str, str)
    chat_selected = pyqtSignal(str, str)
    change_textbox_visibility = pyqtSignal(bool)

    chat_updated = pyqtSignal(str, str)

    last_seen_time_updated = pyqtSignal(str, str)

    add_new_messages = pyqtSignal(dict)
    set_textbox_text = pyqtSignal(str)
    remove_messages = pyqtSignal(dict)

    message_context_changed = pyqtSignal()

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
        self.sender = None
        self.sender_icon_path = None
        self.message_snip = None

        self.chat_selected.connect(self.set_current_chat)
        self.socket_manager.chat_updated.connect(self.update_chat)

    def get_last_message_timestamp(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if chat is None: return None

        chat = chat[0]
        return chat['last_message_timestamp']

    def set_last_message_timestamp(self, chat_id: str, domain:str, timestamp: float):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if chat is None: return

        chat = chat[0]
        chat['last_message_timestamp'] = timestamp
        self.last_seen_time_updated.emit(chat_id, domain)

    def set_current_user_last_seen_time(self, chat_id: str, domain: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        if current_user_domain != domain: return

        chat_users = self.get_chat_users(chat_id, domain)
        for user in chat_users:
            if user['username'] == current_user_username:
                user['last_seen_time'] = time.time()
                return

    def get_current_user_last_seen_time(self, chat_id: str, domain: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        if current_user_domain != domain: return None

        chat_users = self.get_chat_users(chat_id, domain)
        for user in chat_users:
            if user['username'] == current_user_username:
                return user['last_seen_time']

        return None

    def update_chat(self, chat_details: dict):
        self.remove_chat_by_id_and_domain(chat_details['chat_id'], chat_details['domain'])
        self.add_chats([chat_details])

        if self.current_chat is None or \
                (self.current_chat['chat_id'] == chat_details['chat_id'] and self.current_chat['domain'] == chat_details['domain']):
            self.current_chat = chat_details

        current_user_domain = self.get_current_user_domain()
        if current_user_domain == chat_details['domain']:
            self.chat_updated.emit(chat_details['chat_id'], chat_details['domain'])

    def load_messages(self, chat_id: str, domain: str, oldest_message_id: str = None, message_nr: int = 50):
        return self.socket_manager.request_messages(chat_id, domain, oldest_message_id, message_nr)

    def set_edit(self, is_edit: bool, message_id: str = None, sender: str = None, sender_icon_path: str = None, message_snip: str = None):
        if self.is_edit and not is_edit:
            self.set_textbox_text.emit("")
        self.is_edit = is_edit
        self.edit_message_id = message_id
        self.sender = sender
        self.sender_icon_path = sender_icon_path
        self.message_snip = message_snip
        if is_edit:
            self.message_context_changed.emit()
            self.set_reply(False)

    def get_edit_details(self):
        return {
            "is_edit": self.is_edit,
            "edit_message_id": self.edit_message_id,
            "sender": self.sender,
            "sender_icon_path": self.sender_icon_path,
            "message_snip": self.message_snip
        }

    def set_reply(self, is_reply: bool, reply_user: str = None, reply_user_icon_path: str = None, reply_snip: str = None):
        self.is_reply = is_reply
        self.reply_user = reply_user
        self.reply_user_icon_path = reply_user_icon_path
        self.reply_snip = reply_snip
        if is_reply:
            self.message_context_changed.emit()
            self.set_edit(False)

    def get_reply_details(self):
        return {
            "is_reply": self.is_reply,
            "reply_sender": self.reply_user,
            "reply_sender_icon_path": self.reply_user_icon_path,
            "reply_snip": self.reply_snip
        }

    def get_current_user(self):
        return self.current_user

    def set_current_user(self, username: str, domain: str):
        user = self.find_users({
            "username": username,
            "domain": domain
        })
        if user:
            user = user[0]
            self.current_user = user
            self.current_user_changed.emit(user['username'], user['domain'])

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
        })
        if user:
            user = user[0]
            self.remove_user(user)

    def set_current_chat(self, chat_id: str, domain: str):
        if chat_id == "" and domain == "":
            self.current_chat = None
            return

        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })
        if chat:
            chat = chat[0]
            self.current_chat = chat

    def get_chats(self):
        ret = [
            {
                "chat_id": chat['chat_id'],
                "domain": chat['domain'],
            } for chat in self.chats_list
        ]
        return ret

    def get_chat_user_usernames(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if chat:
            chat = chat[0]
            return list(map(lambda user: user['username'], chat['users']))
        return None

    def get_current_chat_id(self):
        if self.current_chat is None:
            return None
        return self.current_chat['chat_id']

    def get_current_chat_domain(self):
        if self.current_chat is None:
            return None
        return self.current_chat['domain']

    def get_current_chat_setting(self):
        if self.current_chat is None:
            return None
        return self.current_chat['chat_setting']

    def get_chat_type(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })
        if chat:
            chat = chat[0]
            return chat['chat_type']
        return None

    def get_chat_display_name(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if not chat: return None
        chat = chat[0]

        if chat['chat_type'] == "chatroom":
            return chat['display_name']
        else:
            current_username = self.get_current_user_username()
            usernames = get_users_username(chat['users'])
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_data = get_user_details_from_chat_users(other_username, chat['users'])
            return other_user_data['username']

    def get_chat_description(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if not chat: return None
        chat = chat[0]

        if chat['chat_type'] == "chatroom":
            return chat['description']
        else:
            current_username = self.get_current_user_username()
            usernames = get_users_username(chat['users'])
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_data = get_user_details_from_chat_users(other_username, chat['users'])
            return other_user_data['description']

    def get_chat_icon_path(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if not chat: return None
        chat = chat[0]

        if chat['chat_type'] == "chatroom":
            return chat['icon_path']
        else:
            current_username = self.get_current_user_username()
            usernames = get_users_username(chat['users'])
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_data = get_user_details_from_chat_users(other_username, chat['users'])
            return other_user_data['icon_path']

    def get_chat_users(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })
        if chat:
            chat = chat[0]
            return chat['users']
        return None

    def user_is_admin(self, chat_id: str, domain: str, username: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if not chat: return False
        chat = chat[0]

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

    def remove_chat_by_id_and_domain(self, chat_id: str, domain: str):
        chat = self.find_chats({
            "chat_id": chat_id,
            "domain": domain
        })

        if chat:
            chat = chat[0]
            self.remove_chat(chat)