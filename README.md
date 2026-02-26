# 🏨 Hotel Booking AI Agent

A production-ready AI-powered hotel booking API built with **FastAPI**, **LangGraph**, **LangChain**, and **OpenRouter** (GPT-OSS 120B free model).

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT / UI                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP REST
┌───────────────────────▼─────────────────────────────────────────┐
│                    FASTAPI APPLICATION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Auth Routes │  │ Hotel Routes │  │    Agent Routes      │  │
│  │  /auth/*     │  │  /hotels/*   │  │  /agent/chat         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                       │             │
│  ┌──────▼─────────────────▼───────────────────────▼──────────┐  │
│  │              Services Layer                                │  │
│  │  AuthService  │  HotelService  │  BookingService          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        │                                       │
│  ┌─────────────────────▼──────────────────────────────────┐   │
│  │              AI AGENT (LangGraph / ReAct)              │   │
│  │                                                        │   │
│  │  1. Load Memory (session history)                      │   │
│  │  2. LLM Call → OpenRouter (GPT-OSS-120B)               │   │
│  │     → Returns structured JSON with action + params     │   │
│  │  3. Tool Dispatch:                                     │   │
│  │     • search  → tool_search_hotels()                   │   │
│  │     • book    → tool_book_hotel()                      │   │
│  │     • status  → tool_get_bookings()                    │   │
│  │     • clarify → return reply (ask user for more info)  │   │
│  │  4. Save Memory (DB + in-memory cache)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                        │                                       │
│  ┌─────────────────────▼──────────────────────────────────┐   │
│  │              MySQL Database (SQLAlchemy ORM)           │   │
│  │  • users  • hotels  • bookings  • conversations       │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
hotel_booking_agent/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   ├── security.py          # JWT + password hashing
│   │   └── logging.py           # Structured logging
│   ├── db/
│   │   └── database.py          # Async SQLAlchemy engine + session
│   ├── models/
│   │   └── models.py            # ORM models (User, Hotel, Booking, Conversation)
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── hotel_service.py
│   │   └── booking_service.py
│   ├── agent/
│   │   ├── agent.py             # Core agent orchestrator
│   │   ├── llm_client.py        # OpenRouter LLM wrapper
│   │   ├── memory.py            # Conversation memory (DB + cache)
│   │   └── tools.py             # Agent tools (search, book, etc.)
│   └── api/
│       ├── middleware.py        # Error handling, request logging
│       └── routes/
│           ├── auth.py
│           ├── hotels.py
│           ├── bookings.py
│           └── agent.py
├── scripts/
│   ├── seed_hotels.py           # Populate DB with sample hotels
│   └── test_api.py              # End-to-end API test demo
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## ⚙️ Setup Guide

### 1. Clone & Virtual Environment

```bash
git clone <your-repo>
cd hotel_booking_agent

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENROUTER_API_KEY=your_key_from_openrouter.ai
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/hotel_booking
SECRET_KEY=your-random-secret-key
```

**Get your OpenRouter API key:** https://openrouter.ai/keys  
Free tier includes access to `openai/gpt-oss-120b:free`

### 3. Start MySQL

**Option A — Docker (recommended):**
```bash
docker-compose up db -d
```

**Option B — Local MySQL:**
```sql
CREATE DATABASE hotel_booking;
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tables are created automatically on startup.

### 5. Seed Sample Hotels

```bash
python scripts/seed_hotels.py
```

### 6. Test the API

Open **http://localhost:8000/docs** for Swagger UI, or run:
```bash
python scripts/test_api.py
```

---

## 🤖 Agent Design Explained

### Why This Architecture?

| Pattern | Decision |
|---------|----------|
| **Simple prompt-based** | Too rigid, no structured output |
| **Native tool calling** | Not reliably supported on free models |
| **ReAct pattern** | ✅ Chosen — reason then act |
| **Structured JSON output** | ✅ Chosen — LLM returns JSON, Python dispatches tools |

### Agent Flow (per message)

```
User: "I want a hotel in Miami for 2 people, Aug 10-15, budget $200"

Step 1: Load memory (session conversation history)
  → [SystemPrompt, HumanMsg("Hi!"), AIMsg("Hello!"), ...]

Step 2: Append new message, call LLM
  → LLM returns:
  {
    "action": "search",
    "reply": "Great! Let me find hotels in Miami for you...",
    "city": "Miami",
    "check_in": "2025-08-10",
    "check_out": "2025-08-15",
    "guests": 2,
    "budget_max": 200
  }

Step 3: Dispatch tool → tool_search_hotels(intent)
  → Queries MySQL, returns 3 matching hotels

Step 4: Append hotel list to reply, return ChatResponse
  → { reply: "...\n- #3 Sunset Beach Resort $380/night...", suggested_hotels: [...] }

Step 5: Save both messages to DB + memory cache
```

### Prompt Design

The system prompt instructs the LLM to:
- Always respond in strict JSON format
- Extract booking parameters from natural language
- Choose the correct `action` (search/book/clarify/status)
- Ask for missing info when dates/city are absent

### Memory Handling

- **In-memory cache** (`dict[session_id → list[BaseMessage]]`) for fast same-request access
- **MySQL persistence** via `conversation_messages` table for cross-session continuity
- Session ID is a UUID returned in every response and must be sent back by the client

---

## 📡 API Reference

### Authentication
```bash
# Register
POST /api/v1/auth/register
{"email": "user@example.com", "username": "john", "password": "pass123"}

# Login → returns JWT token
POST /api/v1/auth/login
{"email": "user@example.com", "password": "pass123"}
```

### Hotels
```bash
GET /api/v1/hotels/?city=Miami&max_price=200&guests=2
GET /api/v1/hotels/{id}
```

### Bookings
```bash
POST /api/v1/bookings/
{"hotel_id": 3, "check_in": "2025-08-10T00:00:00", "check_out": "2025-08-15T00:00:00", "guests": 2}

GET  /api/v1/bookings/
DELETE /api/v1/bookings/{id}
```

### AI Agent Chat
```bash
POST /api/v1/agent/chat
{"message": "Find me a hotel in NYC under $200", "session_id": null}

# Response:
{
  "reply": "Here are great options in NYC:\n- #2 Brooklyn Boutique Inn...",
  "session_id": "uuid-here",
  "suggested_hotels": [...],
  "booking_initiated": false,
  "booking": null
}

# Streaming
POST /api/v1/agent/chat/stream
→ Server-Sent Events: data: {"token": "Here"} \n\n data: {"token": " are"} ...
```

---

## 🚀 Deployment

### Local (Development)
```bash
uvicorn app.main:app --reload
```

### Docker (Full Stack)
```bash
docker-compose up --build
```

---

## 🌐 Frontend Application

This project includes a modern frontend client that interacts with the FastAPI backend.

### Frontend Features

- 🔐 User authentication (JWT-based login/register)
- 💬 AI chat interface with streaming responses
- 🏨 Hotel search with filters
- 📅 Booking creation & management
- 🧠 Session-based conversation memory
- 📱 Responsive UI

### Frontend Tech Stack

- React / Next.js (update with your actual stack)
- Axios for API communication
- JWT token storage
- Server-Sent Events (for streaming chat)

The frontend communicates with:


### Production Suggestions

| Concern | Recommendation |
|---------|---------------|
| **Server** | Use Gunicorn + Uvicorn workers: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4` |
| **Database** | Use AWS RDS / PlanetScale / Railway for managed MySQL |
| **Secrets** | Use AWS Secrets Manager or HashiCorp Vault |
| **Logging** | Ship structured JSON logs to Datadog / CloudWatch |
| **Rate Limiting** | Add slowapi or nginx rate limiting |
| **CORS** | Restrict `allow_origins` to your frontend domain |
| **HTTPS** | Put behind nginx or AWS ALB with SSL termination |
| **LLM Costs** | Upgrade to paid model (claude-3-haiku / gpt-4o-mini) for production reliability |

### Scaling Suggestions

- **Horizontal scaling**: Stateless API (JWT) — just add more containers behind a load balancer
- **Memory cache**: Replace in-process dict with Redis for multi-instance deployments (`langchain-redis`)
- **DB pooling**: Tune SQLAlchemy `pool_size` and `max_overflow` based on load
- **Async I/O**: FastAPI + aiomysql already fully async — maximize throughput per worker
- **LLM caching**: Use `langchain.cache.SQLiteCache` or Redis cache for repeated queries

---

## 🧪 Sample Conversation

```
User: Hi! I want to book a hotel.
Bot:  Hello! I'd love to help you find the perfect hotel. 
      Could you tell me which city you're looking in, 
      your travel dates, and how many guests?

User: New York, August 10-15, 2 people, budget $100-$200.
Bot:  Here are the best matches I found:
      - #2 Brooklyn Boutique Inn (3★) — $150/night in New York
      Would you like to book any of these?

User: Book the Brooklyn Boutique Inn!
Bot:  🎉 Your booking is confirmed!
      Hotel: Brooklyn Boutique Inn
      Check-in: Aug 10, 2025
      Check-out: Aug 15, 2025
      Guests: 2
      Total: $750.00
      Booking ID: #1
```
