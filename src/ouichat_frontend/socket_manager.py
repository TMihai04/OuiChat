import time
import random
import os
import shutil
from PyQt6.QtCore import pyqtSignal, QObject

UPLOAD_DIR_PATH = "./Uploads/"

uploaded_files = []

def get_file_path(file_id: int):
    for file_entry in uploaded_files:
        if file_entry["file_id"] == file_id:
            return file_entry["file_path"]

    return None

def message_args_to_dict(chat_id: str, domain: str, message_id: str, sender: str, sender_icon_path: str,
                         was_edited: bool, is_reply: bool, reply_sender: str, reply_sender_icon_path: str,
                         reply_snip: str, timestamp: float, text: str, files: list):
    return {
        "chat_id": chat_id,
        "domain": domain,
        "message_id": message_id,
        "sender": sender,
        "sender_icon_path": sender_icon_path,
        "was_edited": was_edited,
        "is_reply": is_reply,
        "reply_sender": reply_sender,
        "reply_sender_icon_path": reply_sender_icon_path,
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

    def request_chats(self, username: str, domain: str):

        chats = []
        for idx in reversed(range(20)):  # adding 20 chat rooms to the list
            chat_data = {
                "chat_type": "chatroom",  # {"chatroom", "p2p"}
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

        return chats

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
                sender_icon_path = "./Icons/default_user_icon.png",
                was_edited = was_edited,
                is_reply = is_reply,
                reply_sender = f"TEST_REPLY_{idx}",
                reply_sender_icon_path = "./Icons/default_user_icon.png",
                reply_snip = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                timestamp = time.time(),
                text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                files = []
            )
            messages.append(message)

        return messages

    def request_users(self, domain: str):
        ret = [{
            "username": "fifo",
            "icon_path": "./Icons/default_user_icon.png",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        }, *[{
            "username": f"fifo{idx}",
            "icon_path": "./Icons/default_user_icon.png",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        } for idx in reversed(range(10))]]

        return ret

    def request_create_p2p_chat(self, username1: str, username2: str, domain: str):

        chat_data = {
            "chat_type": "p2p",
            "chat_setting": "rw",
            "domain": domain,
            "chat_id": str(int(random.random() * 10000)),
            "display_name": None,
            "description": None,
            "icon_path": None,
            "creator": None,
            "last_message_timestamp": 0,
            "users":
                [{"username": username1,
                  "is_admin": False,
                  "last_seen_time": 0},
                 {"username": username2,
                  "is_admin": False,
                  "last_seen_time":0}]
        }

        # returns None if error
        return chat_data

    def request_create_chatroom(self, domain: str, creator_username: str, users: list):
        chat_data = {
            "chat_type": "chatroom",
            "chat_setting": "rw",
            "domain": domain,
            "chat_id": str(int(random.random() * 10000)),
            "display_name": f"{creator_username}s chatroom",
            "description": "",
            "icon_path": "./Icons/chat_room_icon.png",
            "creator": creator_username,
            "last_message_timestamp": 0,
            "users":[{
                "username": user,
                "is_admin": user == creator_username,
                "last_seen_time": 0
            } for user in users]
        }

        return chat_data

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

        return files

    def request_download_files(self, file_ids: list):
        home_dir = os.path.expanduser('~')
        downloads_folder = os.path.join(home_dir, 'Downloads')

        if not os.path.exists(downloads_folder):
            os.makedirs(downloads_folder)

        for file_id in file_ids:
            file_path = get_file_path(file_id)
            if not file_path: return # ERROR INEXISTENT FILE

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