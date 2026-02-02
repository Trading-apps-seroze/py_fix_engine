import socket
import threading
import time
from py_fix_engine.fix_session import FixSession
from py_fix_engine.fix_message import FixMessage

class FixClient: 
    def __init__(self, host, port, sender_id="MY_CLIENT", target_id="SERVER"): 
        self.host = host 
        self.port = port 
        self.sender_id = sender_id
        self.target_id = target_id
        
        self.session = None
        self.is_connected = False
        self.retry_interval = 1
        self.reconnect_thread = None

    def start_client(self): 
        if self.reconnect_thread is None or not self.reconnect_thread.is_alive():
            self.reconnect_thread = threading.Thread(target=self._connection_manager, daemon=True)
            self.reconnect_thread.start()

    def _connection_manager(self): 
        while True: 
            if self.session is None or not self.session.is_running: 
                print(f"Attempting to connect to {self.host}:{self.port}...")
                self._connect()
            time.sleep(self.retry_interval)

    def _connect(self):
        try: 
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            
            # Hand the socket over to the Session
            self.session = FixSession(sock, self.sender_id, self.target_id)
            self.session.start()
            
            print(f"Socket Connected. Starting Session.")
            self._send_logon()
            return True 
        except Exception as ex:
            print(f"Connection failed: {ex}")
            return False 

    def _send_logon(self):
        logon = FixMessage(msg_type="A", sender_id=self.sender_id, target_id=self.target_id)
        logon.add_tag(98, "0") 
        logon.add_tag(108, "1")
        self.session.send_message(logon)

    def stop(self):
        if self.session:
            self.session.stop()