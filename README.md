# PyFixEngine

A from-scratch Python implementation of the **FIX 4.2** (Financial Information eXchange) protocol engine. Zero external dependencies — stdlib only.

Built for learning, experimentation, and as a foundation for trading system connectivity.

---

## What It Does

```
┌────────────┐         TCP/IP          ┌────────────┐
│  FixClient │ ◄──────────────────────► │  FixServer │
│            │    FIX 4.2 messages      │            │
└─────┬──────┘                          └──────┬─────┘
      │                                        │
      ▼                                        ▼
 ┌──────────┐                             ┌──────────┐
 │FixSession│  (symmetric — same class)   │FixSession│
 │  ├ listener thread (recv + validate)   │          │
 │  ├ heartbeat thread (send if idle)     │          │
 │  ├ message store (resend support)      │          │
 │  └ FixMessage (encode/decode + cksum)  │          │
 └──────────┘                             └──────────┘
```

**Session-level features:**
- Automatic Logon (`35=A`) on connect
- Heartbeat exchange (`35=0`) with idle-time detection
- Sequence number tracking with persistent state across reconnects
- Gap fill recovery via Resend Request (`35=2`) and Sequence Reset (`35=4`)
- Outbound message store for replay on demand
- Auto-reconnection with configurable retry interval
- Multi-client server with per-connection sessions

**Message-level features:**
- Tag-based message construction and encoding
- FIX checksum calculation and validation
- Repeating group support (encode and parse)

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Trading-apps-seroze/py_fix_engine.git
cd py_fix_engine

# Terminal 1 — start the server
PYTHONPATH=src python3 tests/test_server.py

# Terminal 2 — start the client
PYTHONPATH=src python3 tests/test_client.py
```

You'll see Logon and Heartbeat messages flowing between client and server:

```
SENT: 35=A|49=MY_CLIENT|56=SERVER|8=FIX.4.2|98=0|108=1|34=1|52=20260207-06:48:01.801||10=182|
RECV: 35=0|49=TEST_SERVER|56=MY_CLIENT|8=FIX.4.2|34=1|52=20260207-06:48:01.903||10=096|
```

Both scripts run indefinitely — exit with `Ctrl+C`.

---

## Project Structure

```
src/py_fix_engine/
├── fix_client.py          # TCP client with auto-reconnect loop
├── fix_server.py          # TCP server, accepts connections, tracks sessions
├── fix_session.py         # Core session: threading, send/recv, gap fill, state
├── fix_message.py         # Message container, encoding, checksum, repeating groups
├── fix_message_store.py   # JSON-based outbound message persistence
├── fix_parser.py          # Raw FIX string parser with group-aware parsing
├── fix_tags.py            # Tag number constants and message type definitions
├── fix_engine.py          # (stub — planned)
└── session_manager.py     # (stub — planned)

tests/
├── test_server.py         # Manual test — starts a FIX server on port 9001
└── test_client.py         # Manual test — connects a FIX client to localhost:9001
```

**Runtime files** (created in project root during runs):
- `session_{id}.json` — Persisted sequence numbers for reconnection continuity
- `messages_{id}.json` — Outbound message store for Resend Request handling

---

## How It Works

### Threading Model

Each connection spawns exactly **2 daemon threads**:

| Thread | Responsibility |
|--------|---------------|
| **Listener** | `recv()` loop, message type dispatch, sequence validation |
| **Heartbeat** | Sends `35=0` if no message was sent within the heartbeat interval |

The main thread stays free for application logic.

### Sequence Number Recovery

When a sequence gap is detected (received seq > expected seq):

1. A **Resend Request** (`35=2`) is sent with `BeginSeqNo=expected, EndSeqNo=0` (meaning "everything")
2. The counterparty replays stored messages with `PossDupFlag=Y` (`43=Y`)
3. For any messages not in the store, a **Sequence Reset - Gap Fill** (`35=4, 123=Y`) is sent to skip the gap

### Repeating Groups

Messages can contain repeating groups (e.g., NoPartyIDs):

```python
from py_fix_engine.fix_message import FixMessage

msg = FixMessage(msg_type="D", sender_id="CLIENT", target_id="SERVER")
msg.add_tag(11, "ORD001")
msg.add_tag(55, "AAPL")

msg.add_group(453, [
    {448: "FIRM_A", 447: "D", 452: "1"},
    {448: "FIRM_B", 447: "D", 452: "2"},
])

print(msg.encode())
# ...453=2|448=FIRM_A|447=D|452=1|448=FIRM_B|447=D|452=2|...
```

---

## Configuration

| Parameter | Default | Location |
|-----------|---------|----------|
| Server host | `0.0.0.0` | `FixServer(host=...)` |
| Server port | `9001` | `FixServer(port=...)` |
| Heartbeat interval | `1s` | `FixSession(heartbeat_interval=...)` |
| Client retry interval | `1s` | `FixClient.retry_interval` |

---

## Roadmap

- [x] Socket client and server
- [x] Logon and Heartbeat exchange
- [x] Sequence number tracking and persistence
- [x] Auto-reconnection
- [x] Gap fill handling (Resend Request / Sequence Reset)
- [x] Repeating groups
- [ ] Shutdown after failed logon attempts
- [ ] Session state machine (Connecting, Active, Recovering, Logging Out)
- [ ] Data dictionary (tag name/number mapping from config)
- [ ] Full message parser with body length and checksum validation
- [ ] SQLite-based storage layer

---

## Requirements

- Python 3.8+
- No external dependencies

---

## License

This project is for educational and experimental use.
