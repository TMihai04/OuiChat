import time

def message_args_to_dict(chat_id: str, domain: str, message_id: str, sender: str, sender_icon_path: str,
                         was_edited: bool, is_reply: bool, reply_sender: str, reply_sender_icon_path: str,
                         reply_snip: str, timestamp: str, text: str):
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
        "text": text
    }

class SocketManager:
    """
    TO DO:
        - implement request/websocket communication
    """
    def __init__(self):
        super().__init__()

    def request_chats(self, username: str, domain: str):

        chats = []
        for idx in range(20):  # adding 20 chat rooms to the list
            chat_data = {
                "chat_type": "chatroom",  # {"chatroom", "p2p"}
                "chat_setting": "rw",  # {"rw", "ro"}
                "domain": "test.test.ro" if idx < 10 else "test2.test2.ro",
                "chat_id": str(idx),
                "chat_description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                "icon_path": "./Icons/chat_room_icon.png",
                "users": [{"username": "fifo",
                           "icon_path": "./Icons/default_user_icon.png",
                           "is_admin": True}] if idx < 5 else
                [{"username": "fifo",
                  "icon_path": "./Icons/default_user_icon.png",
                  "is_admin": True},
                 {"username": "fifo2",
                  "icon_path": "./Icons/default_user_icon.png",
                  "is_admin": False}] if idx < 10 else
                [{"username": "fifo2",
                  "icon_path": "./Icons/default_user_icon.png",
                  "is_admin": True}]
            }
            chats.append(chat_data)

        return chats

    def request_messages(self, chat_id: str, domain: str, oldest_message_id: str, message_nr: int):

        messages = []
        for idx in range(20):
            is_reply = idx % 2 == 1
            was_edited = idx % 4 == 0 or idx % 4 == 1

            local_time = time.localtime(time.time())
            formated_time = time.strftime("%H:%M:%S %d/%m/%Y", local_time)

            message = message_args_to_dict(
                chat_id = chat_id,
                domain = domain,
                message_id = f"{idx}",
                sender = f"TEST_SENDER_{idx}",
                sender_icon_path = "./Icons/default_user_icon.png",
                was_edited = was_edited,
                is_reply = is_reply,
                reply_sender = "TEST_REPLY_{idx}",
                reply_sender_icon_path = "./Icons/default_user_icon.png",
                reply_snip = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
                timestamp = formated_time,
                text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
            )
            messages.append(message)

        return messages