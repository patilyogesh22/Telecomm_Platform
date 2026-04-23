# 📡 TeleBot — AI Telecomm Intelligence Platform

<div align="center">

**India's smartest telecom platform — Recharge instantly, compare plans, and learn with AI**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.3-FF6B35?style=for-the-badge)](https://www.trychroma.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

[Features](#-features) • [Quick Start](#-quick-start) • [API Docs](#-api-reference) • [Deploy](#-deploy-to-aws-ec2) • [Architecture](#%EF%B8%8F-architecture)

</div>

---

## ✨ Features

### 💳 Pay & Recharge
- **8 service types** — Mobile, DTH, Broadband, Postpaid, Electricity, Gas, Water, Landline
- **Auto-detect operator** — Enter mobile number → detects Jio / Airtel / Vi / BSNL automatically
- **Real plan data** — 40+ actual Indian telecom plans with prices, validity, data, OTT extras
- **Category filters** — Popular, 5G, Budget, Long Validity, Annual
- **Transaction history** — View recent recharges and bill payments

### 📱 My Plan
- **Smart detection** — Enter any 10-digit number → auto-detect operator from prefix
- **Current plan view** — Active plan with data, calls, SMS, validity specs
- **Usage meters** — Live data, calls, and validity progress bars
- **Alternative plans** — Browse all plans filtered by category
- **One-click recharge** — Pre-fills payment page with operator + plan

### 🤖 AI Tutor (Gemini 2.5 Flash + RAG)
- Ask **"Give me all Jio plans"** → complete plan list with prices
- Ask **"Compare Airtel vs Jio 2GB plans"** → side-by-side comparison
- Ask **"Best 5G plan under ₹350"** → personalized recommendation
- Understands **telecom concepts** — 5G, NB-IoT, LTE-M, VoLTE, eSIM, Static IP
- **RAG-grounded** — every answer backed by ChromaDB semantic retrieval

### 🎯 AI Quiz (Gemini-Generated Questions)
- **Fresh questions every session** — Gemini generates unique MCQs every time
- **Session store** — correct answers kept server-side, never exposed to client
- **Rich explanations** — why right answer is correct + why each wrong option is wrong
- **4 difficulty levels** — All, Easy, Medium, Hard
- **Graceful fallback** — 15 static questions if Gemini is unavailable

### 📋 Plan Explorer
- All 8 platform plans searchable by name, type, data, speed, features
- Real-time filter as you type
- Type badges — Prepaid, Postpaid, IoT/M2M, International, Enterprise

### 🗄️ Vector DB Viewer
- Live stats — plans indexed, concepts indexed, embedding model, similarity metric
- Visual RAG pipeline diagram
- Code snippets showing ChromaDB retrieval

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TeleBot Platform v3.0.0                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Frontend — Vanilla JS SPA (7 pages)                     │   │
│  │  Font: Sora · Theme: Dark glassmorphism                  │   │
│  │                                                           │   │
│  │  Dashboard  Pay & Recharge  My Plan  AI Quiz             │   │
│  │  AI Tutor   Plan Explorer   Vector DB                    │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │ HTTP REST                           │
│  ┌─────────────────────────▼────────────────────────────────┐   │
│  │  Backend — Flask 3.0 (Python 3.11)                       │   │
│  │                                                           │   │
│  │  Auth (SQLite)  ·  Payment (6 routes)  ·  Quiz + AI      │   │
│  │                                                           │   │
│  │  RAG Pipeline:                                            │   │
│  │  telecom_docs.txt → MiniLM embeddings                    │   │
│  │  → ChromaDB (HNSW cosine) → Gemini 2.5 Flash            │   │
│  │                                                           │   │
│  │  operator_data.py  — Jio/Airtel/Vi/BSNL plan DB          │   │
│  │  quiz_engine.py    — Session store + fallback Qs         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Flow

```
User message
     │
     ▼
ChromaDB semantic search  (cosine similarity on MiniLM embeddings)
     │
     ├── + Operator plans injected if asking about Jio/Airtel/Vi/BSNL
     │
     ▼
Gemini 2.5 Flash  (grounded generation)
     │
     ▼
Accurate, context-aware answer
```

---

## 📁 Folder Structure

```
Telecomm_Platform/
│
├── backend/
│   ├── app.py              # Flask server — 30+ API routes
│   ├── llm_service.py      # Gemini 2.5 Flash: quiz gen, explanations, tutor
│   ├── quiz_engine.py      # AI session store + 15 static fallback questions
│   ├── operator_data.py    # Jio/Airtel/Vi/BSNL + DTH/Broadband/Electricity/etc
│   ├── vector_db.py        # ChromaDB RAG: embed, index, retrieve
│   ├── telecom_docs.txt    # Knowledge base (8 plans + 11 concepts)
│   ├── requirements.txt    # Python dependencies
│   ├── test_key.py         # Gemini API key tester
│   └── debug_docs.py       # Vector DB debug helper
│
├── frontend/
│   ├── index.html          # 7-page SPA
│   ├── style.css           # Premium dark theme (Sora font)
│   └── script.js           # Complete app logic
│
├── nginx/
│   └── nginx.conf          # Reverse proxy config
│
├── .github/
│   └── workflows/
│       ├── ci.yml          # Test → Build → Push to Docker Hub
│       └── deploy.yml      # SSH to EC2, pull, restart
│
├── .env.example            # Environment variables template
├── .gitignore
├── Dockerfile              # python:3.11-slim, flat copy, non-root user
├── docker-compose.yml      # Port 5000, env vars, restart:always
├── deploy.sh               # Manual EC2 deploy script
├── setup_ec2.sh            # EC2 first-time setup script
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Gemini API Key](https://makersuite.google.com/app/apikey) — free, takes 1 minute
- Docker (optional, for containerized deployment)

### Option 1 — Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform

# 2. Set up environment variables
cp .env.example backend/.env
# Edit backend/.env — add your GEMINI_API_KEY

# 3. Install Python dependencies
cd backend
pip install -r requirements.txt

# 4. Run the server
python app.py
# Server starts at http://localhost:5000
```

Open `http://localhost:5000` — the frontend is served automatically by Flask.

### Option 2 — Docker Compose

```bash
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform

# Add your API key
echo "GEMINI_API_KEY=your_key_here" > backend/.env

# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3 — Docker Hub Image

```bash
docker pull yogeshpatil22/telebot:latest

docker run -d \
  -p 5000:5000 \
  -e GEMINI_API_KEY=your_key_here \
  --name telebot \
  yogeshpatil22/telebot:latest

# Verify
curl http://localhost:5000/health
```

---

## ⚙️ Environment Variables

Create `backend/.env`:

```env
# Required — free key at https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_API_KEY_1=your-gemini-api-key-1-here
GEMINI_API_KEY_2=your-gemini-api-key-2-here

GROQ_API_KEY=your-groq-api-key-here

# Optional — change for production
SECRET_KEY=telecom-secret-2024
PORT=5000
```

> Without `GEMINI_API_KEY`, the app still works — it falls back to 15 static quiz questions and shows "AI Key Missing" in the status bar. All payment, plan detection, and navigation features work without it.

---

## 📖 API Reference

All endpoints except `/health` require authentication via session cookie.

### Auth

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | `{full_name, username, email, password}` | Create account |
| `POST` | `/api/auth/login` | `{username, password}` | Login |
| `POST` | `/api/auth/logout` | — | Logout |
| `GET`  | `/api/auth/me` | — | Current user info |

### User & Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/user/profile` | Get or update profile |
| `GET`  | `/api/plan` | Current plan |
| `POST` | `/api/plan/change` | `{plan_id}` — Switch plan |
| `GET`  | `/api/bill` | Current bill with tax breakdown |
| `POST` | `/api/bill/pay` | Pay bill (simulated) |
| `GET`  | `/api/usage` | Data, calls, SMS usage stats |
| `GET`  | `/api/calls` | Recent call history |
| `GET`  | `/api/notifications` | App notifications |

### Payment

| Method | Endpoint | Params / Body | Description |
|--------|----------|---------------|-------------|
| `GET`  | `/api/payment/operators` | `?service=mobile` | Operators for a service type |
| `GET`  | `/api/payment/plans` | `?operator=Jio&type=prepaid&service=mobile` | Plans for operator |
| `POST` | `/api/payment/detect` | `{mobile}` | Detect operator from mobile number |
| `POST` | `/api/payment/my-plan` | `{mobile}` | Current plan + all alternatives |
| `POST` | `/api/payment/recharge` | `{service, operator, number, plan_id, amount}` | Process recharge |
| `GET`  | `/api/payment/transactions` | — | Recent transaction history |

**Service types for `/api/payment/operators`:**
`mobile` · `dth` · `broadband` · `postpaid` · `electricity` · `gas` · `water` · `landline`

### Quiz & AI

| Method | Endpoint | Params / Body | Description |
|--------|----------|---------------|-------------|
| `GET`  | `/api/quiz/questions` | `?difficulty=all&count=8` | Generate AI questions via Gemini |
| `POST` | `/api/quiz/submit` | `{question_id, answer, session_id}` | Submit answer + get AI explanation |
| `POST` | `/api/quiz/score` | `{score, total, difficulty}` | Save quiz score to DB |
| `GET`  | `/api/quiz/history` | — | Past quiz scores |
| `POST` | `/api/quiz/chat` | `{message, history}` | AI Tutor chat (RAG + Gemini) |

### Health Check

```bash
GET /health
```
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "service": "Telecomm Intelligence Platform",
  "llm_available": true,
  "vectordb": {
    "plans_indexed": 8,
    "concepts_indexed": 11,
    "similarity_metric": "cosine"
  }
}
```

---

## 📊 Operator Plans Database

### Mobile Plans

| Operator | Logo | Prepaid | Postpaid | Cheapest | Priciest |
|----------|:----:|:-------:|:--------:|:--------:|:--------:|
| Jio | 🟦 | 7 plans | 3 plans | ₹155/24d | ₹2,999/365d |
| Airtel | 🔴 | 7 plans | 3 plans | ₹99/28d | ₹3,359/365d |
| Vi | 🟣 | 7 plans | 3 plans | ₹99/28d | ₹2,899/365d |
| BSNL | 🟡 | 5 plans | 2 plans | ₹94/28d | ₹1,515/365d |

Every plan stores: `id · name · price · validity · data · calls · sms · category · extras[]`

Plan categories: `budget · popular · 5g · long · annual · postpaid`

### Other Service Operators

| Service | Operators Available |
|---------|---------------------|
| 📺 DTH | Tata Play, Airtel DTH, Dish TV, Sun Direct, D2H |
| 🌐 Broadband | Jio Fiber (5 plans ₹399–₹2499), Airtel Xstream (4 plans ₹499–₹1999), BSNL Fiber, ACT Fibernet |
| ⚡ Electricity | BSES Rajdhani, BSES Yamuna, TPDDL, MSEDCL, BESCOM, TNEB, WBSEDCL, UPPCL, PSPCL, JVVNL, KSEB, APCPDCL, TSSPDCL, CESC, DGVCL |
| 🔥 Gas | Indraprastha Gas, Mahanagar Gas, Gujarat Gas, Adani Gas, IGL |
| 💧 Water | Delhi Jal Board, MCGM (Mumbai), BWSSB (Bengaluru), CMWSSB (Chennai), HMWSSB (Hyderabad) |
| ☎️ Landline | BSNL, MTNL, Airtel, JioFiber |

---

## ☁️ Deploy to AWS EC2

### CI/CD via GitHub Actions (Recommended)

**Add these secrets** in your GitHub repo under `Settings → Secrets and variables → Actions`:

| Secret Name | Value |
|-------------|-------|
| `DOCKER_USER` | Docker Hub username |
| `DOCKER_PASS` | Docker Hub password or access token |
| `EC2_HOST` | EC2 public IP address |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Contents of your `.pem` private key file |
| `GEMINI_API_KEY` | Your Gemini API key |

**Push to trigger CI/CD:**
```bash
git push origin main
# Automatically: test → build image → push to Docker Hub → SSH deploy to EC2
```

### Manual Deploy

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# First-time Docker setup
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu && newgrp docker

# Clone and configure
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform
echo "GEMINI_API_KEY=your_key_here" > backend/.env

# Start
docker-compose up -d

# Check health
curl http://localhost:5000/health
docker-compose logs --tail=30
```

### Update Running Instance

```bash
cd ~/Telecomm_Platform
docker-compose down
docker pull yogeshpatil22/telebot:latest
docker-compose up -d
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| AI Model | Google Gemini | 2.5 Flash |
| Vector DB | ChromaDB | 0.5.3 |
| Embeddings | all-MiniLM-L6-v2 | via ChromaDB |
| Backend | Flask | 3.0.3 |
| CORS | Flask-CORS | 4.0.1 |
| Auth | Werkzeug bcrypt + Sessions | — |
| Database | SQLite via SQLAlchemy | — |
| WSGI Server | Gunicorn | 22.0.0 |
| Frontend | Vanilla JS SPA | ES2022 |
| UI Font | Sora (Google Fonts) | — |
| Container | Docker | python:3.11-slim |
| Reverse Proxy | Nginx | — |
| CI/CD | GitHub Actions | — |
| Cloud | AWS EC2 | Ubuntu 22.04 |

---

## 🔧 Troubleshooting

### `ModuleNotFoundError: No module named 'vector_db'`

The Dockerfile must copy backend files **flat** into `/app`:

```dockerfile
# ✅ Correct — all .py files land directly in /app/
COPY backend/ ./

# ❌ Wrong — files land in /app/backend/ and Python can't find them
COPY backend/ ./backend/
```

### Port in use / stale Docker network

```bash
docker-compose down --remove-orphans
docker network prune -f
docker-compose up -d
```

### Old Docker on EC2 (syntax error)

```bash
# Older Docker (v1):
docker-compose up -d

# Newer Docker (v2+):
docker compose up -d
```

### CSS Error: `.badge.5g` invalid selector

Class names can't start with a number in CSS:
```css
.badge-5g { ... }   /* ✅ valid */
.badge.5g  { ... }   /* ❌ invalid — breaks stylesheet */
```

### Gemini 429 rate limit

`llm_service.py` has automatic retry with backoff (4 attempts, 8/16/24/32s waits). If you keep hitting limits, the app falls back to static quiz questions automatically.

### AI Tutor not knowing real plans

Ensure `operator_data.py` is present in the backend folder. The `/api/quiz/chat` route detects operator keywords in messages and injects live plan data into the Gemini context before generating a response.

---

## 📁 Key Files Explained

**`backend/app.py`** — Flask application with 30+ routes. Handles auth (SQLite + bcrypt), payment endpoints, quiz AI generation, tutor chat, billing, usage. `login_required` decorator protects all authenticated routes.

**`backend/llm_service.py`** — All Gemini 2.5 Flash logic:
- `generate_quiz_questions()` — Generates fresh MCQs; validates JSON structure; assigns UUIDs
- `generate_explanation()` — Rich explanation covering why right and why each wrong option fails
- `tutor_chat()` — Multi-turn conversation with RAG context injection
- LRU cache, rate limiter (2s gap), 4× retry with exponential backoff

**`backend/quiz_engine.py`** — Session store (`_sessions` dict keyed by UUID). AI-generated correct answers are stored here, never sent to client. `validate_session_answer()` checks submitted answer against session. Falls back to 15 static questions if session expired.

**`backend/operator_data.py`** — Complete Indian telecom plan database. `detect_operator(mobile)` uses 4-digit and 2-digit prefix lookup to identify operator. `format_plans_for_ai(operator)` returns formatted plan text injected into Gemini context when user asks about plans.

**`backend/vector_db.py`** — ChromaDB initialization. Loads `telecom_docs.txt`, embeds with MiniLM, stores in ephemeral ChromaDB. `retrieve_all(query)` returns top-N relevant chunks via cosine similarity search.

---

## 📊 Project Stats

| Metric | Value |
|--------|------:|
| Frontend pages | 7 |
| API endpoints | 30+ |
| Mobile operators | 4 |
| Mobile plans in DB | ~40 |
| Other service providers | 30+ |
| Service types | 8 |
| RAG documents indexed | 19 |
| Fallback quiz questions | 15 |
| Frontend lines of code | ~1,900 |
| Backend lines of code | ~1,200 |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch — `git checkout -b feat/your-feature`
3. Commit your changes — `git commit -m 'feat: add amazing feature'`
4. Push — `git push origin feat/your-feature`
5. Open a Pull Request

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI quiz generation and tutoring
- [ChromaDB](https://www.trychroma.com/) — Vector database for semantic search
- [Sentence Transformers](https://sbert.net/) — all-MiniLM-L6-v2 embeddings
- [Flask](https://flask.palletsprojects.com/) — Python web framework
- [Sora Font](https://fonts.google.com/specimen/Sora) — Google Fonts

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by [patilyogesh22](https://github.com/patilyogesh22)**

⭐ Star this repo if you found it useful!

</div>
