import json
import websocket
import time
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class WebSocketManager(QObject):
    """
    TO DO:
        - test websockets more thoroughly
    """

    message_received = pyqtSignal(str, str, dict)
    connection_error = pyqtSignal(str, str, str)
    disconnected = pyqtSignal(str, str, bool)
    retry_failed = pyqtSignal(str, str)

    MAX_EVENT_QUEUE_SIZE = 512

    def __init__(self):
        super().__init__()

        self.websockets = []
        self.handled_events_ids = []

    def connect_websocket(self, domain: str, access_token: str):
        new_ws = WebSocketListener(domain, access_token)
        new_ws.message_received.connect(self.handle_event)
        new_ws.connection_error.connect(self.connection_error.emit)
        new_ws.disconnected.connect(self.disconnected.emit)
        new_ws.disconnected.connect(self.clean_up_dead_websocket_on_logout)
        new_ws.finished.connect(new_ws.deleteLater)
        new_ws.retry_failed.connect(self.clean_up_dead_websocket)
        new_ws.retry_failed.connect(self.retry_failed.emit)
        self.websockets.append(new_ws)
        new_ws.start()

    def clean_up_dead_websocket_on_logout(self, domain: str, access_token: str, user_logout: bool):
        if user_logout:
            self.clean_up_dead_websocket(domain, access_token)

    def clean_up_dead_websocket(self, domain: str, access_token: str):
        for ws in self.websockets[:]:
            if ws.domain == domain and ws.access_token == access_token:
                self.websockets.remove(ws)
                break

    def remove_websocket(self, ws: WebSocketListener):
        self.websockets.remove(ws)

    def disconnect_websocket(self, domain: str, access_token: str):
        for ws in self.websockets[:]: # temp copy of the list
            if ws.domain == domain and ws.access_token == access_token:
                ws.stop()
                ws.wait()
                self.websockets.remove(ws)
                break

    def send_message(self, domain: str, access_token: str, message: dict):
        for ws in self.websockets[:]:
            if ws.domain == domain and ws.access_token == access_token:
                ws.send_message(message)
                return

    def handle_event(self, domain: str, access_token: str, event_data: dict):
        # UNCOMMENT WHEN event_id

        # event_id = event_data["event_id"]
        # if event_id in self.handled_events_ids: return

        self.message_received.emit(domain, access_token, event_data)

        if len(self.handled_events_ids) > self.MAX_EVENT_QUEUE_SIZE:
            self.handled_events_ids.pop(0)
        # self.handled_events_ids.append(event_id)

class WebSocketListener(QThread):
    message_received = pyqtSignal(str, str, dict)
    connection_error = pyqtSignal(str, str, str)
    disconnected = pyqtSignal(str, str, bool)
    retry_failed = pyqtSignal(str, str)

    def __init__(self, domain: str, access_token: str):
        super().__init__()
        self.url = f"ws://{domain}/ws/global?token={access_token}"
        self.domain = domain
        self.access_token = access_token
        self.ws = None
        self.is_running = True
        self.max_retries = 3
        self.retry_delay = 2

    def update_access_token(self, access_token: str):
        self.access_token = access_token
        # data = {
        #
        # }
        # self.send_message(data)

    def run(self):
        attempts = 0
        while attempts < self.max_retries and self.is_running:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            print("WS connected")
            self.ws.run_forever()
            print("WS disconnected")
            if not self.is_running:
                break

            attempts += 1
            if attempts < self.max_retries:
                time.sleep(self.retry_delay * attempts)

        if attempts >= self.max_retries:
            self.retry_failed.emit(self.domain, self.access_token)

    def on_open(self, _):
        self.is_running = True

    def on_message(self, _, message):
        data = json.loads(message)
        self.message_received.emit(self.domain, self.access_token, data)

    def on_error(self, _, error):
        self.connection_error.emit(self.domain, self.access_token, str(error))
        if self.ws:
            self.ws.close()

    def on_close(self, _, __, ___):
        user_logout = not self.is_running
        self.disconnected.emit(self.domain, self.access_token, user_logout)

    def send_message(self, data_dict: dict):
        # IMPLEMENT AND SEND THE DATA WITH THE CORRECT FORMAT
        # FIELD DE "access_token": new_token (str)
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send_bytes(json.dumps(data_dict))

    def stop(self):
        self.is_running = False
        if self.ws:
            self.ws.close()