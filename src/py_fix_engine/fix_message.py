"""
Docstring for FixMessage

Responsibility: To hold the data for a single message 
Attributes: A dictionary of tags, a 'get_tag()' method, and an 'encode()' method 

"""

from py_fix_engine.fix_tags import FixTag 


class FixMessage:

    SOH = "\x01"
    
    def __init__(self, msg_type: str, sender_id: str, target_id: str):
        # Dictionary to hold our tags (Responsibility: Hold data for single message)
        self.tags = {
            35: msg_type,
            49: sender_id,
            56: target_id,
            # Note: Tag 8 (BeginString) and 9 (BodyLength) are usually added during encoding
            8: "FIX.4.2"
        }
        # Repeating groups: {count_tag: [{tag: value, ...}, ...]}
        self.groups = {}

    def add_tag(self, tag: int, value: str):
        """Adds or updates a tag in the message."""
        # Convert tag to string to keep keys consistent
        self.tags[tag] = value 

    def get_tag(self, tag_num: int):
        return self.tags.get(tag_num)

    def add_group(self, count_tag, entries):
        """Add a repeating group.

        Args:
            count_tag: The NoXxx tag (e.g. 453 for NoPartyIDs).
            entries: List of dicts [{tag: value, ...}, ...].
        """
        self.groups[count_tag] = entries

    def get_group(self, count_tag):
        """Return the list of entry dicts for a repeating group, or None."""
        return self.groups.get(count_tag)

    @staticmethod
    def calculate_checksum(raw_message: str) -> int: 
        """
        Docstring for calculate_checksum
        
        :param raw_message: Description
        :type raw_message: str
        :return: Description
        :rtype: int
        """

        msg_bytes = raw_message.encode('ascii')

        total_sum = sum(msg_bytes) 
        checksum_val = total_sum%256 

        return f"{checksum_val:03}"

    @staticmethod
    def validate_message(full_message: str) -> bool: 

        # Seperate the message from checksum tag (10)
        parts = full_message.split(f"{FixTag.CHECKSUM}") 
        if len(parts) != 2: 
            return False 
        
        body_to_check = parts[0]
        # Note: \x01 is the SOH delimiter 
        received_checksum = parts[1].replace("\x01", "")

        expected = FixMessage.calculate_checksum(body_to_check)
        return expected == received_checksum 

    def encode(self) -> str:

        # 1. Manually build the string from the tags dictionary
        # We skip Tag 10 because we're about to calculate it
        raw_content = "".join([f"{tag}={val}{FixMessage.SOH}" for tag, val in self.tags.items() if tag != "10"])

        # 2. Append repeating groups
        for count_tag, entries in self.groups.items():
            raw_content += f"{count_tag}={len(entries)}{FixMessage.SOH}"
            for entry in entries:
                for tag, val in entry.items():
                    raw_content += f"{tag}={val}{FixMessage.SOH}"

        check_sum = FixMessage.calculate_checksum(raw_content)
        return f"{raw_content}{FixMessage.SOH}10={check_sum}{FixMessage.SOH}"