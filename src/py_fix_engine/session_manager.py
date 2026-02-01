"""
Docstring for SessionManager

Maintains the `state`
target_seq_num : Next expected seq number 
message_store: list of database of sent messages 

Functions:
- handle_incoming(msg)
- on_logon()
- on_logout()
- check_for_gaps()

"""
from py_fix_engine.fix_tags import FixTag 


def handle_incoming(self, message): 
    msg_typ = message.get_tag()

    if not self.validate_sequence(message.get_tag(35)):
        self.send_resend_request()
        return 
    
    if msg_typ == "A": # Logon 
        self.on_logon(message)
    elif msg_typ == "0": # Heartbeat
        self.on_heartbeat(message)
    elif msg_typ == "1": # Test Request 
        self.send_heartbeat(message.get_tag(112)) # Respond with TestReqID 
    elif msg_typ == "2": # Resend Request 
        self.resend_messages(message) 