# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python FIX (Financial Information eXchange) protocol engine implementing FIX 4.2. Currently in Phase 1: basic session-level connectivity with heartbeating, sequence number tracking, and session state persistence. No external dependencies — stdlib only.

## Running the Project

There is no automated test suite. Testing is done manually with two scripts:

```bash
# Terminal 1: Start the server
python tests/test_server.py

# Terminal 2: Start the client
python tests/test_client.py

# Both run indefinitely — exit with Ctrl+C
```

Session state files (`session_*.json`) are created in the project root during runs. These track sequence numbers for reconnection continuity.

## Architecture

**Component flow:**

```
FixClient / FixServer
    └── creates FixSession (one per connection)
            ├── listener thread  (recv loop, sequence validation)
            ├── heartbeat thread (sends HB if idle >= interval)
            └── FixMessage (encode/decode with checksum)
```

**Key design: FixSession is symmetric.** Both `FixClient` and `FixServer` delegate all messaging to the same `FixSession` class. The client adds connection management and auto-reconnection; the server adds socket accept and multi-client tracking.

**Threading model:** Each connection spawns exactly 2 daemon threads — a listener and a heartbeat sender. The main thread stays free for application logic.

**Sequence numbers:** Separate inbound/outbound counters persisted to `session_{sender_id}.json` after every send and every validated receive. Gap detection is simplified — logs a warning and jumps forward rather than issuing resend requests.

**Message encoding:** Tags stored as `{int: str}` dict. `encode()` concatenates `tag=value\x01` pairs and appends a 3-digit checksum (sum of ASCII bytes mod 256).

## Source Layout

All source is in `src/py_fix_engine/`. Key modules:

- **fix_session.py** — Core session logic: threading, send/recv, sequence tracking, state persistence
- **fix_message.py** — Message data container, encoding, checksum calculation and validation
- **fix_client.py** — TCP client with auto-reconnect loop, sends Logon on connect
- **fix_server.py** — TCP server, accepts connections, creates per-client sessions
- **fix_tags.py** — FIX tag number constants (Tag 8, 34, 35, 49, 56, etc.)
- **fix_parser.py, fix_engine.py, session_manager.py** — Stubs, not yet implemented

## Incomplete / Planned Features

Per GOALS.md, these Phase 1 items remain:
- Gap fill handling (Resend Request, MsgType 35=2)
- Shutdown after 100 failed logon attempts
- Repeating groups support

See DESIGN.md for the full architectural blueprint (data dictionary, message parser, session state machine, storage layer).

## Caveats (from WATCHOUT_FOR.md)

- Session state files must be reset after a day (sequence numbers shouldn't carry over indefinitely)
- Heartbeats must only send when `last_sent_time >= threshold`, not on a fixed timer
