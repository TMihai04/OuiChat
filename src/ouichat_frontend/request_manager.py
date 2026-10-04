import json
import time
import random
import os
from typing import Any
import aiohttp
import asyncio
from PyQt6.QtCore import pyqtSignal, QObject, QThread, QEventLoop
from dotenv import load_dotenv

MAX_REQUESTS = 2 # previously 5
REQUEST_TIMEOUT = 2

DEBUG = True

uploaded_files = []

load_dotenv()
environment = os.getenv('ENVIRONMENT')
if environment == 'local':
    protocol = 'http'
else:
    protocol = 'https'

def get_resp_dict(is_error: bool, code: int, field: Any):
    return {
        "is_error": is_error,
        "code": code,
        "field": field
    }

async def handle_error(response: aiohttp.ClientResponse):
    code = response.status
    if DEBUG:
        print(code)
        print(await response.text())
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
                async with session.post(url=f"{protocol}://{domain}/api/{endpoint}", data=register_json) as resp:
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
                async with session.get(url=f"{protocol}://{domain}/api/users/me", headers=headers) as resp:
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
                async with session.post(url=f"{protocol}://{domain}/api/users/profile/status", headers=headers, json=body) as resp:
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

async def change_user_icon(domain: str, access_token: str, icon_id: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    body = {
        "icon_id": icon_id,
    }

    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/users/profile/picture", headers=headers, json=body) as resp:
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

class ChangeUserIconWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, icon_id: str):
        super().__init__()

        self.domain = domain
        self.access_token = access_token
        self.icon_id = icon_id

    def run(self):
        resp = asyncio.run(change_user_icon(domain=self.domain, access_token=self.access_token, icon_id=self.icon_id))
        self.finished.emit(resp)

async def get_users_list_request(domain: str, access_token: str):
    headers = {
        'Authorization': f"Bearer {access_token}",
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"{protocol}://{domain}/api/users/list", headers=headers) as resp:
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
                async with request_type(url=f"{protocol}://{domain}/api/users/preferences/blacklist", headers=headers, json=body) as resp:
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
                async with session.post(url=f"{protocol}://{domain}/api/refresh", headers=headers) as resp:
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
            "picture_id": icon_id if icon_id != "" else None
        },
        "participants": participants
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/chats/create", headers=headers, json=body) as resp:
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
                async with session.get(url=f"{protocol}://{domain}/api/chats/chat", headers=headers, params=params) as resp:
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

async def get_chats_request(domain: str, access_token: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"{protocol}://{domain}/api/chats/list", headers=headers) as resp:
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

class GetChatsWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token

    def run(self):
        resp = asyncio.run(get_chats_request(domain=self.domain, access_token=self.access_token))
        self.finished.emit(resp)

async def modify_admin_request(domain: str, access_token: str, chat_id: str, users: dict):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = {
        "admins": users
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/chats/participant/admin", headers=headers, params=params, json=body) as resp:
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

class ModifyAdminWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, users: dict):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.users = users

    def run(self):
        resp = asyncio.run(modify_admin_request(domain=self.domain, access_token=self.access_token, chat_id=self.chat_id, users=self.users))
        self.finished.emit(resp)

async def modify_users_request(domain: str, access_token: str, chat_id: str, usernames: list, add: bool):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = {
        "who": usernames
    }
    endpoint = "add" if add else "remove"
    req = "POST" if add else "DELETE"
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.request(method=req, url=f"{protocol}://{domain}/api/chats/participant/{endpoint}", headers=headers, params=params, json=body) as resp:
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

class ModifyUsersWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, usernames: list, add: bool):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.usernames = usernames
        self.add = add

    def run(self):
        resp = asyncio.run(modify_users_request(domain=self.domain, access_token=self.access_token, chat_id=self.chat_id, usernames=self.usernames, add=self.add))
        self.finished.emit(resp)

async def leave_chat_request(domain: str, access_token: str, chat_id: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.delete(url=f"{protocol}://{domain}/api/chats/participant/leave", headers=headers, params=params) as resp:
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

class LeaveChatWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id

    def run(self):
        resp = asyncio.run(leave_chat_request(domain=self.domain, access_token=self.access_token, chat_id=self.chat_id))
        self.finished.emit(resp)

async def modify_chat_details(domain: str, access_token: str, chat_id: str, text: str, field: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = {
        field: text
    }
    endpoint = "picture" if field == "icon_id" else field
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/chats/preferences/{endpoint}", headers=headers, params=params, json=body) as resp:
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

class ModifyChatDetailsWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, text: str, field: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.text = text
        self.field = field

    def run(self):
        resp = asyncio.run(modify_chat_details(self.domain, self.access_token, self.chat_id, self.text, self.field))
        self.finished.emit(resp)

async def upload_file_request(domain: str, access_token: str, absolute_file_path: str, file_type: str):
    filename = os.path.basename(absolute_file_path)
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/octet-stream',
        'X-Original-Filename': filename
    }
    params = {
        'file_type': file_type
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                with open(absolute_file_path, 'rb') as file:
                    async with session.post(url=f"{protocol}://{domain}/api/attachments/upload", headers=headers, params=params, data=file) as resp:
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

class UploadFileWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, absolute_file_path: str, file_type: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.absolute_file_path = absolute_file_path
        self.file_type = file_type

    def run(self):
        resp = asyncio.run(upload_file_request(self.domain, self.access_token, self.absolute_file_path, self.file_type))
        self.finished.emit(resp)

async def download_file_request(domain: str, access_token: str, file_id: str, path: str | None):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'file_id': file_id
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"{protocol}://{domain}/api/attachments/download", headers=headers, params=params) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    cd_header = resp.headers.get('Content-Disposition', '')
                    filename = f"download_{file_id}"
                    if "filename=" in cd_header:
                        filename = cd_header.split("filename=")[-1].strip(' "\'')

                    if path is None:
                        user_path = os.path.expanduser('~')
                        downloads_path = os.path.join(user_path, 'Downloads')
                        if not os.path.exists(downloads_path):
                            os.makedirs(downloads_path)

                        base_name, ext = os.path.splitext(filename)
                        save_path = os.path.join(downloads_path, filename)
                        counter = 1
                        while os.path.exists(save_path):
                            save_path = os.path.join(downloads_path, f"{base_name} ({counter}){ext}")
                            counter += 1

                    else:
                        _, ext = os.path.splitext(filename)
                        save_path = f'{path}/{file_id}{ext}'

                    with open(save_path, 'wb') as file:
                        async for chunk in resp.content.iter_chunked(8192):
                            file.write(chunk)

                    return get_resp_dict(False, resp.status, save_path)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class DownloadFileWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, file_id: str, path: str | None):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.file_id = file_id
        self.path = path

    def run(self):
        resp = asyncio.run(download_file_request(self.domain, self.access_token, self.file_id, self.path))
        self.finished.emit(resp)

async def send_message_request(domain: str, access_token: str, chat_id: str, text: str | None, file_ids: list | None, replied_to: str | None):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = dict()
    if text: body['content'] = text
    if file_ids: body['attachments'] = file_ids
    if replied_to: body['replied_to'] = replied_to
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/messages/send", headers=headers, params=params, json=body) as resp:
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

class SendMessageWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, text: str | None, file_ids: list | None, replied_to: str | None):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.text = text
        self.file_ids = file_ids
        self.replied_to = replied_to

    def run(self):
        resp = asyncio.run(send_message_request(self.domain, self.access_token, self.chat_id, self.text, self.file_ids, self.replied_to))
        self.finished.emit(resp)

async def edit_message_request(domain: str, access_token: str, chat_id: str, message_id: str, text: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = {
        'message_id': message_id,
        'new_content': text
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.post(url=f"{protocol}://{domain}/api/messages/edit", headers=headers, params=params, json=body) as resp:
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

class EditMessageWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, message_id: str, text: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.message_id = message_id
        self.text = text

    def run(self):
        resp = asyncio.run(edit_message_request(self.domain, self.access_token, self.chat_id, self.message_id, self.text))
        self.finished.emit(resp)

async def delete_message_request(domain: str, access_token: str, chat_id: str, message_id: str):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id
    }
    body = {
        'message_id': message_id,
    }
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.delete(url=f"{protocol}://{domain}/api/messages/delete", headers=headers, params=params,
                                        json=body) as resp:
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

class DeleteMessageWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, message_id: str):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.message_id = message_id

    def run(self):
        resp = asyncio.run(delete_message_request(self.domain, self.access_token, self.chat_id, self.message_id))
        self.finished.emit(resp)

async def get_messages_request(domain: str, access_token: str, chat_id: str, direction: str | None, message_id: str | None, batch_size: int | None):
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'chat_id': chat_id,
        'direction': direction if direction else "",
    }
    if message_id: params['message_id'] = message_id
    if batch_size: params['batch_size'] = str(batch_size)
    async with aiohttp.ClientSession() as session:
        for request_count in range(MAX_REQUESTS):
            try:
                async with session.get(url=f"{protocol}://{domain}/api/messages/list", headers=headers, params=params) as resp:
                    try:
                        resp.raise_for_status()
                    except aiohttp.ClientResponseError as _:
                        return await handle_error(resp)

                    messages = []
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            json_str = line[len('data:'):].strip()
                            if json_str:
                                messages.append(json.loads(json_str))

                    return get_resp_dict(False, resp.status, messages)

            except (aiohttp.ClientError, asyncio.TimeoutError) as _:
                await asyncio.sleep(REQUEST_TIMEOUT * request_count)
                continue

        return get_resp_dict(True, 408, 'Cannot establish a connection with the server.')

class GetMessagesWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, domain: str, access_token: str, chat_id: str, direction: str | None, message_id: str | None, batch_size: int | None):
        super().__init__()
        self.domain = domain
        self.access_token = access_token
        self.chat_id = chat_id
        self.direction = direction
        self.message_id = message_id
        self.batch_size = batch_size

    def run(self):
        resp = asyncio.run(get_messages_request(self.domain, self.access_token, self.chat_id, self.direction, self.message_id, self.batch_size))
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

class RequestManager(QObject):
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
        self.change_user_icon_worker = None
        self.refresh_tokens_worker = None
        self.create_chat_worker = None
        self.get_chat_details_worker = None
        self.get_chats_worker = None
        self.modify_admin_worker = None
        self.add_users_worker = None
        self.leave_chat_worker = None
        self.modify_chat_details_worker = None
        self.upload_files_worker = None
        self.download_file_worker = None
        self.send_messages_worker = None
        self.edit_message_worker = None
        self.delete_message_worker = None
        self.get_messages_worker = None

    def request_chats(self, domain: str, access_token: str):
        self.get_chats_worker = GetChatsWorker(domain, access_token)
        worker_response = execute_request_loop(self.get_chats_worker)
        self.get_chats_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response

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

        white = worker_response.get('field', dict()).get('item', dict()).get('white', [])
        black = worker_response.get('field', dict()).get('item', dict()).get('black', [])
        return True, {"field": {
            "white": white,
            "black": black
        }}

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

    def request_upload_files(self, domain: str, access_token: str, file_list: list):
        successfully_uploaded_files = []
        for file_path, file_type in file_list:
            self.upload_files_worker = UploadFileWorker(domain, access_token, file_path, file_type)
            worker_response = execute_request_loop(self.upload_files_worker)
            self.upload_files_worker.deleteLater()

            is_error = worker_response.get('is_error')
            if is_error:
                return False, worker_response, successfully_uploaded_files

            file_id = worker_response.get('field', dict()).get('item', dict()).get('file_id')
            successfully_uploaded_files.append({
                'file_id': file_id,
                'file_name': os.path.basename(file_path),
            })

        return True, None, successfully_uploaded_files

    def request_download_file(self, domain: str, access_token: str, file_id: str, path: str | None):
        self.download_file_worker = DownloadFileWorker(domain, access_token, file_id, path)
        worker_response = execute_request_loop(self.download_file_worker)
        self.download_file_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, worker_response.get('field')

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

    def request_change_user_icon(self, domain: str, access_token: str, icon_id: str):
        self.change_user_icon_worker = ChangeUserIconWorker(domain, access_token, icon_id)
        worker_response = execute_request_loop(self.change_user_icon_worker)
        self.change_user_icon_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_modify_admin(self, domain: str, access_token: str, chat_id: str, users: dict):
        self.modify_admin_worker = ModifyAdminWorker(domain, access_token, chat_id, users)
        worker_response = execute_request_loop(self.modify_admin_worker)
        self.modify_admin_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_modify_users(self, domain: str, access_token: str, chat_id: str, usernames: list, add: bool):
        self.add_users_worker = ModifyUsersWorker(domain, access_token, chat_id, usernames, add)
        worker_response = execute_request_loop(self.add_users_worker)
        self.add_users_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_leave_chat(self, domain: str, access_token: str, chat_id: str):
        self.leave_chat_worker = LeaveChatWorker(domain, access_token, chat_id)
        worker_response = execute_request_loop(self.leave_chat_worker)
        self.leave_chat_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_modify_chat_details(self, domain: str, access_token: str, chat_id: str, text: str, field: str):
        self.modify_chat_details_worker = ModifyChatDetailsWorker(domain, access_token, chat_id, text, field)
        worker_response = execute_request_loop(self.modify_chat_details_worker)
        self.modify_chat_details_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_modify_chat_name(self, domain: str, access_token: str, chat_id: str, name: str):
        return self.request_modify_chat_details(domain, access_token, chat_id, name, "name")

    def request_modify_chat_description(self, domain: str, access_token: str, chat_id: str, desc: str):
        return self.request_modify_chat_details(domain, access_token, chat_id, desc, "description")

    def request_modify_chat_icon(self, domain: str, access_token: str, chat_id: str, icon_id: str):
        return self.request_modify_chat_details(domain, access_token, chat_id, icon_id, "icon_id")

    def request_send_message(self, domain: str, access_token: str, chat_id: str, text: str | None, file_ids: list | None, replied_to: str | None):
        self.send_messages_worker = SendMessageWorker(domain, access_token, chat_id, text, file_ids, replied_to)
        worker_response = execute_request_loop(self.send_messages_worker)
        self.send_messages_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_edit_message(self, domain: str, access_token: str, chat_id: str, message_id: str, text: str):
        self.edit_message_worker = EditMessageWorker(domain, access_token, chat_id, message_id, text)
        worker_response = execute_request_loop(self.edit_message_worker)
        self.edit_message_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_delete_message(self, domain: str, access_token: str, chat_id: str, message_id: str):
        self.delete_message_worker = DeleteMessageWorker(domain, access_token, chat_id, message_id)
        worker_response = execute_request_loop(self.delete_message_worker)
        self.delete_message_worker.deleteLater()

        is_error = worker_response.get('is_error')
        if is_error:
            return False, worker_response
        return True, None

    def request_get_messages(self, domain: str, access_token: str, chat_id: str, direction: str | None, message_id: str | None, batch_size: int | None):
        self.get_messages_worker = GetMessagesWorker(domain, access_token, chat_id, direction, message_id, batch_size)
        worker_response = execute_request_loop(self.get_messages_worker)
        self.get_messages_worker.deleteLater()

        is_error = worker_response.get('is_error')
        return not is_error, worker_response
