import time
import random
import os
import shutil
from typing import Any
import aiohttp
import asyncio
from PyQt6.QtCore import pyqtSignal, QObject, QThread, QEventLoop

UPLOAD_DIR_PATH = "./Uploads/"

MAX_REQUESTS = 5
REQUEST_TIMEOUT = 2

uploaded_files = []

def get_resp_dict(is_error: bool, code: int, field: Any):
    return {
        "is_error": is_error,
        "code": code,
        "field": field
    }

async def handle_error(response: aiohttp.ClientResponse):
    code = response.status
    if code == 400 or code == 401:
        error_msg = (await response.json()).get('detail', 'Something went wrong.')
        return get_resp_dict(True, code, error_msg)
    return get_resp_dict(True, code, 'Something went wrong')

async def login_register_request(domain: str, username: str, password: str, login: bool):
    register_json = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    endpoint = "login" if login else "register"
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/{endpoint}", data=register_json) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(False, 408, 'Cannot establish a connection with the server.')

class CredentialsRequestWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, username: str, password: str, login: bool):
        super().__init__()

        self.domain = domain
        self.username = username
        self.password = password
        self.login = login

    def run(self):
        resp = asyncio.run(login_register_request(self.domain, self.username, self.password, self.login))
        self.finished.emit(resp)

async def get_current_user_profile_request(domain: str, access_token: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"http://{domain}/users/me", headers=headers) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class CurrentUserProfileWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str):
        super().__init__()

        self.domain = domain
        self.access_token = access_token

    def run(self):
        resp = asyncio.run(get_current_user_profile_request(domain=self.domain, access_token=self.access_token))
        self.finished.emit(resp)

async def change_user_description(domain: str, access_token: str, new_description: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    body = {
        "status": new_description,
    }

    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/users/profile/status", headers=headers, json=body) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class ChangeUserDescriptionWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, new_description: str):
        super().__init__()

        self.domain = domain
        self.access_token = access_token
        self.new_description = new_description

    def run(self):
        resp = asyncio.run(change_user_description(domain=self.domain, access_token=self.access_token, new_description=self.new_description))
        self.finished.emit(resp)

async def change_user_icon(domain: str, access_token: str, icon_path):
    """
    TO DO:
        1. upload the new image to the backend
        2. get file id from backend response
        3. save file in cache with the name being its id
        4. send request to backend to change icon id with the new id
    """
    pass

class ChangeUserIconWorker(QThread):
    """
    TO DO:
        - to be implemented
    """
    pass

async def get_users_list_request(domain: str, access_token: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"http://{domain}/users/list", headers=headers) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class UsersListRequestWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str):
        super().__init__()

        self.domain = domain
        self.access_token = access_token

    def run(self):
        resp = asyncio.run(get_users_list_request(domain=self.domain, access_token=self.access_token))
        self.finished.emit(resp)

async def block_unblock_user_request(domain: str, access_token: str, username: str, block: bool):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    body = {
        "who": username,
    }
    async with aiohttp.ClientSession() as session:
        request_type = session.post if block else session.delete
        for request_count in range(MAX_REQUESTS):
            try:
                async with request_type(url=f"http://{domain}/users/preferences/blacklist", headers=headers, json=body) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class BlockUnblockUserWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, username: str, block: bool):
        super().__init__()

        self.domain = domain
        self.access_token = access_token
        self.username = username
        self.block = block

    def run(self):
        resp = asyncio.run(block_unblock_user_request(self.domain, self.access_token, self.username, self.block))
        self.finished.emit(resp)

async def refresh_tokens_request(domain: str, refresh_token: str):
    headers = {
        'Authorization': f"Bearer {refresh_token}",
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/refresh", headers=headers) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class RefreshTokensWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, refresh_token: str):
        super().__init__()
        self.domain = domain
        self.refresh_token = refresh_token

    def run(self):
        resp = asyncio.run(refresh_tokens_request(domain=self.domain, refresh_token=self.refresh_token))
        self.finished.emit(resp)

async def create_chat_request(domain: str, access_token: str,
                              is_group_chat: bool, name: str, description: str, icon_id: str, participants: dict):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    body = {
        "type": "group" if is_group_chat else "direct",
        "group": {
            "name": name,
            "description": description,
            "picture_id": icon_id
        },
        "participants": participants
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"http://{domain}/chats/create", headers=headers, json=body) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class CreateChatWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str,
                 is_group_chat: bool, name: str, description: str, icon_id: str, participants: dict):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.is_group_chat = is_group_chat
        self.name = name
        self.description = description
        self.icon_id = icon_id
        self.participants = participants

    def run(self):
        resp = asyncio.run(create_chat_request(domain=self.domain, access_token=self.access_token,
                                               is_group_chat=self.is_group_chat, name=self.name,
                                               description=self.description, icon_id=self.icon_id,
                                               participants=self.participants))
        self.finished.emit(resp)

async def get_chat_details_request(domain: str, access_token: str, chat_id: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"http://{domain}/chats/chat", headers=headers, params=params) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    resp_dict = await resp.json()
                    return get_resp_dict(False, resp.status, resp_dict)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class GetChatDetailsWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id

    def run(self):
        resp = asyncio.run(get_chat_details_request(domain=self.domain, access_token=self.access_token, chat_id=self.chat_id))
        self.finished.emit(resp)

def execute_request_loop(worker: QThread):
    loop = QEventLoop()
    worker_response = dict()

    def catch_response(resp):
        nonlocal worker_response
        worker_response = resp
        loop.quit()

    worker.finished.connect(catch_response)
    worker.start()
    loop.exec()

    return worker_response

def get_file_path(file_id: int):
    for file_entry in uploaded_files:
        if file_entry["file_id"] == file_id:
            return file_entry["file_path"]

    return None

def message_args_to_dict(chat_id: str, domain: str, message_id: str, sender: str,
                         was_edited: bool, is_reply: bool, reply_sender: str,
                         reply_snip: str, timestamp: float, text: str, files: list):
    return {
        "chat_id": chat_id,
        "domain": domain,
        "message_id": message_id,
        "sender": sender,
        "was_edited": was_edited,
        "is_reply": is_reply,
        "reply_sender": reply_sender,
        "reply_snip": reply_snip,
        "timestamp": timestamp,
        "text": text,
        "uploaded_files": files,
    }

class SocketManager(QObject):
    """
    TO DO:
        - implement request/websocket communication
    """

    chat_updated = pyqtSignal(dict) # chat_details

    def __init__(self):
        super().__init__()

        self.credentials_worker = None
        self.users_list_worker = None
        self.block_unblock_worker = None
        self.current_user_profile_worker = None
        self.change_user_description_worker = None
        self.refresh_tokens_worker = None
        self.create_chat_worker = None
        self.get_chat_details_worker = None

    def request_chats(self, username: str, domain: str):

        chats = []
        for idx in reversed(range(20)):  # adding 20 chat rooms to the list
            chat_data = {
                "chat_type": "group",  # {"group", "direct"}
                "chat_setting": "rw",  # {"rw", "ro"}
                "domain": domain,
                "chat_id": str(idx),
                "display_name": f"chatroom {str(idx)}",
                "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                "icon_path": "./Icons/chat_room_icon.png",
                "creator": "fifo" if idx % 2 == 1 else "fifo2",
                "last_message_timestamp": time.time(),
                "users": [{"username": "fifo",
                           "is_admin": True,
                           "last_seen_time": time.time()}] if idx < 5 else
                [{"username": "fifo",
                  "is_admin": True,
                  "last_seen_time": time.time()},
                 {"username": "fifo2",
                  "is_admin": False,
                  "last_seen_time": time.time() - 2},
                 {"username": "fifo3",
                  "is_admin": False,
                  "last_seen_time": time.time()}] if idx < 10 else
                [{"username": "fifo2",
                  "is_admin": True,
                  "last_seen_time": time.time()}]
            }
            chats.append(chat_data)

        # return False, error_dict on error
        return True, {"field": chats}

    def request_refresh_tokens(self, domain: str, refresh_tokens):
        self.refresh_tokens_worker = RefreshTokensWorker(domain, refresh_tokens)
        worker_response = execute_request_loop(self.refresh_tokens_worker)
        self.refresh_tokens_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

    def request_messages(self, chat_id: str, domain: str, oldest_message_id: str, message_nr: int):

        messages = []
        for idx in range(20):
            is_reply = idx % 2 == 1
            was_edited = idx % 4 == 0 or idx % 4 == 1

            message = message_args_to_dict(
                chat_id = chat_id,
                domain = domain,
                message_id = str(int(random.random() * 10000)),
                sender = f"TEST_SENDER_{idx}",
                was_edited = was_edited,
                is_reply = is_reply,
                reply_sender = f"TEST_REPLY_{idx}",
                reply_snip = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                timestamp = time.time(),
                text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                files = []
            )
            messages.append(message)

        # return False, ... on error
        return True, {"field": messages}

    # TO BE DELETED LATER SINCE IT'S NOT NEEDED TO CREATE MOCK USERS ANYMORE
    def __create_users(self):
        for idx in range(10):
            self.credentials_worker = CredentialsRequestWorker("localhost:8000", f"fifo{idx}", "Test.Test1", False)
            worker_response = execute_request_loop(self.credentials_worker)
            self.credentials_worker.deleteLater()

            is_error = worker_response.get('is_error')
            if is_error:
                return False, worker_response

        return True, None

    def request_users(self, domain: str, access_token: str):
        # TO BE DELETED LATER SINCE IT'S NOT NEEDED TO CREATE MOCK USERS ANYMORE
        success, resp_data  = self.__create_users()
        if not success:
            print("Could not create all users.")

        self.users_list_worker = UsersListRequestWorker(domain, access_token)
        worker_response = execute_request_loop(self.users_list_worker)
        self.users_list_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response

        users_list = worker_response.get('field').get('items', [])
        return True, {"field": users_list}

    # def request_create_p2p_chat(self, username1: str, username2: str, domain: str):
    #
    #     chat_data = {
    #         "chat_type": "p2p",
    #         "chat_setting": "rw",
    #         "domain": domain,
    #         "chat_id": str(int(random.random() * 10000)),
    #         "display_name": None,
    #         "description": None,
    #         "icon_path": None,
    #         "creator": None,
    #         "last_message_timestamp": 0,
    #         "users":
    #             [{"username": username1,
    #               "is_admin": False,
    #               "last_seen_time": 0},
    #              {"username": username2,
    #               "is_admin": False,
    #               "last_seen_time":0}]
    #     }
    #
    #     # returns False, error_dict if error
    #     return True, {"field": chat_data}
    #
    # def request_create_chatroom(self, domain: str, creator_username: str, users: list):
    #     chat_data = {
    #         "chat_type": "group",
    #         "chat_setting": "rw",
    #         "domain": domain,
    #         "chat_id": str(int(random.random() * 10000)),
    #         "display_name": f"{creator_username}s chatroom",
    #         "description": "",
    #         "icon_path": "./Icons/chat_room_icon.png",
    #         "creator": creator_username,
    #         "last_message_timestamp": 0,
    #         "users":[{
    #             "username": user,
    #             "is_admin": user == creator_username,
    #             "last_seen_time": 0
    #         } for user in users]
    #     }
    #
    #     # return False, error_dict if request fails
    #     return True, {"field": chat_data}

    def request_create_chat(self, domain: str, access_token: str, is_group_chat: bool, name: str,
                            description: str, icon_id: str, participants: dict):
        self.create_chat_worker = CreateChatWorker(domain, access_token, is_group_chat, name, description, icon_id, participants)
        worker_response = execute_request_loop(self.create_chat_worker)
        self.create_chat_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

    def request_get_chat_details(self, domain: str, access_token: str, chat_id: str):
        self.get_chat_details_worker = GetChatDetailsWorker(domain, access_token, chat_id)
        worker_response = execute_request_loop(self.get_chat_details_worker)
        self.get_chat_details_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

    def request_upload_files(self, file_list: list):
        files = []
        if not os.path.isdir(UPLOAD_DIR_PATH):
            os.mkdir(UPLOAD_DIR_PATH)

        for file_path in file_list:
            file_id = str(int(random.random() * 10000))
            file_name = os.path.basename(file_path)
            new_file_path = f"{UPLOAD_DIR_PATH}/{file_id}_{file_name}"
            shutil.copy2(file_path, new_file_path)
            files.append({
                "file_id": file_id,
                "file_name": file_name
            })
            uploaded_files.append({
                "file_id": file_id,
                "file_path": new_file_path
            })

        # return False, error_dict in case of requests error
        return True, {"field": files}

    def request_download_files(self, file_ids: list):
        home_dir = os.path.expanduser('~')
        downloads_folder = os.path.join(home_dir, 'Downloads')

        if not os.path.exists(downloads_folder):
            os.makedirs(downloads_folder)

        for file_id in file_ids:
            file_path = get_file_path(file_id)
            if not file_path: return False, "Download failed" # ERROR INEXISTENT FILE

            file_name = os.path.basename(file_path).split("_", 1)[1]
            base_name, ext = os.path.splitext(file_name)
            save_path = os.path.join(downloads_folder, file_name)

            counter = 1
            while os.path.exists(save_path):
                new_name = f"{base_name} ({counter}){ext}"
                save_path = os.path.join(downloads_folder, new_name)
                counter += 1

            try:
                shutil.copy2(file_path, save_path)
            except Exception as e:
                print(f"Download failed: {e}")

        return True, None

    def request_block_unblock_user(self, domain: str, access_token: str, username: str, block: bool):
        self.block_unblock_worker = BlockUnblockUserWorker(domain, access_token, username, block)
        worker_response = execute_request_loop(self.block_unblock_worker)
        self.block_unblock_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_register_login(self, domain: str, username: str, password: str, login: bool):
        self.credentials_worker = CredentialsRequestWorker(domain, username, password, login)
        worker_response = execute_request_loop(self.credentials_worker)
        self.credentials_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

    def request_get_current_user_profile(self, domain: str, access_token: str):
        self.current_user_profile_worker = CurrentUserProfileWorker(domain, access_token)
        worker_response = execute_request_loop(self.current_user_profile_worker)
        self.current_user_profile_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

    def request_change_user_description(self, domain: str, access_token: str, text: str):
        self.change_user_description_worker = ChangeUserDescriptionWorker(domain, access_token, text)
        worker_response = execute_request_loop(self.change_user_description_worker)
        self.change_user_description_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None