import time
from py_fix_engine.fix_server import FixServer

# 1. Initialize Server (listening on all interfaces on port 9001)
server = FixServer(host="0.0.0.0", port=9001, server_id="TEST_SERVER")

# 2. Start the listener thread
server.start_server()

# 3. Keep alive
print("FIX Server is running. Press Ctrl+C to shut down.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down server...")
    server.stop()