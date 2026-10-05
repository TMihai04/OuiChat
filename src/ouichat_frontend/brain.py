import glob

from PyQt6.QtCore import QObject, pyqtSignal

import time
import os

from PyQt6.QtWidgets import QDialog

from request_manager import RequestManager, message_args_to_dict
from websocket_manager import WebSocketManager

class Brain(QObject):
    """
    TO DO:
        - on websocket update (a user blocked the current user), delete the user entry from the users list
        - I need both the reachable users (for block system) list and
        all users list (for display of users that have me blocked, but we're still in common group chats)
    """

    chats_added = pyqtSignal(list)
    chat_removed = pyqtSignal(str, str)

    run_error_dialog = pyqtSignal(str)

    add_users_to_domain_signal = pyqtSignal(str, list)
    remove_user_from_domain_signal = pyqtSignal(str, str)
    user_reachable_status_changed = pyqtSignal(str, str, bool)
    modify_admins_signal = pyqtSignal(str, str, list, list)

    set_chat_visibility = pyqtSignal(str, str, bool)

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

    add_new_messages = pyqtSignal(dict) # key = (chat_id, domain); val = list[message_dict]
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

    cache_path = "../../ignore/Cache"
    os.makedirs(cache_path, exist_ok=True)

    def __init__(self, refresh_login_dialog_class: type, error_dialog):
        super().__init__()

        self.request_manager = RequestManager()
        self.websocket_manager = WebSocketManager()
        self.refresh_login_dialog = refresh_login_dialog_class(self)
        self.error_dialog = error_dialog

        self.users_list = []
        self.chats_list = dict() # key: domain | value: list of chats
        self.domain_users_list = dict() # key: domain | value: list of users
        self.reachable_users_list = []

        self.current_user = None
        self.current_chat = None

        self.is_reply = False
        self.reply_user = None
        self.reply_user_icon_path = None
        self.reply_snip = None
        self.reply_message_id = None

        self.is_edit = False
        self.edit_message_id = None
        self.sender = None
        self.sender_icon_path = None
        self.message_snip = None

        self.chat_selected.connect(self.set_current_chat)
        self.add_new_messages.connect(self.update_timestamps)

        self.request_manager.chat_updated.connect(self.update_chat)

        self.websocket_manager.connection_error.connect(self.handle_websocket_error)
        self.websocket_manager.message_received.connect(self.handle_websocket_event)
        self.websocket_manager.retry_failed.connect(self.handle_websocket_retry_failed)

    def handle_websocket_retry_failed(self, domain: str, access_token: str):
        self.run_error_dialog.emit(f"Connection lost with {domain}. Logging out...")
        self.logout_user_by_details(domain, access_token)

    @staticmethod
    def handle_websocket_error(domain: str, _, error_message: str):
        print(f"Websocket error for {domain}: {error_message}")

    def handle_websocket_event(self, domain: str, access_token: str, event_data: dict):
        print(event_data)

        event_type = event_data['type']
        event_scope = event_data['scope']
        event_payload = event_data['data']

        event_scope_tokenized = event_scope.split('.')
        if event_scope_tokenized[0] == 'token':

            username = None
            for user in self.users_list:
                if user['domain'] == domain and user['access_token'] == access_token:
                    username = user['username']
            if not username: return

            success = self.refresh_tokens(domain, access_token)
            if not success:
                self.logout_user_by_details(domain, access_token)
                return

            user = self.find_user(username, domain)

            self.websocket_manager.update_access_token(domain, access_token, user['access_token'])

            return

        elif event_scope_tokenized[0] == 'user':
            if len(event_scope_tokenized) == 1:
                if event_type == 'create':
                    self.add_users_to_domain(domain, [event_payload])
                    return

                elif event_type == 'delete':
                    username = event_payload['username']
                    current_user_domain = self.get_current_user_domain()
                    if domain == current_user_domain and self.user_is_reachable(username):
                        self.change_reachable_user(username, add=False)

                    self.remove_user_from_domain(domain, username)

                    return

                else: return
            elif len(event_scope_tokenized) == 2:
                if event_type != 'update': return

                if event_scope_tokenized[1] == 'blacklist':
                    current_user_domain = self.get_current_user_domain()
                    if domain != current_user_domain: return

                    username = event_payload['username']
                    got_blacklisted = event_payload['is_blacklisted']
                    self.change_reachable_user(username, add=not got_blacklisted)

                    return

                elif event_scope_tokenized[1] == 'status':
                    username = event_payload['username']
                    new_status = event_payload['status']

                    success = self.set_user_description(username, domain, new_status)
                    if not success:
                        self.run_error_dialog.emit("Could not set user description!")
                        return

                    return

                elif event_scope_tokenized[1] == 'picture':
                    username = event_payload['username']
                    new_picture_id = event_payload['picture_id']

                    success = self.set_user_icon_path(username, domain, new_picture_id)
                    if not success:
                        self.run_error_dialog.emit("Could not set user icon path!")
                        return

                    return

                elif event_scope_tokenized[1] == 'login':
                    # NO IMPLEMENTATION NEEDED YET
                    return

                else: return
            else: return

        elif event_scope_tokenized[0] == 'conversation':
            if len(event_scope_tokenized) == 1:
                if event_type == 'create':
                    chat_details = event_payload
                    chat_dict = self.get_chat_dict_from_chat_details(domain, chat_details)

                    self.add_chats([chat_dict])

                    return

                elif event_type == 'delete':
                    chat_id = event_payload['conversation_id']
                    success = self.remove_chat(chat_id, domain)
                    if not success:
                        self.run_error_dialog.emit("Could not remove chat!")
                        return

                    return

                else: return
            elif len(event_scope_tokenized) == 2:
                if event_type != 'update': return

                if event_scope_tokenized[1] == 'admins':
                    chat_id = event_payload['conversation_id']
                    make = event_payload['make_admin']
                    remove = event_payload['remove_admin']

                    self.modify_admins(chat_id, domain, make, remove)

                    return

                elif event_scope_tokenized[1] == 'participants':
                    operation = event_payload['operation']
                    if operation != 'removed' and operation != 'added': return

                    chat_id = event_payload['conversation_id']
                    participants = event_payload['who']
                    if operation == 'removed':
                        success, error_msg = self.remove_users_from_chat(chat_id, domain, participants)
                        if not success:
                            self.run_error_dialog.emit("Could not remove users!")
                            return

                    else:
                        success, error_msg = self.add_users_to_chat(chat_id, domain, participants)
                        if not success:
                            self.run_error_dialog.emit("Could not add users!")
                            return

                    return

                elif event_scope_tokenized[1] == 'name':
                    chat_id = event_payload['conversation_id']
                    new_name = event_payload['name']

                    success, error_msg = self.set_chat_display_name(chat_id, domain, new_name)
                    if not success:
                        self.run_error_dialog.emit(error_msg)
                        return

                    return

                elif event_scope_tokenized[1] == 'description':
                    chat_id = event_payload['conversation_id']
                    new_desc = event_payload['description']

                    success = self.set_chat_description(chat_id, domain, new_desc)
                    if not success:
                        self.run_error_dialog.emit("Could not set chat description!")
                        return

                    return

                elif event_scope_tokenized[1] == 'picture':
                    chat_id = event_payload['conversation_id']
                    icon_path = event_payload['picture_id']

                    success, error_msg = self.set_chat_icon_path(chat_id, domain, icon_path)
                    if not success:
                        self.run_error_dialog.emit(error_msg)
                        return

                    return

                elif event_scope_tokenized[1] == 'owner':
                    chat_id = event_payload['conversation_id']
                    owner = event_payload['owner']
                    chat = self.find_chat(chat_id, domain)
                    if chat:
                        chat['creators'] = [owner]
                    return

                elif event_scope_tokenized[1] == 'seen':
                    chat_id = event_payload['conversation_id']
                    seen_at = event_payload.get('last_seen')
                    username = None
                    for user in self.users_list:
                        if user['domain'] == domain and user['access_token'] == access_token:
                            username = user['username']
                    if username and isinstance(seen_at, int):
                        self._write_last_seen(chat_id, domain, seen_at, username)
                    return

                else: return
            else: return

        elif event_scope_tokenized[0] == 'message':
            if len(event_scope_tokenized) == 1:
                if event_type != 'create' and event_type != 'delete': return

                if event_type == 'create':
                    message_id = event_payload['message_id']
                    sender = event_payload['sender']
                    text = event_payload['content'] if event_payload['content'] else ""
                    attachments = event_payload['attachments']
                    replied_to = event_payload['replied_to'] # message_id
                    created_at = event_payload['created_at']
                    updated_at = event_payload['updated_at']
                    chat_id = event_payload['chat_id']

                    message_dict = message_args_to_dict(
                        chat_id=chat_id,
                        domain=domain,
                        message_id=message_id,
                        sender=sender,
                        was_edited=created_at != updated_at,
                        is_reply=replied_to is not None,
                        reply_sender="Unknown User", # TO BE MODIFIED
                        reply_snip="Unknown Message", # TO BE MODIFIED
                        timestamp=created_at,
                        text=text,
                        files=list(map(lambda file_id: {"file_name": file_id, "file_id": file_id}, attachments)), # FUTURE: GET FILE NAME FROM MESSAGE STATE
                    )

                    signal_dict = {
                        (chat_id, domain): [message_dict]
                    }
                    self.add_new_messages.emit(signal_dict)
                    return

                else:
                    message_id = event_payload['message_id']
                    chat_id = event_payload['chat_id']

                    signal_dict = {
                        (chat_id, domain): [message_id]
                    }
                    self.remove_messages.emit(signal_dict)
                    return

            elif len(event_scope_tokenized) == 2:
                if event_type != 'update': return

                message_id = event_payload['message_id']
                new_text = event_payload['content']
                chat_id = event_payload['chat_id']
                self.message_edited.emit(chat_id, domain, message_id, new_text)
                return

        else:
            return

    def icon_path_from_icon_id(self, icon_id: str | None):
        if icon_id is None: return "./Icons/default_user_icon.png"

        matching_files = glob.glob(f"{self.cache_path}/{icon_id}.*")
        if matching_files:
            return matching_files[0]
        return None

    def delete_message_request(self, message_id: str):
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()
        current_chat_id = self.get_current_chat_id()
        success, resp_data = self.request_manager.request_delete_message(current_user_domain, current_user_access_token, current_chat_id, message_id)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.delete_message_request(message_id)
            else:
                return False, "Could NOT delete message."

        return True, None

    def edit_message_request(self, message_id: str, text: str):
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()
        current_chat_id = self.get_current_chat_id()
        success, resp_data = self.request_manager.request_edit_message(current_user_domain, current_user_access_token, current_chat_id, message_id, text)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.edit_message_request(message_id, text)
            else:
                return False, "Could NOT edit message."

        return True, None

    def send_message_request(self, text: str, file_ids: list, replied_to: str):
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()
        current_chat_id = self.get_current_chat_id()
        success, resp_data = self.request_manager.request_send_message(current_user_domain, current_user_access_token, current_chat_id, text, file_ids, replied_to)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.send_message_request(text, file_ids, replied_to)
            else:
                return False, "Could NOT send message."

        return True, None

    def remove_users_from_chat(self, chat_id: str, domain: str, users: list):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return False, "Could NOT find chatroom!"

        chat['users'] = [user for user in chat['users'] if user['username'] not in users]

        self.removed_members_from_chat.emit(chat_id, domain, users)

        chat_users = list(map(lambda user: user['username'], self.get_chat_users(chat_id, domain)))
        safe_to_remove = True
        for user in self.users_list:
            if user['username'] in chat_users:
                safe_to_remove = False
                break

        if safe_to_remove:
            self.remove_chat(chat_id, domain)

        return True, None

    def add_users_to_chat(self, chat_id: str, domain: str, users: list):
        chat = self.find_chat(chat_id, domain)
        if not chat:
            current_user_access_token = self.get_current_user_access_token()
            success, resp_data = self.request_manager.request_get_chat_details(domain, current_user_access_token, chat_id)

            if not success:
                if resp_data['code'] == 401:
                    refreshed = self.refresh_tokens()
                    if not refreshed:
                        return False, "Could not refresh session"
                    else:
                        return self.add_users_to_chat(chat_id, domain, users)
                else:
                    return False, resp_data.get('field')

            chat_details = resp_data.get('field').get('item')
            chat_dict = self.get_chat_dict_from_chat_details(domain, chat_details)

            self.add_chats([chat_dict])

            self.added_members_to_chat.emit(chat_id, domain, users)
            return True, None

        chat['users'].extend([{
            "username": user,
            "is_admin": False,
            "last_seen_time": 0
        } for user in users])

        self.added_members_to_chat.emit(chat_id, domain, users)
        return True, None

    def modify_admins(self, chat_id: str, domain: str, make: list, remove: list):
        chat_users = self.get_chat_users(chat_id, domain)
        for user in chat_users:
            if user['username'] in make:
                user['is_admin'] = True
            elif user['username'] in remove:
                user['is_admin'] = False

        self.modify_admins_signal.emit(chat_id, domain, make, remove)

    def set_user_icon_path(self, username: str, domain: str, icon_path: str | None):
        user_data = self.get_user_details(username, domain)
        if not user_data: return False
        user_data['profile']['picture_id'] = icon_path if icon_path is not None else None

        self.user_updated.emit(username, domain)

        return True

    def set_user_description(self, username: str, domain: str, description: str):
        user_data = self.get_user_details(username, domain)
        if not user_data: return False
        user_data['profile']['status'] = description

        self.user_updated.emit(username, domain)

        return True

    def remove_user_from_domain(self, domain: str, username: str):
        domain_users = self.get_domain_users(domain)
        for user in domain_users:
            if user['username'] == username:
                domain_users.remove(user)

                self.remove_user_from_domain_signal.emit(domain, username)

                return

    def logout_user_by_details(self, domain: str, access_token: str):
        current_user_username = self.get_current_user_username()
        self.set_current_user_last_seen_time_current_chat()
        self.main_window_comms_requested.emit()

        # SEND LAST SEEN MESSAGE ID THROUGH WEBSOCKET

        self.websocket_manager.disconnect_websocket(domain, access_token)

        self.logout_user.emit(current_user_username, domain)

        other_logged_users_in_current_domain = []
        for user in self.users_list:
            if user['domain'] == domain:
                other_logged_users_in_current_domain.append(user['username'])

        if not other_logged_users_in_current_domain:
            self.remove_domain.emit(domain)
            del self.chats_list[domain]
            del self.domain_users_list[domain]
        else:
            chats_to_remove = dict()
            chats_to_remove['domain'] = domain
            chats_to_remove['chat_ids'] = []
            for idx in reversed(range(len(self.chats_list[domain]))):
                chat = self.chats_list[domain][idx]
                safe_to_remove = True
                for other_user in other_logged_users_in_current_domain:
                    if other_user in list(map(lambda chat_user: chat_user['username'], chat['users'])):
                        safe_to_remove = False
                        break
                if safe_to_remove:
                    chats_to_remove['chat_ids'].append(chat['chat_id'])
                    del self.chats_list[domain][idx]

            self.remove_chats.emit(chats_to_remove)

        for idx in range(len(self.users_list)):
            if self.users_list[idx]['username'] == current_user_username and self.users_list[idx]['domain'] == domain:
                del self.users_list[idx]
                break

    def logout_current_user(self):
        """
        TO DO:
            - send state to server after setting user last seen time
        """
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        self.logout_user_by_details(current_user_domain, current_user_access_token)
        self.select_previous_user.emit()

    def refresh_tokens(self, domain: str | None = None, access_token: str | None = None):
        target_domain = domain if domain else self.get_current_user_domain()
        target_access_token = access_token if access_token else self.get_current_user_access_token()

        target_user = None
        for user in self.users_list:
            if user['domain'] == target_domain and user['access_token'] == target_access_token:
                target_user = user

        if not target_user: return False

        success, resp_data = self.request_manager.request_refresh_tokens(domain, target_user['refresh_token'])
        if not success:
            response = self.refresh_login_dialog.exec()
            return response == QDialog.DialogCode.Accepted

        resp_data = resp_data.get('field')

        target_user['access_token'] = resp_data['access_token']
        target_user['refresh_token'] = resp_data['refresh_token']
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

        success, resp_data = self.request_manager.request_get_current_user_profile(req_domain, req_access_token)
        if not success and resp_data['code'] == 401:
            refreshed = self.refresh_tokens()
            if not refreshed: return False, "Could not refresh session"
            else: return self.get_current_user_profile(req_domain, req_access_token)
        return success, resp_data.get('field')

    def register_login_user(self, domain: str | None, username: str | None, password: str, login: bool):
        req_domain = domain if domain else self.get_current_user_domain()
        req_username = username if username else self.get_current_user_username()
        success, resp_data = self.request_manager.request_register_login(req_domain, req_username, password, login)
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
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_change_user_description(current_user_domain, current_user_access_token, description)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session"
                else:
                    return self.set_current_user_description(description)
            else:
                return False, resp_data.get('field')

        return True, None


    def set_current_user_icon_path(self, icon_path: str):
        current_user_access_token = self.get_current_user_access_token()
        current_user_domain = self.get_current_user_domain()

        success, resp_data, uploaded_files = self.upload_files([(icon_path, "icon")])
        if not success:
            return False, "Could not upload icon."

        icon_id = uploaded_files[0]['file_id']

        success, resp_data = self.request_manager.request_change_user_icon(current_user_domain, current_user_access_token, icon_id)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.set_current_user_icon_path(icon_path)
            else:
                return False, resp_data.get('field')

        return True, None

    def upload_files(self, file_list: list):
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()
        success, resp_data, uploaded_files = self.request_manager.request_upload_files(current_user_domain, current_user_access_token, file_list)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session", uploaded_files
                else:
                    return self.upload_files(file_list)
            else:
                return False, "Could NOT upload all files.", uploaded_files
        return True, None, uploaded_files

    def download_file(self, file_id: str, path: str | None = None):
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()
        success, resp_data = self.request_manager.request_download_file(current_user_domain, current_user_access_token, file_id, path)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.download_file(file_id, path)
            else:
                return False, "Could NOT download file."

        return True, resp_data

    def add_users_to_chat_request(self, chat_id: str, domain: str, users: list):
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_modify_users(domain, current_user_access_token, chat_id, users, add=True)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session"
                else:
                    return self.add_users_to_chat_request(chat_id, domain, users)
            else:
                return False, "Could NOT add users to chatroom!"

        return True, None

    def get_chat_dict_from_chat_details(self, domain: str, chat_details: dict):
        chat_type = chat_details.get('type')
        chat_setting = 'rw'
        if chat_type == 'direct':
            blacklist = self.get_current_user_blacklist()
            for user in chat_details.get('preferences').get('participants'):
                if user.get('username') in blacklist:
                    chat_setting = 'ro'
                    break

        return {
            "chat_type": chat_details.get('type'),
            "chat_setting": chat_setting,
            "domain": domain,
            "chat_id": chat_details.get('conversation_id'),
            "display_name": chat_details.get('profile').get('name'),
            "description": chat_details.get('profile').get('description'),
            "icon_path": chat_details.get('profile').get('picture_id'),
            "creators": chat_details.get('preferences').get('created_by'),
            "last_message_timestamp": 0,
            "users": [{
                "username": participant.get('username'),
                "is_admin": participant.get('is_admin'),
                "last_seen_time": participant.get('last_seen') or 0
            } for participant in chat_details.get('preferences').get('participants')],
        }

    def create_chatroom(self, users: list):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        users_dict = dict()
        for username in users:
            users_dict[username] = False
        users_dict[current_user_username] = True

        name = f'{current_user_username}s Chatroom'
        description = f'{current_user_username}s Chatroom'
        icon_id = ""

        success, resp_data = self.request_manager.request_create_chat(
            current_user_domain, current_user_access_token, is_group_chat = True,
            name = name, description = description, icon_id = icon_id, participants = users_dict
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else: return self.create_chatroom(users)
            else:
                return False, "Could NOT create chatroom!"

        resp_data = resp_data.get('field')
        chat_id = resp_data.get('item').get('conversation_id')

        success, resp_data = self.request_manager.request_get_chat_details(
            current_user_domain, current_user_access_token, chat_id
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else: return self.create_chatroom(users)
            else:
                return False, "Could NOT fetch chat details!"

        resp_data = resp_data.get('field')
        chat_details = resp_data.get('item')

        chat_dict = self.get_chat_dict_from_chat_details(current_user_domain, chat_details)

        self.add_chats([chat_dict])
        return True, (chat_id, current_user_domain)

    def set_chat_icon_path(self, chat_id, domain, icon_path):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False, "Could not find chat!"

        chat['icon_path'] = icon_path

        self.chat_updated.emit(chat_id, domain)
        return True, None

    def set_chat_icon_path_request(self, chat_id: str, domain: str, icon_path: str):
        """
        NOT MADE FOR WEBSOCKET UPDATES
        """
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data, uploaded_files = self.upload_files([(icon_path, "icon")])
        if not success:
            return False, resp_data

        icon_id = uploaded_files[0]['file_id']

        success, resp_data = self.request_manager.request_modify_chat_icon(
            domain, current_user_access_token, chat_id, icon_id
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.set_chat_icon_path_request(chat_id, domain, icon_path)
            else:
                return False, "Could NOT set chat icon!"

        return True, None

    def set_chat_display_name(self, chat_id: str, domain: str, display_name: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False, "Could not find chat!"

        chat['display_name'] = display_name

        self.chat_updated.emit(chat_id, domain)
        return True, None

    def set_chat_display_name_request(self, chat_id: str, domain: str, display_name: str):
        """
        NOT MADE FOR WEBSOCKET UPDATES
        """
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_modify_chat_name(
            domain, current_user_access_token, chat_id, display_name
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session!"
                else:
                    return self.set_chat_display_name_request(chat_id, domain, display_name)
            else:
                return False, "Could NOT set chat name!"

        return True, None

    def set_chat_description(self, chat_id: str, domain: str, description: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False, "Could not find chat!"

        chat['description'] = description

        self.chat_updated.emit(chat_id, domain)
        return True, None

    def set_chat_description_request(self, chat_id: str, domain: str, description: str):
        """
        NOT MADE FOR WEBSOCKET UPDATES
        """
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_modify_chat_description(
            domain, current_user_access_token, chat_id, description
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session!"
                else:
                    return self.set_chat_display_name_request(chat_id, domain, description)
            else:
                return False, "Could NOT set chat description!"

        return True, None

    def user_is_blocked(self, username: str):
        return username in self.current_user['blacklist']

    def user_is_reachable(self, username: str):
        return username in self.reachable_users_list

    def block_user(self, username: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_block_unblock_user(current_user_domain, current_user_access_token, username, True)
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

        chat_id = self.p2p_chat_exists(current_user_username, username, current_user_domain)
        if chat_id:
            chat = self.find_chat(chat_id, current_user_domain)
            chat['chat_setting'] = 'ro'

        return True, None

    def unblock_user(self, username: str):
        current_user_username = self.get_current_user_username()
        current_user_domain = self.get_current_user_domain()
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_block_unblock_user(current_user_domain, current_user_access_token, username, False)
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
        current_user_access_token = self.get_current_user_access_token()
        if current_user_domain != domain: return False, "User domains do NOT match!"

        users = dict()
        users[current_user_username] = True
        users[username] = True

        success, resp_data = self.request_manager.request_create_chat(
            current_user_domain, current_user_access_token, is_group_chat = False,
            name = "dummy", description = "dummy", icon_id = "dummy", participants = users
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else: return self.create_p2p_chat(username, domain)
            else:
                return False, "Could NOT create chat!"

        resp_data = resp_data.get('field')
        chat_id = resp_data.get('item').get('conversation_id')

        success, resp_data = self.request_manager.request_get_chat_details(
            current_user_domain, current_user_access_token, chat_id
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session!"
                else:
                    return self.create_p2p_chat(username, domain)
            else:
                return False, "Could NOT fetch chat details!"

        resp_data = resp_data.get('field')
        chat_details = resp_data.get('item')

        chat_dict = self.get_chat_dict_from_chat_details(current_user_domain, chat_details)

        self.add_chats([chat_dict])
        return True, chat_id

    def get_chat_creators(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None
        return chat['creators']

    def change_admin_status(self, chat_id: str, domain: str, username: str, is_admin: bool):
        chat = self.find_chat(chat_id, domain)
        if not chat: return False, "Could not find chat."

        current_user_access_token = self.get_current_user_access_token()

        user_dict = {
            username: is_admin
        }

        success, resp_data = self.request_manager.request_modify_admin(domain, current_user_access_token, chat_id, user_dict)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.change_admin_status(chat_id, domain, username, is_admin)
            else:
                return False, "Could NOT modify admin!"

        return True, None

    def update_timestamps(self, messages: dict):
        for (chat_id, domain), messages_list in messages.items():
            last_message_timestamp = messages_list[-1]['timestamp']
            self.set_last_message_timestamp(chat_id, domain, last_message_timestamp)

        self.timestamps_updated.emit()

    def get_user_icon_path(self, username: str, domain: str):
        user_data = self.get_user_details(username, domain)
        if not user_data: return './Icons/default_user_icon.png'
        icon_id = user_data['profile']['picture_id']
        icon_path = self.icon_path_from_icon_id(icon_id)
        if not icon_path:
            success, resp_data = self.download_file(icon_id, str(self.cache_path))
            if not success:
                return './Icons/default_user_icon.png'
            return resp_data

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

        self.add_users_to_domain_signal.emit(domain, users)

    def get_chat_setting(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return None
        return chat['chat_setting']

    def set_chat_setting(self, chat_id: str, domain: str, setting: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return
        if setting != 'rw' and setting != 'ro': return
        chat['chat_setting'] = setting

    def leave_chat(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return False, "Could NOT find chatroom!"

        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_leave_chat(domain, current_user_access_token, chat_id)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.leave_chat(chat_id, domain)
            else:
                return False, "Could NOT leave chatroom!"

        return True, None

    def delete_chat(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if chat is None: return False, "Could NOT find chatroom!"

        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_delete_chat(domain, current_user_access_token, chat_id)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.delete_chat(chat_id, domain)
            else:
                return False, "Could NOT delete chatroom!"

        return True, None

    def remove_users_from_chat_request(self, chat_id: str, domain: str, users: list):
        current_user_access_token = self.get_current_user_access_token()

        success, resp_data = self.request_manager.request_modify_users(domain, current_user_access_token, chat_id, users, add=False)
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.remove_users_from_chat_request(chat_id, domain, users)
            else:
                return False, "Could NOT remove users to chatroom!"

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
        current_user_domain = self.get_current_user_domain()
        if current_user_domain != domain: return

        stamp = max(int(time.time() * 1000), self.get_last_message_timestamp(chat_id, domain) or 0)
        self._write_last_seen(chat_id, domain, stamp)
        self._push_last_seen(chat_id, domain)

    def _write_last_seen(self, chat_id: str, domain: str, stamp: int, username: str | None = None):
        if username is None:
            if self.get_current_user_domain() != domain: return
            username = self.get_current_user_username()

        chat_users = self.get_chat_users(chat_id, domain)
        if chat_users is None: return

        for user in chat_users:
            if user['username'] != username: continue
            user['last_seen_time'] = max(user.get('last_seen_time') or 0, stamp)
            if username == self.get_current_user_username() and domain == self.get_current_user_domain():
                self.last_seen_time_updated.emit(chat_id, domain)
            return

    def _push_last_seen(self, chat_id: str, domain: str, retried: bool = False):
        if self.get_current_user_domain() != domain: return
        access_token = self.get_current_user_access_token()
        success, resp_data = self.request_manager.request_mark_chat_seen(domain, access_token, chat_id)
        if not success:
            if not retried and resp_data.get('code') == 401 and self.refresh_tokens():
                self._push_last_seen(chat_id, domain, retried=True)
            return
        seen_at = resp_data.get('field', {}).get('item', {}).get('last_seen')
        if isinstance(seen_at, int):
            self._write_last_seen(chat_id, domain, seen_at)

    def prime_chat_activity(self, chats: list):
        username = self.get_current_user_username()
        domain = self.get_current_user_domain()
        access_token = self.get_current_user_access_token()
        for chat in chats:
            if chat['domain'] != domain: continue
            success, messages = self.load_messages(domain, chat['chat_id'], "old", None, 1)
            if not success or not messages: continue
            chat['last_message_timestamp'] = messages[-1]['timestamp']
            seen = 0
            for user in chat['users']:
                if user['username'] == username:
                    seen = user.get('last_seen_time') or 0
                    break
            if seen: continue
            success, resp_data = self.request_manager.request_mark_chat_seen(domain, access_token, chat['chat_id'])
            if not success and resp_data.get('code') == 401 and self.refresh_tokens():
                access_token = self.get_current_user_access_token()
                success, resp_data = self.request_manager.request_mark_chat_seen(domain, access_token, chat['chat_id'])
            if not success: continue
            seen_at = resp_data.get('field', {}).get('item', {}).get('last_seen')
            if not isinstance(seen_at, int): continue
            for user in chat['users']:
                if user['username'] == username:
                    user['last_seen_time'] = seen_at

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

    def load_messages(self, domain: str, chat_id: str, direction: str | None, message_id: str | None, batch_size: int | None):
        current_user_access_token = self.get_current_user_access_token()
        success, resp_data = self.request_manager.request_get_messages(
            domain, current_user_access_token, chat_id, direction, message_id, batch_size
        )
        if not success:
            if resp_data['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed:
                    return False, "Could not refresh session"
                else:
                    return self.load_messages(domain, chat_id, direction, message_id, batch_size)
            else:
                return False, "Could NOT load messages!"

        messages = resp_data.get('field')
        formatted_messages = []
        for message in messages:
            if message_id and message['message_id'] == message_id: continue
            formatted_messages.append(message_args_to_dict(
                chat_id=chat_id,
                domain=domain,
                message_id=message['message_id'],
                sender=message['sender'],
                was_edited=message['created_at'] != message['updated_at'],
                is_reply=message['replied_to'] is not None,
                reply_sender='Unknown User', # TO BE MODIFIED
                reply_snip='Unknown Message', # TO BE MODIFIED
                timestamp=message['created_at'],
                text=message['content'] if message['content'] else "",
                files=list(map(lambda file_id: {"file_name": file_id, "file_id": file_id}, message['attachments'])) # FUTURE: GET FILE NAME FROM MESSAGE STATE
            ))

        return True, formatted_messages

    # def load_messages(self, chat_id: str, domain: str, oldest_message_id: str = None, message_nr: int = 50):
    #     success, resp_data = self.request_manager.request_messages(chat_id, domain, oldest_message_id, message_nr)
    #     if not success and resp_data['code'] == 401:
    #         refreshed = self.refresh_tokens()
    #         if not refreshed: return False, "Could not refresh session"
    #         else: return self.load_messages(chat_id, domain, oldest_message_id, message_nr)
    #     return success, resp_data.get('field')

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

    def set_reply(self, is_reply: bool, reply_user: str = None, reply_user_icon_path: str = None, reply_snip: str = None, reply_message_id: str = None):
        self.is_reply = is_reply
        self.reply_user = reply_user
        self.reply_user_icon_path = reply_user_icon_path
        self.reply_snip = reply_snip
        self.reply_message_id = reply_message_id
        if is_reply:
            self.set_edit(False)
            self.message_context_changed.emit()

    def get_reply_details(self):
        return {
            "is_reply": self.is_reply,
            "reply_sender": self.reply_user,
            "reply_sender_icon_path": self.reply_user_icon_path,
            "reply_snip": self.reply_snip,
            "reply_message_id": self.reply_message_id
        }

    def get_current_user(self):
        return self.current_user

    def change_reachable_user(self, username: str, add: bool):
        current_user_domain = self.get_current_user_domain()
        if add:
            self.reachable_users_list.append(username)
        else:
            self.reachable_users_list.remove(username)

        self.user_reachable_status_changed.emit(current_user_domain, username, add)

    def set_current_user_reachable_users(self, users: list):
        self.reachable_users_list = list(map(lambda user: user['username'], users))

    def set_current_user(self, username: str, domain: str):
        user = self.find_user(username, domain)
        if user:
            success, resp_data = self.request_manager.request_users(user['domain'], user['access_token'])
            if not success:
                if resp_data['code'] == 401:
                    refreshed = self.refresh_tokens()
                    if not refreshed:
                        return False, "Could not refresh session!"
                    else:
                        return self.set_current_user(username, domain)
                else:
                    return False, "Could NOT fetch users!"

            resp_data = resp_data.get('field')
            white = resp_data['white']

            self.current_user = user
            self.set_current_user_reachable_users(white)

            self.current_user_changed.emit(user['username'], user['domain'])

            return True, None

        return False, "Could not find user!"

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

        success, resp_data1 = self.request_manager.request_chats(user_data['domain'], user_data['access_token'])
        if not success:
            if resp_data1['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.add_user(user_data)
            else:
                return False, "Could NOT fetch chats!"

        success, resp_data2 = self.request_manager.request_users(user_data['domain'], user_data['access_token'])
        if not success:
            if resp_data2['code'] == 401:
                refreshed = self.refresh_tokens()
                if not refreshed: return False, "Could not refresh session!"
                else:
                    return self.add_user(user_data)
            else:
                return False, "Could NOT fetch users!"

        resp_data1 = resp_data1.get('field').get('items')
        resp_data2 = resp_data2.get('field')

        chat_dicts = list(map(lambda chat_details: self.get_chat_dict_from_chat_details(user_data['domain'], chat_details), resp_data1))
        self.prime_chat_activity(chat_dicts)
        self.add_chats(chat_dicts)

        white = resp_data2['white']
        black = resp_data2['black']
        self.add_users_to_domain(user_data['domain'], white + black)
        self.set_current_user_reachable_users(white)

        self.websocket_manager.connect_websocket(user_data['domain'], user_data['access_token'])

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

        if chat['chat_type'] == "group":
            return chat['display_name']
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            return other_username

    def get_chat_description(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return None

        if chat['chat_type'] == "group":
            return chat['description']
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            other_user_description = self.get_user_description(other_username, domain)
            return other_user_description

    def get_chat_icon_path(self, chat_id: str, domain: str):
        chat = self.find_chat(chat_id, domain)
        if not chat: return './Icons/chat_room_icon.png'

        if chat['chat_type'] == "group":
            icon_id = chat['icon_path']
            icon_path = self.icon_path_from_icon_id(icon_id)
            if not icon_path:
                success, resp_data = self.download_file(icon_id, str(self.cache_path))
                if not success:
                    return './Icons/chat_room_icon.png'
                return resp_data

            return icon_path
        else:
            current_username = self.get_current_user_username()
            usernames = [usr['username'] for usr in chat['users']]
            other_username = usernames[0] if usernames[0] != current_username else usernames[1]
            return self.get_user_icon_path(other_username, domain)

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
        if not chats: return False

        for chat in chats:
            if chat['chat_id'] == chat_id:
                chats.remove(chat)

                self.chat_removed.emit(domain, chat_id)

                return True

        return False

    def p2p_chat_exists(self, username1: str, username2: str, domain: str):
        chats = self.chats_list.get(domain, None)
        if not chats: return None

        for chat in chats:
            if chat['chat_type'] != "direct": continue
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