
from py_fix_engine.fix_client import FixClient
import time 

# 1. Initiate Client 
client = FixClient("localhost", 9001)

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