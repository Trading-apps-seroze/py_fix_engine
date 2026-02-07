import threading
import time
import os
import json
from datetime import datetime, timezone
from py_fix_engine.fix_message import FixMessage
from py_fix_engine.fix_message_store import FixMessageStore
from py_fix_engine.fix_parser import extract_tag

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

        # Message store for resend support
        self.message_store = FixMessageStore(self.sender_id)

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

        raw_msg = msg.encode()

        # Persist to message store before incrementing
        self.message_store.store(self.out_seq_num, raw_msg)

        # Increment outbound and save the WHOLE state
        self.out_seq_num += 1
        self._save_session_state()

        try:
            self.socket.sendall(raw_msg.encode())
            self.last_sent_time = time.time()
            print(f"SENT: {raw_msg.replace(FixMessage.SOH, '|')}")
        except Exception as e:
            self.stop()

    def _validate_inbound_seq(self, msg_str):
        try:
            msg_seq_num_str = extract_tag(msg_str, 34)
            if msg_seq_num_str is None:
                return True

            msg_seq_num = int(msg_seq_num_str)

            if msg_seq_num < self.expected_in_seq_num:
                # Check PossDupFlag — duplicates with 43=Y are acceptable
                poss_dup = extract_tag(msg_str, 43)
                if poss_dup == "Y":
                    return True
                print(f"!!! SEQ ERROR: Received {msg_seq_num}, expected {self.expected_in_seq_num}")
                return False

            if msg_seq_num > self.expected_in_seq_num:
                print(f"!!! SEQ GAP: Received {msg_seq_num}, expected {self.expected_in_seq_num}. Sending Resend Request.")
                self._send_resend_request(self.expected_in_seq_num, 0)
                # Jump forward to accept the current message
                self.expected_in_seq_num = msg_seq_num

            # Increment expected inbound and save state
            self.expected_in_seq_num += 1
            self._save_session_state()
            return True
        except Exception as e:
            print(f"Inbound Validation Error: {e}")
            return False

    def _send_resend_request(self, begin_seq, end_seq):
        """Send a Resend Request (35=2) asking for messages from begin_seq to end_seq.

        end_seq=0 means "send everything from begin_seq onwards".
        """
        msg = FixMessage(msg_type="2", sender_id=self.sender_id, target_id=self.target_id)
        msg.add_tag(7, str(begin_seq))
        msg.add_tag(16, str(end_seq))
        self.send_message(msg)

    def _handle_resend_request(self, msg_str):
        """Handle an incoming Resend Request (35=2).

        Look up stored messages and resend them with PossDupFlag=Y.
        For any gaps in the store, send a Sequence Reset - Gap Fill.
        """
        begin_str = extract_tag(msg_str, 7)
        end_str = extract_tag(msg_str, 16)
        if begin_str is None or end_str is None:
            print("!!! Invalid Resend Request: missing BeginSeqNo or EndSeqNo")
            return

        begin = int(begin_str)
        end = int(end_str)
        print(f"Handling Resend Request: BeginSeqNo={begin}, EndSeqNo={end}")

        stored = self.message_store.get_range(begin, end)

        # Determine the actual end: if end=0, use our current out_seq_num - 1
        actual_end = end if end != 0 else self.out_seq_num - 1

        seq = begin
        while seq <= actual_end:
            if seq in stored:
                # Resend the original message with PossDupFlag=Y injected
                original = stored[seq]
                resend_str = self._inject_poss_dup(original)
                try:
                    self.socket.sendall(resend_str.encode())
                    self.last_sent_time = time.time()
                    print(f"RESENT (PossDup): seq={seq}")
                except Exception:
                    self.stop()
                    return
                seq += 1
            else:
                # Find the extent of the gap in the store
                gap_start = seq
                while seq <= actual_end and seq not in stored:
                    seq += 1
                new_seq = seq  # First available seq after the gap
                self._send_sequence_reset_gap_fill(gap_start, new_seq)

    def _inject_poss_dup(self, raw_msg):
        """Inject PossDupFlag=Y (tag 43) into a raw FIX message string and update SendingTime."""
        # Insert 43=Y right after the sequence number tag (34=...)
        parts = raw_msg.split('\x01')
        result = []
        for part in parts:
            result.append(part)
            if part.startswith("34="):
                result.append("43=Y")
            # Update sending time to now
            if part.startswith("52="):
                now = datetime.now(timezone.utc)
                result[-1] = "52=" + now.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

        rebuilt = '\x01'.join(result)
        # Recalculate checksum
        # Strip old checksum
        cs_idx = rebuilt.find('\x0110=')
        if cs_idx != -1:
            body = rebuilt[:cs_idx + 1]  # include the SOH before 10=
        else:
            body = rebuilt
        checksum = FixMessage.calculate_checksum(body)
        return f"{body}10={checksum}\x01"

    def _send_sequence_reset_gap_fill(self, gap_start_seq, new_seq_no):
        """Send a Sequence Reset - Gap Fill (35=4, 123=Y) to skip a gap."""
        msg = FixMessage(msg_type="4", sender_id=self.sender_id, target_id=self.target_id)
        msg.add_tag(123, "Y")       # GapFillFlag
        msg.add_tag(36, str(new_seq_no))  # NewSeqNo
        # Gap fills are sent with the sequence number of the gap start
        msg.add_tag(34, str(gap_start_seq))

        now = datetime.now(timezone.utc)
        msg.add_tag(49, self.sender_id)
        msg.add_tag(56, self.target_id)
        msg.add_tag(52, now.strftime("%Y%m%d-%H:%M:%S.%f")[:-3])

        raw_msg = msg.encode()
        try:
            self.socket.sendall(raw_msg.encode())
            self.last_sent_time = time.time()
            print(f"SENT Gap Fill: {gap_start_seq} -> {new_seq_no}")
        except Exception:
            self.stop()

    def _handle_sequence_reset(self, msg_str):
        """Handle an incoming Sequence Reset (35=4).

        Updates expected_in_seq_num to the NewSeqNo value.
        """
        new_seq_str = extract_tag(msg_str, 36)
        if new_seq_str is None:
            print("!!! Invalid Sequence Reset: missing NewSeqNo (tag 36)")
            return

        new_seq = int(new_seq_str)
        gap_fill = extract_tag(msg_str, 123)

        if gap_fill == "Y":
            print(f"Sequence Reset - Gap Fill: advancing expected seq from {self.expected_in_seq_num} to {new_seq}")
        else:
            print(f"Sequence Reset - Reset: advancing expected seq from {self.expected_in_seq_num} to {new_seq}")

        self.expected_in_seq_num = new_seq
        self._save_session_state()

    def _listen_loop(self):
        while self.is_running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.stop()
                    break

                decoded_msg = data.decode('utf-8', errors='ignore')
                print(f"RECV: {decoded_msg.replace(chr(1), '|')}")

                # Check message type before sequence validation
                msg_type = extract_tag(decoded_msg, 35)

                if msg_type == "2":
                    # Resend Request — handle before seq validation
                    self._handle_resend_request(decoded_msg)
                    continue

                if msg_type == "4":
                    # Sequence Reset — handle directly (adjusts our expected seq)
                    self._handle_sequence_reset(decoded_msg)
                    continue

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
