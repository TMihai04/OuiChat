from PyQt6.QtCore import QObject, pyqtSignal

import time

from PyQt6.QtWidgets import QDialog

from socket_manager import SocketManager

class Brain(QObject):
    """
    TO DO:
        - on websocket update (a user blocked the current user), delete the user entry from the users list
    """

    chats_added = pyqtSignal(list)
    chat_removed = pyqtSignal(dict)

    remove_chats = pyqtSignal(dict)
    remove_domain = pyqtSignal(str)
    logout_user = pyqtSignal(str, str)

    select_previous_user = pyqtSignal()
    current_user_changed = pyqtSignal(str, str)
    user_updated = pyqtSignal(str, str)
    chat_selected = pyqtSignal(str, str)
    select_chat = pyqtSignal(str, str)
    change_textbox_visibility = pyqtSignal(bool)

    added_members_to_chat = pyqtSignal(str, str, list)
    removed_members_from_chat = pyqtSignal(str, str, list)

    chat_updated = pyqtSignal(str, str)

    last_seen_time_updated = pyqtSignal(str, str)

    add_new_messages = pyqtSignal(dict)
    timestamps_updated = pyqtSignal()

    set_textbox_text = pyqtSignal(str)
    remove_messages = pyqtSignal(dict)
    message_edited = pyqtSignal(str, str, str, str)

    message_context_changed = pyqtSignal()
    upload_context_files_added = pyqtSignal(list)
    upload_context_files_removed = pyqtSignal(list)

    send_message = pyqtSignal()
    clear_staged_files = pyqtSignal()
    clear_message_context = pyqtSignal()

    main_window_settings_requested = pyqtSignal()
    main_window_comms_requested = pyqtSignal()
    main_window_user_settings_requested = pyqtSignal()

    MAX_CHAT_BUBBLES = 15

    def __init__(self, refresh_login_dialog_class: type, error_dialog):
        super().__init__()

        self.socket_manager = SocketManager()
        self.refresh_login_dialog = refresh_login_dialog_class(self)
        self.error_dialog = error_dialog

        self.users_list = []
        self.chats_list = dict() # key: domain | value: list of chats
        self.domain_users_list = dict() # key: domain | value: list of users

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
        self.add_new_messages.connect(self.update_timestamps)

    def logout_current_user(self):
        """
        TO DO:
            - send state to server after setting user last seen time
        """
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        self.set_current_user_last_seen_time_current_chat()
        self.main_window_comms_requested.emit()
        self.logout_user.emit(current_user_username, current_user_domain)

        other_logged_users_in_current_domain = []
        for user in self.users_list:
            if user['domain'] == current_user_domain:
                other_logged_users_in_current_domain.append(user['username'])

        if not other_logged_users_in_current_domain:
            self.remove_domain.emit(current_user_domain)
            del self.chats_list[current_user_domain]
            del self.domain_users_list[current_user_domain]
        else:
            chats_to_remove = dict()
            chats_to_remove['domain'] = current_user_domain
            chats_to_remove['chat_ids'] = []
            for idx in reversed(range(len(self.chats_list[current_user_domain]))):
                chat = self.chats_list[current_user_domain][idx]
                safe_to_remove = True
                for other_user in other_logged_users_in_current_domain:
                    if other_user in list(map(lambda chat_user: chat_user['username'], chat['users'])):
                        safe_to_remove = False
                        break
                if safe_to_remove:
                    chats_to_remove['chat_ids'].append(chat['chat_id'])
                    del self.chats_list[current_user_domain][idx]

            self.remove_chats.emit(chats_to_remove)

        for idx in range(len(self.users_list)):
            if self.users_list[idx]['username'] == current_user_username and self.users_list[idx]['domain'] == current_user_domain:
                del self.users_list[idx]
                break

        self.select_previous_user.emit()

    def refresh_tokens(self):
        current_user_domain = self.get_current_user_domain()
        current_user_refresh_token = self.get_current_user_refresh_token()

        success, resp_data = self.socket_manager.request_refresh_tokens(current_user_domain, current_user_refresh_token)
        if not success:
            response = self.refresh_login_dialog.exec()
            return response == QDialog.DialogCode.Accepted

        resp_data = resp_data.get('field')

        self.set_current_user_access_token(resp_data['access_token'])
        self.set_current_user_refresh_token(resp_data['refresh_token'])
        return True

    def get_current_user_profile(self, domain: str | None, access_token: str | None):
        if not domain:
            req_domain = self.get_current_user_domain()
        else:
            req_domain = domain

        if not access_token:
            req_access_token = self.get_current_user_access_token()
        else:
            req_access_token = access_token

        success, resp_data = self.socket_manager.request_get_current_user_profile(req_domain, req_access_token)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session"
            else: return self.get_current_user_profile(req_domain, req_access_token)
        return success, resp_data.get('field')

    def register_login_user(self, domain: str | None, username: str | None, password: str, login: bool):
        req_domain = domain if domain else self.get_current_user_domain()
        req_username = username if username else self.get_current_user_username()
        success, resp_data = self.socket_manager.request_register_login(req_domain, req_username, password, login)
        return success, resp_data.get('field')

    def set_current_user_refresh_token(self, refresh_token: str):
        current_user = self.get_current_user()
        if not current_user:return
        current_user['refresh_token'] = refresh_token

    def set_current_user_access_token(self, access_token: str):
        current_user = self.get_current_user()
        if not current_user:return
        current_user['access_token'] = access_token

    def get_current_user_refresh_token(self):
        current_user = self.get_current_user()
        if not current_user: return ""
        return current_user['refresh_token']

    def get_current_user_access_token(self):
        current_user = self.get_current_user()
        if not current_user: return ""
        return current_user['access_token']

    def user_is_in_chat(self, chat_id: str, domain: str, username):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False

        users = chat['users']
        for user in users:
            if user['username'] == username:
                return True

        return False

    def get_logged_users(self):
        return [
            {
                "username": logged_user['username'],
                "domain": logged_user['domain'],
            } for logged_user in self.users_list
        ]

    def get_current_user_description(self):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()

        return self.get_user_description(current_user_username, current_user_domain)

    def set_current_user_description(self, description: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.socket_manager.request_change_user_description(current_user_domain, current_user_access_token, description)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session"
                else:
                    return self.set_current_user_description(description)
            else:
                return False, resp_data.get('field')

        # REMOVE UNNEEDED BITS OF THE METHOD ONCE THE WEBSOCKET UPDATES ARE IMPLEMENTED
        # CHANGE DESCRIPTION ONLY ON WEBSOCKET UPDATE
        user = self.get_user_details(current_user_username, current_user_domain)
        if not user: return False, "Could not get current user details"

        user['profile']['status'] = description
        self.user_updated.emit(current_user_username, current_user_domain)
        return True, None

    def set_current_user_icon_path(self, icon_path: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()

        user = self.get_user_details(current_user_username, current_user_domain)
        if not user: return

        user['profile']['picture_id'] = icon_path
        self.user_updated.emit(current_user_username, current_user_domain)

    def upload_files(self, file_list: list):
        success, resp_data = self.socket_manager.request_upload_files(file_list)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session"
            else: return self.upload_files(file_list)
        return success, resp_data.get('field') # MATCH RETURN STATEMENT HERE WITH THE RETURNED DATA FROM socket_manager

    def download_files(self, ids: list):
        success, resp_data = self.socket_manager.request_download_files(ids)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session"
            else:
                return self.download_files(ids)

        return True, None

    def add_users_to_chat(self, chat_id: str, domain: str, users: list):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False, "Could NOT find chatroom!"

        # PASS REQUEST THROUGH SERVER AND UPDATE LIST ONLY ON SERVER UPDATE
        chat['users'].extend([{
            "username": user,
            "is_admin": False,
            "last_seen_time": 0
        } for user in users])

        self.added_members_to_chat.emit(chat_id, domain, users)
        return True, None

    def create_chatroom(self, users: list):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()

        users.append(current_user_username)
        success, resp_data = self.socket_manager.request_create_chatroom(current_user_domain, current_user_username, users)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session!"
            else: return self.create_chatroom(users)

        resp_data = resp_data.get('field')
        if not resp_data: return False, "Could NOT create chatroom!"

        self.add_chats([resp_data])
        # MATCH RETURN VALUES WITH THE VALUES FROM socket_manager
        return True, (resp_data['chat_id'], resp_data['domain'])

    def set_chat_icon_path(self, chat_id: str, domain: str, icon_path: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return
        chat['icon_path'] = icon_path

        current_user_domain = self.get_current_user_domain()
        if domain == current_user_domain:
            self.chat_updated.emit(chat_id, domain)

    def set_chat_display_name(self, chat_id: str, domain: str, display_name: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return
        chat['display_name'] = display_name

        current_user_domain = self.get_current_user_domain()
        if domain == current_user_domain:
            self.chat_updated.emit(chat_id, domain)

    def set_chat_description(self, chat_id: str, domain: str, description: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return
        chat['description'] = description

        current_user_domain = self.get_current_user_domain()
        if domain == current_user_domain:
            self.chat_updated.emit(chat_id, domain)

    def user_is_blocked(self, username: str):
        return username in self.current_user['blacklist']

    def user_is_reachable(self, username: str):
        current_user_domain = self.get_current_user_domain()
        users = self.domain_users_list.get(current_user_domain, None)
        if users is None: return False

        usernames = [user['username'] for user in users]
        return username in usernames

    def block_user(self, username: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.socket_manager.request_block_unblock_user(current_user_domain, current_user_access_token, username, True)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.block_user(username)
            else:
                return False, resp_data.get('field')

        # REMOVE UNNEEDED BITS OF THE METHOD ONCE THE WEBSOCKET UPDATES ARE IMPLEMENTED
        # CHANGE BLACKLIST ONLY ON WEBSOCKET UPDATE
        self.current_user['blacklist'].append(username)

        # SEND REQUEST TO SERVER TO MAKE CHAT READ-ONLY
        chat_id = self.p2p_chat_exists(current_user_username, username, current_user_domain)
        if chat_id:
            chat = self.find_chat(chat_id, current_user_domain)
            chat['chat_setting'] = 'ro'

        return True, None

    def unblock_user(self, username: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.socket_manager.request_block_unblock_user(current_user_domain, current_user_access_token, username, False)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.unblock_user(username)
            else:
                return False, resp_data.get('field')

        # REMOVE UNNEEDED BITS OF THE METHOD ONCE THE WEBSOCKET UPDATES ARE IMPLEMENTED
        # CHANGE BLACKLIST ONLY ON WEBSOCKET UPDATE
        self.current_user['blacklist'].remove(username)

        # SEND REQUEST TO SERVET TO MAKE CHAT READ-WRITE (if other user is reachable)
        chat_id = self.p2p_chat_exists(current_user_username, username, current_user_domain)
        if chat_id and self.user_is_reachable(username):
            chat = self.find_chat(chat_id, current_user_domain)
            chat['chat_setting'] = 'rw'

        return True, None

    def get_domain_users(self, domain: str):
        users = self.domain_users_list.get(domain, None)
        return users

    def create_p2p_chat(self, username: str, domain: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        if current_user_domain != domain: return False, "User domains do NOT match!"

        success, resp_data = self.socket_manager.request_create_p2p_chat(current_user_username, username, domain)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session!"
            else: return self.create_p2p_chat(username, domain)

        resp_data = resp_data.get('field')
        if not resp_data: return False, "Could NOT create chat!"
        self.add_chats([resp_data])

        return True, resp_data['chat_id']

    def get_chat_creator(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None
        return chat['creator']

    def change_admin_status(self, chat_id: str, domain: str, username: str, is_admin: bool):
        chat = self.find_chat(chat_id, domain)
        if not chat: return

        users = chat['users']
        for user in users:
            if user['username'] == username:
                user['is_admin'] = is_admin

    def update_timestamps(self, messages: dict):
        for (chat_id, domain), messages_list in messages.items():
            last_message_timestamp = messages_list[-1]['timestamp']
            self.set_last_message_timestamp(chat_id, domain, last_message_timestamp)

        self.timestamps_updated.emit()

    def get_user_icon_path(self, username: str, domain: str):
        user_data = self.get_user_details(username, domain)
        if not user_data: return './Icons/default_user_icon.png'
        icon_path = user_data['profile']['picture_id']
        if not icon_path: return './Icons/default_user_icon.png'
        return icon_path

    def get_user_description (self, username: str, domain: str):
        user_data = self.get_user_details(username, domain)
        if not user_data: return ""
        return user_data['profile']['status']

    def get_user_details(self, username: str, domain: str):
        domain_users = self.domain_users_list.get(domain, None)
        if domain_users is None: return None

        for user in domain_users:
            if user['username'] == username:
                return user

        return None

    def add_users_to_domain(self, domain: str, users: list):
        users_list = self.domain_users_list.get(domain, None)
        if users_list is None:
            self.domain_users_list[domain] = users
        else:
            usernames = [usr['username'] for usr in users_list]
            for user in users:
                if user['username'] not in usernames:
                    self.domain_users_list[domain].append(user)

    def get_chat_setting(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return None
        return chat['chat_setting']

    def set_chat_setting(self, chat_id: str, domain: str, setting: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return
        if setting != 'rw' and setting != 'ro': return
        chat['chat_setting'] = setting

    def remove_users_from_chat(self, chat_id: str, domain: str, users: list):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return False, "Could NOT find chatroom!"

        chat['users'] = [user for user in chat['users'] if user['username'] not in users]

        self.removed_members_from_chat.emit(chat_id, domain, users)
        return True, None


    def get_last_message_timestamp(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return None
        return chat['last_message_timestamp']

    def set_last_message_timestamp(self, chat_id: str, domain:str, timestamp: float):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return
        chat['last_message_timestamp'] = timestamp
        self.last_seen_time_updated.emit(chat_id, domain)

    def set_current_user_last_seen_time_current_chat(self):
        current_chat_id = self.get_current_chat_id()
        current_chat_domain = self.get_current_chat_domain()
        if current_chat_id and current_chat_domain:
            self.set_current_user_last_seen_time(current_chat_id, current_chat_domain)

    def set_current_user_last_seen_time(self, chat_id: str, domain: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        if current_user_domain != domain: return

        chat_users = self.get_chat_users(chat_id, domain)
        if chat_users is None: return

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
        chat = self.find_chat(chat_details['chat_id'], chat_details['domain'])
        if chat:
            chat.update(chat_details)
        else:
            self.add_chats([chat_details])

        if self.current_chat is None or \
                (self.current_chat['chat_id'] == chat_details['chat_id'] and self.current_chat['domain'] == chat_details['domain']):
            self.current_chat = chat_details

        current_user_domain = self.get_current_user_domain()
        if current_user_domain == chat_details['domain']:
            self.chat_updated.emit(chat_details['chat_id'], chat_details['domain'])

    def load_messages(self, chat_id: str, domain: str, oldest_message_id: str = None, message_nr: int = 50):
        success, resp_data = self.socket_manager.request_messages(chat_id, domain, oldest_message_id, message_nr)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session"
            else: return self.load_messages(chat_id, domain, oldest_message_id, message_nr)
        return success, resp_data.get('field')

    def set_edit(self, is_edit: bool, message_id: str = None, sender: str = None, sender_icon_path: str = None, message_snip: str = None):
        if self.is_edit and not is_edit:
            self.set_textbox_text.emit("")
        self.is_edit = is_edit
        self.edit_message_id = message_id
        self.sender = sender
        self.sender_icon_path = sender_icon_path
        self.message_snip = message_snip
        if is_edit:
            self.set_reply(False)
            self.message_context_changed.emit()
            self.clear_staged_files.emit()

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
            self.set_edit(False)
            self.message_context_changed.emit()

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
        user = self.find_user(username, domain)
        if user:
            self.current_user = user
            self.current_user_changed.emit(user['username'], user['domain'])

    def get_current_user_username(self):
        return self.current_user["username"]

    def get_current_user_domain(self):
        return self.current_user["domain"]

    def get_current_user_icon(self):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()

        return self.get_user_icon_path(current_user_username, current_user_domain)

    def get_current_user_blacklist(self):
        current_user = self.get_current_user()
        return current_user['blacklist']

    def add_user(self, user_data: dict):
        self.users_list.append(user_data)
        self.current_user = user_data

        success, resp_data1 = self.socket_manager.request_chats(user_data['username'], user_data['domain'])
        if not success:
            if resp_data1['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.add_user(user_data)
            else:
                return False, resp_data1.get('field')

        success, resp_data2 = self.socket_manager.request_users(user_data['domain'], user_data['access_token'])
        if not success:
            if resp_data2['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.add_user(user_data)
            else:
                return False, resp_data2.get('field')

        resp_data1 = resp_data1.get('field')
        resp_data2 = resp_data2.get('field')

        self.add_chats(resp_data1)
        self.add_users_to_domain(user_data['domain'], resp_data2)
        self.current_user_changed.emit(user_data['username'], user_data['domain'])
        return True, None

    def remove_user(self, user_data: dict):
        self.users_list.remove(user_data)

    def find_user(self, username: str, domain: str):
        for user in self.users_list:
            if user['username'] == username and user['domain'] == domain:
                return user
        return None

    def remove_user_by_username_and_domain(self, username: str, domain: str):
        user = self.find_user(username, domain)
        if user:
            self.remove_user(user)

    def set_current_chat(self, chat_id: str, domain: str):
        if chat_id == "" and domain == "":
            self.current_chat = None
            return

        chat = self.find_chat(chat_id, domain)
        if not chat:
            self.current_chat = None
            return

        self.current_chat = chat

    def get_chats(self):
        ret = []
        for domain, chats in self.chats_list.items():
            for chat in chats:
                ret.append({
                    "chat_id": chat['chat_id'],
                    "domain": domain
                })
        return ret

    def get_chat_user_usernames(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None
        return list(map(lambda user: user['username'], chat['users']))

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
        chat = self.find_chat(chat_id, domain)
        if not chat: return None
        return chat['chat_type']

    def get_chat_display_name(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None

        if chat['chat_type'] == "chatroom":
            return chat['display_name']
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            return other_username

    def get_chat_description(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None

        if chat['chat_type'] == "chatroom":
            return chat['description']
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_description = self.get_user_description(other_username, domain)
            return other_user_description

    def get_chat_icon_path(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None

        if chat['chat_type'] == "chatroom":
            return chat['icon_path']
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_data = self.get_user_details(other_username, domain)
            if not other_user_data: return "./Icons/default_user_icon.png"

            icon_path = other_user_data['profile']['picture_id']
            if icon_path is None:
                return "./Icons/default_user_icon.png"
            return icon_path

    def get_chat_users(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None
        return chat['users']

    def user_is_admin(self, chat_id: str, domain: str, username: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False

        for user in chat['users']:
            if user['username'] == username:
                return user['is_admin']
        return False

    def add_chats(self, chat_data: list[dict]):
        added_chats = []
        for chat in chat_data:
            chat_domain = chat['domain']
            if not self.chat_exists(chat['chat_id'], chat_domain):
                chats = self.chats_list.get(chat_domain, None)
                if not chats:
                    self.chats_list[chat_domain] = [chat]
                else:
                    chats.append(chat)
                added_chats.append(chat)

        self.chats_added.emit(added_chats)

    def remove_chat(self, chat_id: str, domain: str):
        chats = self.chats_list.get(domain, None)
        if not chats: return

        for chat in chats:
            if chat['chat_id'] == chat_id:
                chats.remove(chat)
                return

    def p2p_chat_exists(self, username1: str, username2: str, domain: str):
        chats = self.chats_list.get(domain, None)
        if not chats: return None

        for chat in chats:
            if chat['chat_type'] != "p2p": continue
            users = [user['username'] for user in chat['users']]
            if username1 in users and username2 in users:
                return chat['chat_id']

        return None

    def chat_exists(self, chat_id: str, domain: str):
        chats = self.chats_list.get(domain, None)
        if not chats: return False

        for chat in chats:
            if chat["chat_id"] == chat_id:
                return True
        return False

    def find_chat(self, chat_id: str, domain: str):
        chats = self.chats_list.get(domain, None)
        if not chats: return None

        for chat in chats:
            if chat['chat_id'] == chat_id:
                return chat

        return None

    def remove_chat_by_id_and_domain(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return
        self.remove_chat(chat['chat_id'], chat['domain'])