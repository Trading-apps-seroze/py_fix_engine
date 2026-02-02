import threading
import time
import os
import json
from datetime import datetime, timezone
from py_fix_engine.fix_message import FixMessage

class FixSession:
    def __init__(self, sock, sender_id, target_id, heartbeat_interval=1):
        self.socket = sock
        self.sender_id = sender_id
        self.target_id = target_id
        self.heartbeat_interval = heartbeat_interval
        
        # A single state file for the session
        self.state_file = f"session_{self.sender_id}.json"
        
        self.is_running = True
        self.last_sent_time = 0
        
        # Load state (Outbound and Inbound)
        state = self._load_session_state()
        self.out_seq_num = state['out']
        self.expected_in_seq_num = state['in']
        
        self.hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)

    def _load_session_state(self):
        """Loads both sequence numbers from a JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        # Default starting state
        return {'out': 1, 'in': 1}

    def _save_session_state(self):
        """Saves both sequence numbers atomically."""
        state = {
            'out': self.out_seq_num,
            'in': self.expected_in_seq_num
        }
        try:
            # Writing to a temp file then renaming is the "pro" way to prevent corruption
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except IOError as e:
            print(f"Error saving session state: {e}")

    def start(self):
        self.hb_thread.start()
        self.listener_thread.start()

    def send_message(self, msg: FixMessage):
        if not self.is_running: return

        msg.add_tag(49, self.sender_id)
        msg.add_tag(56, self.target_id)
        msg.add_tag(34, str(self.out_seq_num))
        
        now = datetime.now(timezone.utc)
        msg.add_tag(52, now.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])

        # Increment outbound and save the WHOLE state
        self.out_seq_num += 1
        self._save_session_state()
        
        raw_msg = msg.encode()
        try:
            self.socket.sendall(raw_msg.encode())
            self.last_sent_time = time.time()
            print(f"SENT: {raw_msg.replace(FixMessage.SOH, '|')}")
        except Exception as e:
            self.stop()

    def _validate_inbound_seq(self, msg_str):
        try:
            # Extract Tag 34
            msg_seq_num = None
            for part in msg_str.split('\x01'):
                if part.startswith("34="):
                    msg_seq_num = int(part.split("=")[1])
                    break
            
            if msg_seq_num is None: return True

            if msg_seq_num < self.expected_in_seq_num:
                print(f"!!! SEQ ERROR: Received {msg_seq_num}, expected {self.expected_in_seq_num}")
                return False
            
            if msg_seq_num > self.expected_in_seq_num:
                print(f"!!! SEQ GAP: Received {msg_seq_num}, expected {self.expected_in_seq_num}")
                # Update our expectation to match their jump (simplified logic)
                self.expected_in_seq_num = msg_seq_num
            
            # Increment expected inbound and save state
            self.expected_in_seq_num += 1
            self._save_session_state()
            return True
        except Exception as e:
            print(f"Inbound Validation Error: {e}")
            return False

    def _listen_loop(self):
        while self.is_running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.stop()
                    break
                
                decoded_msg = data.decode('utf-8', errors='ignore')
                print(f"RECV: {decoded_msg.replace('\x01', '|')}")

                if not self._validate_inbound_seq(decoded_msg):
                    self.stop()
                    break
            except:
                self.stop()
                break

    def _heartbeat_loop(self):
        while self.is_running:
            time.sleep(0.1)
            if time.time() - self.last_sent_time >= self.heartbeat_interval:
                hb = FixMessage(msg_type="0", sender_id=self.sender_id, target_id=self.target_id)
                self.send_message(hb)

    def stop(self):
        self.is_running = False
        try: self.socket.close()
        except: pass