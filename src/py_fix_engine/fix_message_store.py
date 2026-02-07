"""
Persistent message store for FIX sessions.

Stores every outbound message keyed by sequence number so that
messages can be replayed in response to Resend Requests.
"""

import json
import os


class FixMessageStore:
    def __init__(self, sender_id):
        self.store_file = f"messages_{sender_id}.json"
        self._messages = self._load()

    def _load(self):
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self):
        try:
            with open(self.store_file, "w") as f:
                json.dump(self._messages, f)
        except IOError as e:
            print(f"Error saving message store: {e}")

    def store(self, seq_num, raw_message):
        """Store a raw message string keyed by its sequence number."""
        self._messages[str(seq_num)] = raw_message
        self._save()

    def get_range(self, begin, end):
        """Return messages in [begin, end] range as {seq_num_int: raw_msg}.

        If end is 0, return all messages from begin onwards.
        """
        result = {}
        for key, value in self._messages.items():
            seq = int(key)
            if seq >= begin and (end == 0 or seq <= end):
                result[seq] = value
        return dict(sorted(result.items()))
