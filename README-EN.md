# Cookie Finance Bot

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-API_v4-34A853?style=flat&logo=googlesheets&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Evolution_API_v2-25D366?style=flat&logo=whatsapp&logoColor=white)

Financial control bot for a homemade cookie business, operated entirely via WhatsApp. The user sends receipt photos, text messages, or voice notes about sales and expenses; an AI extracts the information and records everything in a Google Sheets spreadsheet with real-time balance.

## Why This Project Exists

Small artisanal businesses rarely have a structured financial control process. The daily routine is hectic — production, sales, supply purchases — and recording every transaction in a spreadsheet requires discipline, time, and a context switch that most people simply never make.

The result is predictable: at the end of the month, you don't know exactly how much came in, how much went out, or whether the business actually turned a profit.

Cookie Finance Bot solves this by eliminating the friction of recording. The user already uses WhatsApp all day; now they just need to send a message as they would normally — "Joana took 4 cookies, R$60", a voice note while driving, or a photo of the grocery receipt — and the bot handles the rest. No new app to learn, no form to fill out, no data lost because "I'll log it later".

Financial control now happens naturally, in the same place where the business already happens.

---

## How It Works

```
[WhatsApp]
    │  Receipt photo / text / voice note
    ▼
[Evolution API]  →  POST webhook
    ▼
[FastAPI — webhook/router.py]
    │  Validates → queues → responds 200 immediately
    ▼
[Async worker — asyncio.Queue]
    │
    ├─ Is it a pending confirmation response?
    │       └─ Resolve pending → save to Sheets → confirm on WhatsApp
    │
    ├─ Text or audio
    │       ├─ Audio → Whisper API → transcribed text
    │       └─ GPT-4o mini → classifies (INCOME / EXPENSE / IGNORE)
    │               ├─ IGNORE → ends without response
    │               └─ INCOME / EXPENSE
    │                       ├─ confidence ≥ 0.85 → save directly → confirm
    │                       └─ confidence < 0.85 → ask for confirmation → wait yes/no
    │
    └─ Image (receipt)
            └─ GPT-4o mini Vision → extracts establishment, amount, date
                    └─ same confidence flow above
```

---

## Features

- **Receipt photo recording** — send the grocery receipt and the bot automatically extracts establishment, amount, and date
- **Free-text recording** — no fixed format: "Joana took 4 cookies, R$60" is enough
- **Voice note recording** — voice messages are transcribed via Whisper and processed as text
- **Smart confirmation** — when extraction confidence is low, the bot asks for confirmation before saving
- **`/summary` command** — returns income, expenses, and current month's balance directly in WhatsApp
- **Real-time Google Sheets** — each transaction creates a new row in the "Transactions" tab
- **Summary dashboard** — "Summary" tab with period selector, totals, and balance calculated by formulas
- **Chat filter** — only processes the configured group or conversation, ignores everything else
- **Non-financial messages silently ignored** — reminders, general conversations, and stickers generate no response

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| WhatsApp | Evolution API (self-hosted) | v2 |
| Backend | Python + FastAPI | 3.12 / 0.115.x |
| ASGI Server | Uvicorn | 0.30.x |
| Validation | Pydantic v2 | 2.7.x |
| LLM + Vision | OpenAI GPT-4o mini | — |
| Audio transcription | OpenAI Whisper API | — |
| Spreadsheet | Google Sheets API v4 | — |
| Google Auth | google-auth (service account) | 2.x |
| HTTP client | httpx | 0.27.x |
| Configuration | pydantic-settings | 2.x |
| Containerization | Docker + Compose | 27.x / 2.x |

---

## Architecture Summary

The bot is a single-process **FastAPI** application with two main components running concurrently:

**Webhook (synchronous at the edge):** receives the `POST /webhook` from Evolution API, validates the payload, queues the message in an `asyncio.Queue`, and immediately returns `200 OK` — without blocking the caller.

**Async worker (actual processing):** continuously consumes the queue. For each message, it identifies the media type (text, audio, or image), calls the necessary external services (Whisper for audio, GPT-4o mini for extraction and classification), manages the state of pending confirmations in memory, and writes to the spreadsheet via Google Sheets API.

Write serialization via queue eliminates race conditions in Sheets without needing an additional database. The state of pending confirmations is kept in an in-memory dictionary with a 5-minute TTL — restarting the container discards open confirmations, which is acceptable given the short expiration time.

### Google Sheets Spreadsheet

The spreadsheet has two tabs:

- **Transactions** — one row per transaction with columns: Date, Type, Description, Amount (R$), Source, and Timestamp. Written via API with each new transaction.
- **Summary** — automatically set up at initialization with `SUMPRODUCT` formulas, period dropdown (from 03/2026), and overall totals without filter. No API writes after initial setup.

### Security

| Surface | Mitigation |
|---|---|
| Public webhook | Filter by `chat_id` — ignores any message outside the configured group |
| Google credentials | Stored as environment variable, never versioned |
| OpenAI key | Same — `.env` outside version control |
| Injection via message | Prompt isolated with explicit instruction to return only structured JSON |

---

## License

Private use.

---

## Author

**Klauber Fischer** — AI Engineer specialized in LLM Applications, Multi-Agent Systems, and RAG in production.

[linkedin.com/in/klaubeer](https://linkedin.com/in/klaubeer) · klaubeer@gmail.com
