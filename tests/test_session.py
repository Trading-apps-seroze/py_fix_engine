
from py_fix_engine.fix_client import FixClient
from py_fix_engine.fix_message import FixMessage
import time 

# 1. Initiate Client 
client = FixClient("localhost", 9001)
# client.start_client() 

# # 2. Build a Logon Message (MsgType 'A')
# logon = FixMessage(msg_type = 'A', sender_id = "MY_CLIENT", target_id = "TEST_SERVER")
# # logon.add_tag(98, 0)
# # logon.add_tag(108, 30)

# # 3. Send it! 
# client.send_message(logon)

# try: 
#     while client.is_running :
#         time.sleep(2)
# except KeyboardInterrupt: 
#     client.stop()


# 2. Start the background manager
client.start_client()

# 3. Keep the main thread alive!
print("Main thread is now sleeping. Press Ctrl+C to exit.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    client.stop()