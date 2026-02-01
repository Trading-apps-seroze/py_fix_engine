
import socket 
import threading 
import time 
import os 
import datetime 
from datetime import datetime, timezone 

from py_fix_engine.fix_message import FixMessage


class FixClient: 
    def __init__(self, host, port): 
        self.host = host 
        self.port = port 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.is_running = False 
        
        self.hb_thread = None 
        self.heartbeat_interval = 1 # 1s 

        self.last_sent_time = 0 
        self.reconnect_thread = None 
        self.retry_interval = 1 # 1s 

        self.listener_thread = None 

        self.seq_file = f"CLIENT-1.seq"
        self.out_seq_num = self._load_seq()


    def _load_seq(self):
        """Read the last used sequence from a file, or start at 1."""
        if os.path.exists(self.seq_file):
            with open(self.seq_file, "r") as f:
                return int(f.read().strip())
        return 1

    def _save_seq(self):
        """Persist the current sequence number to disk."""
        with open(self.seq_file, "w") as f:
            f.write(str(self.out_seq_num))


    def send_logon(self):
        """Constructs and sends the initial Logon (35=A) message."""
        logon = FixMessage(msg_type="A", sender_id="SENDER_COMP_ID", target_id="")
        # Tag 98: 0 = None/Other (Encryption method)
        logon.add_tag(98, "0") 
        # Tag 108: Heartbeat interval in seconds
        logon.add_tag(108, str(self.heartbeat_interval))
        self.send_message(logon)


    def _start_heartbeat(self): 
        """Starts the background thread"""
        self.hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True) 
        self.hb_thread.start()


    def _heartbeat_loop(self): 
        """ The loops that runs in the background """
        print(f"Heartbeat thread started (Interval: {self.heartbeat_interval}s)")
        while self.is_running:
            time.sleep(self.heartbeat_interval)
            elapsed = time.time() - self.last_sent_time 

            if elapsed >= self.heartbeat_interval:
                hb_msg = FixMessage(msg_type="0", sender_id="MY_CLIENT", target_id="SERVER")
                self.send_message(hb_msg)
                print(f"DEBUG: Sent Heartbeat")

    def start_client(self): 
        """Starts the connection manager thread."""
        if self.reconnect_thread is None or not self.reconnect_thread.is_alive():
            self.reconnect_thread = threading.Thread(target=self._connection_manager, daemon=True)
            self.reconnect_thread.start()
            print("Connection Manager started...")


    def _connection_manager(self): 
        while True: 
            if not self.is_running: 
                print(f"Attempting to connect to {self.host} {self.port}...")
                success = self._connect()
                if not success: 
                    print("Connection failed. Retrying in {self.retry_interval}")
                    time.sleep(self.retry_interval) 
                    # Production Tip: Increase interval here for exponential backoff
                    continue

            # reconnect after 1s 
            time.sleep(1)


    def _connect(self):
        try: 
            # Initialize a fresh socket each time as we cannot use socket object after 
            # failure, we have to garbage collect this 
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(5)  # Give up after 5 seconds

            self.is_running = True 

            self._start_heartbeat() # start hb background thread 
            
            self.listener_thread = threading.Thread(target = self._listen, daemon=True)
            self.listener_thread.start()

            print(f"Connected to {self.host}:{self.port}")

            self.send_logon() # send logon (35=A)
            return True 
        except Exception as ex:
            print(f"Connection failed: {ex}")
            return False 


    def send_message(self, fix_message: FixMessage): 
        if self.is_running: 

            # 1. Assign current sequence
            fix_message.add_tag(34, str(self.out_seq_num))
            
            # 2. Increment and Save IMMEDIATELY (Atomic-ish)
            self.out_seq_num += 1
            self._save_seq()


            # 3. Add SendingTime (Tag 52) - Format: YYYYMMDD-HH:MM:SS.mmm
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%d-%H:%M:%S.%f")[:-3] # Truncate to milliseconds
            fix_message.add_tag(52, timestamp)

            raw_fix_message = fix_message.encode() # returns str 
            
            self.socket.sendall(raw_fix_message.encode())
            self.last_sent_time = time.time()
            print(f"SENT: {raw_fix_message.replace(f'{FixMessage.SOH}', '|')}")

    def _listen(self):

        while self.is_running: 
            try: 
                data = self.socket.recv(4096)
                if not data: 
                    print("Connection closed by server.")
                    self.is_running = False 
                    break 

                print(f"RECV: {data.replace(b'\x01', b'|')}")

            except Exception as ex: 
                print(f"Error receiving data: {ex}")
                self.is_running = False 

    def stop(self):
        self.is_running = False 
        self.socket.close()


""" 
2. Handling the "Streaming" Problem
In the real world, socket.recv(4096) might return half of a FIX message or two messages 
stuck together. This is a common point of failure for beginners.

To solve this, your listener needs a Buffer. You should append incoming bytes to a buffer
and then "extract" complete messages by looking for the 10=xxx\x01 trailer.

"""