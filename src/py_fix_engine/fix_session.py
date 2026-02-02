import threading
import time
from datetime import datetime, timezone
from py_fix_engine.fix_message import FixMessage

class FixSession:
    def __init__(self, sock, sender_id, target_id, heartbeat_interval=1):
        self.socket = sock
        self.sender_id = sender_id
        self.target_id = target_id
        self.heartbeat_interval = heartbeat_interval
        
        self.is_running = True
        self.last_sent_time = 0
        self.out_seq_num = 1 # In production, load this from a file
        
        # Threads
        self.hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)

    def start(self):
        """Starts the session workers."""
        self.hb_thread.start()
        self.listener_thread.start()

    def send_message(self, msg: FixMessage):
        if not self.is_running: return

        # Fill in Session Headers
        msg.add_tag(49, self.sender_id)
        msg.add_tag(56, self.target_id)
        msg.add_tag(34, str(self.out_seq_num))
        
        # Add Timestamp (Tag 52)
        now = datetime.now(timezone.utc)
        msg.add_tag(52, now.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])

        self.out_seq_num += 1
        raw_msg = msg.encode()
        
        try:
            self.socket.sendall(raw_msg.encode())
            self.last_sent_time = time.time()
            print(f"SENT: {raw_msg.replace(FixMessage.SOH, '|')}")
        except Exception as e:
            print(f"Send Error: {e}")
            self.stop()

    def _heartbeat_loop(self):
        while self.is_running:
            time.sleep(0.1) 
            if time.time() - self.last_sent_time >= self.heartbeat_interval:
                hb = FixMessage(msg_type="0", sender_id=self.sender_id, target_id=self.target_id)
                self.send_message(hb)

    def _listen_loop(self):
        buffer = b""
        while self.is_running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    print("Session disconnected by remote.")
                    self.stop()
                    break
                
                # Logic for handling the "Streaming Problem" would go here
                print(f"RECV: {data.replace(b'\x01', b'|')}")
                
            except Exception as e:
                print(f"Listen Error: {e}")
                self.stop()
                break

    def stop(self):
        self.is_running = False
        try:
            self.socket.close()
        except:
            pass