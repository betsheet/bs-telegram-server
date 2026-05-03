# bstelegramserver

A **FastAPI** microservice that acts as a Telegram user-API gateway for the Betsheet platform. It wraps [`bstelegramuser`](https://github.com/betsheet/bstelegramuser) (a Telethon-based Telegram user client) and exposes a REST API so that other internal services can authenticate users, inspect their dialogs, and retrieve channel messages — without ever handling Telegram credentials directly.

---

## Table of Contents

- [Architecture overview](#architecture-overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the server](#running-the-server)
- [API Reference](#api-reference)
  - [Health check](#health-check)
  - [Auth endpoints](#auth-endpoints)
  - [Channels endpoints](#channels-endpoints)
  - [Listening endpoints](#listening-endpoints)
- [Authentication flow (step-by-step)](#authentication-flow-step-by-step)
- [Project structure](#project-structure)

---

## Architecture overview

```
Internal API  ──►  bstelegramserver  ──►  bstelegramuser (Telethon)  ──►  Telegram MTProto
                        │
                        └──►  bsutils  (shared models / logger)
```

- **`bstelegramserver`** is a stateless-ish FastAPI server. It keeps in-memory `BSTelegramUserClient` instances (one per user) managed by `TelegramClientManager`.
- Session files are persisted under `sessions/<user_id>.session` so users only need to authenticate once.
- Telegram `api_id` / `api_hash` credentials are fetched on demand from the main Betsheet API (protected by a service JWT token).

---

## Requirements

- Python ≥ 3.11
- Access to the internal Betsheet API (provides Telegram app credentials)
- A `.env` file (see [Configuration](#configuration))

---

## Installation

```bash
# Clone the repository
git clone https://github.com/betsheet/bstelegramserver.git
cd bstelegramserver

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (including private packages from GitHub)
pip install -e .
```

> **Note:** `bstelegramuser` and `bsutils` are pulled directly from GitHub. Make sure your environment has read access to those repositories.

---

## Configuration

Create a `.env` file in the project root with the following variables:

```dotenv
# Base URL of the internal Betsheet API
API_BASE_URL=https://api.betsheet.internal

# JWT token used to authenticate this service against the Betsheet API
API_SERVICE_JWT_TOKEN=your_service_token_here

# Path of the endpoint that returns Telegram app credentials (api_id / api_hash)
GET_TELEGRAM_APP_CREDENTIALS_ENDPOINT=/get-telegram-app-credentials

# Path of the endpoint where processed Telegram messages are forwarded
PROCESS_TELEGRAM_MESSAGES_ENDPOINT=/pick/process-telegram-messages
```

---

## Running the server

```bash
# Development (auto-reload)
fastapi dev app.py

# Production
uvicorn app:app --host 0.0.0.0 --port 8008
```

Interactive API docs are available at `http://localhost:8008/docs` once the server is running.

---

## API Reference

### Health check

#### `GET /`

Returns a simple status response to verify the service is alive.

**Response**
```json
{ "status": "ok" }
```

---

### Auth endpoints

Base path: `/auth`

---

#### `POST /auth/request-verification-code`

Initiates the Telegram authentication flow for a user. Telegram will send a verification code to the user's Telegram app.

If the user already has a valid session, the endpoint returns immediately with `already_authenticated: true` and no code is sent.

**Request body**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "phone_number": "+34600000000"
}
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "phone_number": "+34600000000",
  "already_authenticated": false
}
```

---

#### `POST /auth/verify-code`

Completes the authentication by submitting the code the user received in their Telegram app. On success, a session file is created under `sessions/<user_id>.session`.

**Request body**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "code": "12345"
}
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "authenticated": true
}
```

| Status | Meaning |
|--------|---------|
| `200`  | Authentication successful |
| `400`  | Invalid or expired code |
| `404`  | No active session found — call `/request-verification-code` first |

---

#### `GET /auth/is-authenticated/{user_id}`

Checks whether the given user currently has an authenticated Telegram session loaded in memory.

**Example**
```
GET /auth/is-authenticated/68c5055a3150f98b28b32a00
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "authenticated": true
}
```

| Status | Meaning |
|--------|---------|
| `200`  | Check performed (see `authenticated` field) |
| `404`  | No active session found in memory |

---

### Channels endpoints

Base path: `/channels`

All endpoints in this group require the user to have an active, authenticated session in memory. Start the authentication flow first if needed.

---

#### `GET /channels/{user_id}`

Returns the list of dialogs (channels and supergroups) the user belongs to.

**Example**
```
GET /channels/68c5055a3150f98b28b32a00
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "dialogs": [
    { "name": "Crypto Signals", "type": "channel" },
    { "name": "Dev Team", "type": "supergroup" }
  ]
}
```

| Status | Meaning |
|--------|---------|
| `200`  | Dialogs returned |
| `401`  | User not authenticated |
| `404`  | No active session found |
| `500`  | Unexpected Telegram error |

---

#### `POST /channels/{user_id}/messages`

Returns the last `n` messages from the specified channel.

**Request body**
```json
{
  "channel_name": "Crypto Signals",
  "n": 10
}
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "channel": "Crypto Signals",
  "messages": [
    {
      "id": 4821,
      "text": "BTC just broke $70k 🚀",
      "date": "2026-03-16T10:30:00+00:00"
    },
    {
      "id": 4820,
      "text": "Watch the 68k support level.",
      "date": "2026-03-16T09:15:00+00:00"
    }
  ]
}
```

| Status | Meaning |
|--------|---------|
| `200`  | Messages returned |
| `400`  | `n` is not a positive integer |
| `401`  | User not authenticated |
| `404`  | No active session or channel not found |
| `500`  | Unexpected Telegram error |

---

#### `POST /channels/{user_id}/get-dialog-username`

Resolves the `@username` handle of a dialog given its display name.

**Request body**
```json
{
  "dialog_name": "Crypto Signals"
}
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "channel_name": "Crypto Signals",
  "username": "cryptosignalshub"
}
```

| Status | Meaning |
|--------|---------|
| `200`  | Username returned (may be `null` if the dialog has no public username) |
| `401`  | User not authenticated |
| `404`  | No active session or dialog not found |
| `500`  | Unexpected Telegram error |

---

### Listening endpoints

Base path: `/listening`

All endpoints in this group require the user to have an active, authenticated session in memory.

---

#### `POST /listening/{user_id}/start`

Registers a set of channels to listen to and starts the Telegram event listener for the given user in the background. Once started, every new message received in the registered channels is forwarded to the configured processing endpoint (`PROCESS_TELEGRAM_MESSAGES_ENDPOINT`).

Each channel can be identified by its **display name** (e.g. `"Crypto Signals"`) or its **@username** (e.g. `"cryptosignalshub"` or `"@cryptosignalshub"`). If any channel cannot be found among the user's Telegram dialogs the **entire request is rejected** and no listener is started.

**Request body**
```json
{
  "channels": ["Crypto Signals", "@anotherChannel", "exactDisplayName"]
}
```

**Response**
```json
{
  "user_id": "68c5055a3150f98b28b32a00",
  "listening_channels": ["@cryptosignalshub", "@anotherChannel", "@exactdisplayname"]
}
```

The `listening_channels` field contains the resolved `@username` identifiers that were actually registered with the client.

| Status | Meaning |
|--------|---------|
| `200`  | Listener started; channels listed in `listening_channels` |
| `400`  | `channels` list is empty |
| `401`  | User not authenticated |
| `404`  | No active session found, or one or more channels not found in the user's dialogs |
| `500`  | Unexpected error while resolving channels |

---

## Authentication flow (step-by-step)

Here is a complete example using `curl`:

```bash
USER_ID="68c5055a3150f98b28b32a00"
PHONE="+34600000000"
BASE="http://localhost:8008"

# 1. Request the verification code
curl -s -X POST "$BASE/auth/request-verification-code" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\", \"phone_number\": \"$PHONE\"}"

# 2. Submit the code received in the Telegram app
curl -s -X POST "$BASE/auth/verify-code" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\", \"code\": \"12345\"}"

# 3. (Optional) Check authentication status
curl -s "$BASE/auth/is-authenticated/$USER_ID"

# 4. Fetch the list of dialogs
curl -s "$BASE/channels/$USER_ID"

# 5. Fetch the last 5 messages from a channel
curl -s -X POST "$BASE/channels/$USER_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"channel_name": "Crypto Signals", "n": 5}'
```

Or using Python's `httpx`:

```python
import httpx

BASE = "http://localhost:8008"
USER_ID = "68c5055a3150f98b28b32a00"
PHONE = "+34600000000"

with httpx.Client() as client:
    # Step 1 – request code
    client.post(f"{BASE}/auth/request-verification-code", json={
        "user_id": USER_ID,
        "phone_number": PHONE,
    })

    code = input("Enter the Telegram code: ")

    # Step 2 – verify code
    resp = client.post(f"{BASE}/auth/verify-code", json={
        "user_id": USER_ID,
        "code": code,
    })
    print(resp.json())  # {"user_id": "...", "authenticated": true}

    # Step 3 – list dialogs
    dialogs = client.get(f"{BASE}/channels/{USER_ID}").json()
    print(dialogs["dialogs"])

    # Step 4 – get last 10 messages
    messages = client.post(f"{BASE}/channels/{USER_ID}/messages", json={
        "channel_name": "Crypto Signals",
        "n": 10,
    }).json()
    for msg in messages["messages"]:
        print(msg["date"], msg["text"])
```

---

## Project structure

```
bstelegramserver/
├── app.py                        # FastAPI application entry point
├── pyproject.toml                # Project metadata and dependencies
├── .env                          # Environment variables (not committed)
├── managers/
│   └── telegram_client_manager.py  # In-memory registry of BSTelegramUserClient instances
├── routers/
│   ├── auth_router.py            # /auth/* endpoints
│   ├── channels_router.py        # /channels/* endpoints
│   └── listening_router.py       # /listening/* endpoints
├── util/
│   └── util.py                   # Shared helpers (logger, HTTP client, env vars)
└── sessions/
    └── <user_id>.session         # Persisted Telethon session files (not committed)
```
