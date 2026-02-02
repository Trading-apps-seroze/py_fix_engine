import socket
import threading
from py_fix_engine.fix_session import FixSession

class FixServer:
    def __init__(self, host='0.0.0.0', port=9001, server_id="SERVER"):
        self.host = host
        self.port = port
        self.server_id = server_id
        self.is_running = False
        self.sessions = []  # List to keep track of active client sessions

    def start_server(self):
        """Starts the server listener thread."""
        self.is_running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        print(f"FIX Server listening on {self.host}:{self.port}...")

    def _accept_loop(self):
        # Create the listening socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Prevent "Address already in use"
        server_sock.bind((self.host, self.port))
        server_sock.listen(5)

        while self.is_running:
            try:
                client_sock, addr = server_sock.accept()
                print(f"New connection from {addr}")

                # Create a new session for this specific client
                # Note: On the server, TargetID is the Client's ID
                # Usually, we'd wait for a Logon to identify them, 
                # but for now, we'll label them "CLIENT"
                session = FixSession(client_sock, sender_id=self.server_id, target_id="MY_CLIENT")
                session.start()
                
                self.sessions.append(session)
                
            except Exception as e:
                if self.is_running:
                    print(f"Accept error: {e}")
                break

    def stop(self):
        self.is_running = False
        for session in self.sessions:
            session.stop()