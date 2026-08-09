

<div align="center">

<img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11"/>
<img src="https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
<img src="https://img.shields.io/badge/Gemini-2.0%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"/>
<img src="https://img.shields.io/badge/Groq-Llama%203.3%2070B-F55036?style=for-the-badge" alt="Groq"/>
<img src="https://img.shields.io/badge/ChromaDB-0.5.3-FF6B35?style=for-the-badge" alt="ChromaDB"/>
<img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
<img src="https://img.shields.io/badge/AWS-EC2-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS EC2"/>

# 📡 TeleBot — AI Telecomm Intelligence Platform

**India's smartest telecom platform.  
Recharge instantly · Compare plans · Learn with AI · Triage support tickets autonomously.**

[Features](#-features) · [Problem Statements](#-three-problem-statements) · [Quick Start](#-quick-start) · [API Reference](#-api-reference) · [Architecture](#%EF%B8%8F-architecture) · [Deploy](#-deploy-to-aws-ec2)

</div>

---

## 🌟 Features at a Glance

| | Feature | What it does |
|---|---|---|
| 💳 | **Pay & Recharge** | Mobile · DTH · Broadband · Electricity · Gas · Water · Landline |
| 📱 | **My Plan** | Enter any number → auto-detect operator → current plan + alternatives |
| 🤖 | **AI Tutor** | Ask "Best Jio plan under ₹300" → instant answer powered by Gemini + RAG |
| 🎯 | **AI Quiz** | Fresh Gemini-generated MCQs every session · rich explanations |
| 🛡️ | **Support Triage Agent** | Paste complaint → NER + AI classifies urgency · drafts response · creates ticket |
| 📋 | **Plan Explorer** | All 8 platform plans + 40+ operator plans searchable |
| 🗄️ | **Vector DB Viewer** | Live RAG pipeline stats · ChromaDB index viewer |

---

## 📋 Three Problem Statements

### Problem Statement 1 — IaC Provisioning for Telecomm System
> *"Automate the provisioning of infrastructure using Docker, Git, GitHub Actions, enabling repeatable, scalable environment setup."*

**Implemented:**
- `Dockerfile` — `python:3.11-slim` base, flat `COPY backend/ ./` (critical for imports), non-root user, `HEALTHCHECK`
- `docker-compose.yml` — port mapping, `env_file`, volume for SQLite persistence, `restart: always`
- `.github/workflows/ci.yml` — test → build Docker image → push to Docker Hub with `:latest` + `:sha` tags
- `.github/workflows/deploy.yml` — SSH to EC2 → write `.env` → `docker pull` → `compose restart` → health check
- `setup_ec2.sh` — installs Docker, clones repo, starts containers on a fresh Ubuntu server

---

### Problem Statement 2 — Telecomm Quiz / Tutor Bot (Gen AI)
> *"AI educational bot using Python, Vector DB, LLM API — evaluates responses, provides deep contextual explanations, creates a personalized learning loop."*

**Implemented:**
- **AI Quiz** — Gemini 2.0 Flash generates 8 fresh MCQs every session · correct answers stored server-side only (never sent to client) · RAG-grounded explanations for every answer
- **AI Tutor** — Conversational chatbot knows all 40+ Indian operator plans · RAG retrieval from ChromaDB before every response · multi-turn conversation memory · smart operator detection injects live plan data
- **RAG Pipeline** — `telecom_docs.txt` (8 plans + 11 concepts) → `all-MiniLM-L6-v2` embeddings → ChromaDB HNSW cosine index → top-N context injected into Gemini prompt
- **Multi-key rotation** — 3 Gemini keys + 1 Groq fallback (Llama 3.3 70B) · auto-rotates on 429 · midnight reset thread

---

### Problem Statement 3 — Telecomm Support Triage Agent (Agentic AI)
> *"Reactive triage agent — real-time urgency/intent classification, Named Entity Recognition (NER), AI-generated draft responses to accelerate resolution times."*

**Implemented:**
- **NER** — regex extracts phone numbers, account IDs, amounts (₹), dates, operator names, ticket refs · 0ms · no API needed
- **Urgency classification** — CRITICAL / HIGH / MEDIUM / LOW · local keyword rules (instant) + Gemini AI (nuanced)
- **Intent detection** — 13 categories: outage, billing, plan_change, roaming, speed, complaint, cancellation, upgrade, porting, account, device, recharge, general
- **AI draft response** — Gemini generates professional empathetic reply with customer's extracted entities embedded
- **Ticket management** — `TKT-YYYYMMDD-XXXXXX` IDs · OPEN → IN_PROGRESS → RESOLVED → CLOSED lifecycle · escalation flags · dashboard stats
- **Full offline fallback** — all features work without API via keyword classification + template responses

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Frontend  —  Vanilla JS SPA  (7 pages)              │
│  Dashboard  ·  Pay & Recharge  ·  My Plan  ·  AI Quiz               │
│  AI Tutor  ·  Support Triage  ·  Plan Explorer  ·  Vector DB        │
└────────────────────────────┬────────────────────────────────────────┘
                             │  HTTP REST  (35 endpoints)
┌────────────────────────────▼────────────────────────────────────────┐
│                 Backend  —  Flask 3.0  ·  Python 3.11               │
│                                                                      │
│  app.py           35 routes · auth · billing · payments             │
│  llm_service.py   Gemini + Groq · multi-key rotation · cache        │
│  quiz_engine.py   session store · fallback bank (15 Qs)             │
│  triage_agent.py  NER · classify · draft · ticket CRUD              │
│  operator_data.py 40+ plans · detect_operator() prefix lookup       │
│  vector_db.py     ChromaDB init · retrieve_plans · retrieve_all     │
└────┬───────────────────────┬────────────────────────────────────────┘
     │                       │
     ▼                       ▼
┌──────────────┐    ┌────────────────────────────────────────────────┐
│   SQLite DB  │    │              AI + Data Layer                   │
│  users table │    │  Gemini 2.0 Flash (×3 keys, auto-rotate)       │
│  quiz_scores │    │  Groq  ·  Llama 3.3 70B  (final fallback)      │
└──────────────┘    │  ChromaDB  ·  all-MiniLM-L6-v2  ·  HNSW       │
                    └────────────────────────────────────────────────┘
```

### RAG Pipeline

```
telecom_docs.txt  →  MiniLM-L6-v2 embeddings  →  ChromaDB (HNSW cosine)
                                                          ↓
User query  →  semantic search  →  top-N chunks  →  Gemini  →  grounded answer
```

### Multi-Key Rotation

```
Request → Key 1  → 429? → rotate → Key 2  → 429? → rotate → Key 3
                                                              ↓ 429?
                                                          Groq (Llama 3.3 70B)
                                                              ↓ fail?
                                                       Offline fallback
                                                       (rule-based, 0 ms)
Keys auto-reset at midnight every day.
```

---

## 📁 Folder Structure

```
Telecomm_Platform/
│
├── backend/
│   ├── app.py              # 899 lines · 35 API routes · Flask entry point
│   ├── llm_service.py      # 771 lines · Gemini + Groq · multi-key rotation · LRU cache
│   ├── triage_agent.py     # 637 lines · NER · classification · ticket CRUD · stats
│   ├── quiz_engine.py      # 250 lines · session store · 15 static fallback questions
│   ├── operator_data.py    # 334 lines · 40+ Indian plans · detect_operator() · helpers
│   ├── vector_db.py        # 374 lines · ChromaDB · MiniLM embeddings · RAG retrieval
│   ├── telecom_docs.txt    # Knowledge base: 8 plans + 11 telecom concepts
│   ├── test_key.py         # Quick Gemini API key tester
│   ├── debug_docs.py       # Vector DB debug helper
│   └── requirements.txt    # Python dependencies
│
├── frontend/
│   ├── index.html          # 7-page SPA (602 lines)
│   ├── style.css           # Dark premium theme — Sora font (744 lines)
│   └── script.js           # Complete app logic (1240 lines)
│
├── nginx/
│   └── nginx.conf          # Reverse proxy config
│
├── .github/
│   └── workflows/
│       ├── ci.yml          # Test → Build → Push to Docker Hub
│       └── deploy.yml      # SSH to EC2 → pull → restart → health check
│
├── .env.example            # Environment variable template
├── .gitignore
├── Dockerfile              # python:3.11-slim · flat COPY · non-root user · HEALTHCHECK
├── docker-compose.yml      # Port 5000 · env_file · volume · restart:always
├── deploy.sh               # Manual EC2 deploy script
├── setup_ec2.sh            # EC2 first-time Docker + Git setup
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Get it |
|---|---|---|
| Python | 3.11+ | python.org |
| Docker | 24+ | docker.com |
| Gemini API Key | free | [makersuite.google.com](https://makersuite.google.com/app/apikey) |
| Groq API Key | free | [console.groq.com](https://console.groq.com) |

### Option 1 — Local (No Docker)

```bash
# 1. Clone
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform

# 2. Create environment file
cp .env.example backend/.env
# Edit backend/.env — add your API keys (see Environment Variables section)

# 3. Install Python dependencies
cd backend
pip install -r requirements.txt

# 4. Run
python app.py
# App starts at http://localhost:5000
```

### Option 2 — Docker Compose

```bash
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform

# Add your API keys
cp .env.example backend/.env
# Edit backend/.env

# Build and start
docker-compose up --build -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3 — Docker Hub (Fastest)

```bash
docker pull yogeshpatil22/telebot:latest

docker run -d \
  -p 5000:5000 \
  --env-file ./backend/.env \
  --name telebot \
  yogeshpatil22/telebot:latest

# Health check
curl http://localhost:5000/api/health
```

---

## ⚙️ Environment Variables

Create `backend/.env` from `.env.example`:

```env
# ── Required: Gemini API Keys (free at makersuite.google.com) ──────────
# Add up to 3 keys — system auto-rotates when one hits 429 quota
GEMINI_API_KEY=AIzaSy_YOUR_PRIMARY_KEY
GEMINI_API_KEY_1=AIzaSy_YOUR_SECOND_KEY
GEMINI_API_KEY_2=AIzaSy_YOUR_THIRD_KEY

# ── Required: Groq API Key (free at console.groq.com) ─────────────────
# Final fallback when all Gemini keys are exhausted — 14,400 req/day free
# Runs Llama 3.3 70B at 500+ tokens/second on Groq LPU hardware
GROQ_API_KEY=gsk_YOUR_GROQ_KEY

# ── App config ─────────────────────────────────────────────────────────
SECRET_KEY=telecom-secret-2024
PORT=5000
```

> **Note:** Without any API key the app still works — quiz falls back to 15 static questions, tutor gives rule-based answers, triage uses keyword classification. No crash.

---

## 📖 API Reference

### Authentication  `4 routes`

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | `{full_name, username, email, password}` | Create account |
| `POST` | `/api/auth/login` | `{username, password}` | Login · sets session cookie |
| `POST` | `/api/auth/logout` | — | Clear session |
| `GET` | `/api/auth/me` | — | Current user info |

### User & Billing  `8 routes`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/user/profile` | View or update profile |
| `GET` | `/api/plan` | Current subscription plan |
| `POST` | `/api/plan/change` | `{plan_id}` — switch plan |
| `GET` | `/api/bill` | Bill with 18% GST breakdown |
| `POST` | `/api/bill/pay` | Pay bill (simulated) |
| `GET` | `/api/usage` | Data / calls / SMS usage stats |
| `GET` | `/api/calls` | Recent call history |
| `GET` | `/api/notifications` | App notifications |

### Payment Dashboard  `6 routes`

| Method | Endpoint | Params | Description |
|--------|----------|--------|-------------|
| `GET` | `/api/payment/operators` | `?service=mobile` | Operators for service type |
| `GET` | `/api/payment/plans` | `?operator=Jio&type=prepaid` | Plans for operator |
| `POST` | `/api/payment/detect` | `{mobile}` | Detect operator from prefix |
| `POST` | `/api/payment/my-plan` | `{mobile}` | Current plan + all alternatives |
| `POST` | `/api/payment/recharge` | `{service, operator, number, plan_id, amount}` | Process recharge |
| `GET` | `/api/payment/transactions` | — | Recent transaction history |

**Service types:** `mobile` · `dth` · `broadband` · `postpaid` · `electricity` · `gas` · `water` · `landline`

### Quiz / Tutor Bot  `5 routes`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/quiz/questions` | Gemini generates 8 fresh MCQs · session ID returned · answers stored server-side |
| `POST` | `/api/quiz/submit` | `{session_id, question_id, answer}` → validate + AI explanation |
| `POST` | `/api/quiz/score` | Save score to SQLite |
| `GET` | `/api/quiz/history` | Past quiz scores |
| `POST` | `/api/quiz/chat` | `{message, history}` → AI Tutor (RAG + Gemini) |

### Support Triage Agent  `6 routes`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/triage/analyze` | Full pipeline: NER → classify → draft → ticket |
| `POST` | `/api/triage/entities` | NER only — fast, no AI call |
| `GET` | `/api/triage/tickets` | Queue · filter by `?urgency=HIGH` or `?status=OPEN` |
| `GET` | `/api/triage/tickets/<id>` | Single ticket detail |
| `POST` | `/api/triage/tickets/<id>/status` | `{status}` — OPEN → IN_PROGRESS → RESOLVED → CLOSED |
| `GET` | `/api/triage/stats` | Dashboard: counts by urgency, intent, status, escalations |

### Health  `1 route`

```bash
GET /api/health
```
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "llm_available": true,
  "api_keys": [
    {"provider": "Gemini", "key_suffix": "abc123", "exhausted": false, "active": true},
    {"provider": "Gemini", "key_suffix": "def456", "exhausted": false, "active": false},
    {"provider": "Groq",   "key_suffix": "ghi789", "exhausted": false, "active": true}
  ],
  "vectordb": {
    "plans_indexed": 8,
    "concepts_indexed": 11,
    "similarity_metric": "cosine"
  }
}
```

---

## 📊 Operator Plans Database

### Mobile — 40+ real Indian plans

| Operator | Prepaid | Postpaid | Cheapest | Most Expensive |
|----------|:-------:|:--------:|:--------:|:--------------:|
| 🟦 Jio | 7 plans | 3 plans | ₹155 / 24d | ₹2,999 / 365d |
| 🔴 Airtel | 8 plans | 3 plans | ₹99 / 28d | ₹3,359 / 365d |
| 🟣 Vi | 7 plans | 3 plans | ₹99 / 28d | ₹2,899 / 365d |
| 🟡 BSNL | 5 plans | 2 plans | ₹94 / 28d | ₹1,515 / 365d |

Each plan stores: `id · name · price · validity · data · calls · sms · category · extras[]`

Plan categories: `budget · popular · 5g · long · annual · postpaid`

### Other Services

| Service | Providers |
|---------|-----------|
| 📺 DTH | Tata Play · Airtel DTH · Dish TV · Sun Direct · D2H |
| 🌐 Broadband | Jio Fiber (5 plans ₹399–₹2499) · Airtel Xstream · BSNL Fiber · ACT |
| ⚡ Electricity | 15 boards — BSES · MSEDCL · BESCOM · TNEB · UPPCL · WBSEDCL + more |
| 🔥 Gas | Indraprastha Gas · Mahanagar Gas · Gujarat Gas · Adani Gas |
| 💧 Water | Delhi Jal Board · MCGM · BWSSB · CMWSSB · HMWSSB |
| ☎️ Landline | BSNL · MTNL · Airtel · JioFiber |

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| AI Model | Google Gemini | 2.0 Flash | Quiz gen · explanations · tutor · triage drafts |
| AI Fallback | Groq / Llama 3.3 70B | latest | 500+ tok/s when Gemini exhausted |
| Vector DB | ChromaDB | 0.5.3 | Semantic search · RAG retrieval |
| Embeddings | all-MiniLM-L6-v2 | via ChromaDB | 384-dim text embeddings |
| Backend | Flask | 3.0.3 | Web framework · 35 REST endpoints |
| CORS | Flask-CORS | 4.0.1 | Cross-origin API access |
| Auth | Werkzeug bcrypt | 3.0.3 | Session cookies · password hashing |
| ORM | Flask-SQLAlchemy | 3.1.1 | SQLite models · migrations |
| WSGI | Gunicorn | 22.0.0 | Production multi-worker server |
| Frontend | Vanilla JS SPA | ES2022 | 7-page app · no framework |
| Font | Sora (Google Fonts) | — | Premium dark theme UI |
| Container | Docker | python:3.11-slim | Portable deployment |
| Proxy | Nginx | — | Reverse proxy · SSL termination |
| CI/CD | GitHub Actions | — | Auto test · build · deploy |
| Cloud | AWS EC2 | Ubuntu 22.04 | Live production server |

---

## ☁️ Deploy to AWS EC2

### Automatic via GitHub Actions (Recommended)

**Step 1 — Add GitHub Secrets**

Go to `Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value |
|--------|-------|
| `DOCKER_USER` | `yogeshpatil22` |
| `DOCKER_PASS` | Docker Hub password or access token |
| `EC2_HOST` | Your EC2 public IP address |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Full contents of your `.pem` file |
| `GEMINI_API_KEY` | Your primary Gemini key |
| `GEMINI_API_KEY_1` | Your second Gemini key |
| `GEMINI_API_KEY_2` | Your third Gemini key |
| `GROQ_API_KEY` | Your Groq key |
| `SECRET_KEY` | `telecom-secret-2024` |

**Step 2 — Push to trigger pipeline**

```bash
git push origin main
# Automatically: test → build image → push Docker Hub → SSH deploy → health check
```

### Manual Deploy to EC2

```bash
# SSH in
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# First time only — install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu && newgrp docker

# Clone and configure
git clone https://github.com/patilyogesh22/Telecomm_Platform.git
cd Telecomm_Platform
cp .env.example backend/.env
# Edit backend/.env with your real keys

# Start
docker-compose up -d --build

# Verify
curl http://localhost:5000/api/health
```

### Update Running Instance

```bash
cd ~/Telecomm_Platform
git pull origin main
docker-compose down
docker pull yogeshpatil22/telebot:latest
docker-compose up -d
```

### Open Port 5000

In AWS Console → EC2 → Security Groups → Inbound Rules:

```
Type: Custom TCP  |  Port: 5000  |  Source: 0.0.0.0/0
```

App is live at: `http://YOUR_EC2_IP:5000`

---

## 🔧 Troubleshooting

### `ModuleNotFoundError: No module named 'vector_db'`

Dockerfile must copy files **flat** into `/app`:

```dockerfile
COPY backend/ ./      ✅  — all .py files land in /app/
COPY backend/ ./backend/  ❌  — imports fail
```

### Port 5000 already in use

```bash
docker-compose down --remove-orphans
docker network prune -f
docker-compose up -d
```

### CSS `.badge.5g` invalid selector error

Class names cannot start with a digit. Use `.badge-5g` instead.

### Old Docker syntax on EC2

```bash
docker-compose up -d   # Docker v1 (hyphen)
docker compose up -d   # Docker v2+ (space)
```

### `.pem` file permission denied

```bash
chmod 400 your-key.pem
```

### AI Tutor shows "offline" despite valid key

```bash
# Check key is in container
docker exec telebot cat /app/.env
# If empty, recreate the file on EC2
```

### Gemini 429 despite having keys

Key rotation is automatic. Check `/api/health` to see which keys are exhausted. All keys reset at midnight automatically.

---

## 📊 Project Stats

| Metric | Value |
|--------|------:|
| Python lines of code | 3,366 |
| Frontend lines of code | ~2,400 |
| API endpoints | 35 |
| Mobile plans in database | 40+ |
| Other service providers | 30+ |
| Service payment types | 8 |
| RAG documents indexed | 19 |
| Static fallback quiz questions | 15 |
| NER entity types | 7 |
| Triage intent categories | 13 |
| API keys supported | 4 (3 Gemini + 1 Groq) |

---

## 🤝 Contributing

```bash
# Fork the repo, then:
git checkout -b feat/your-feature
git commit -m "feat: add your feature"
git push origin feat/your-feature
# Open a Pull Request
```

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI quiz generation, explanations, tutor chat, triage drafts
- [Groq](https://groq.com/) — Ultra-fast LLM inference (500+ tokens/sec) as fallback
- [ChromaDB](https://www.trychroma.com/) — Vector database for semantic RAG search
- [Sentence Transformers](https://sbert.net/) — `all-MiniLM-L6-v2` for 384-dim embeddings
- [Flask](https://flask.palletsprojects.com/) — Lightweight Python web framework
- [Sora Font](https://fonts.google.com/specimen/Sora) — Clean modern typeface

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by [patilyogesh22](https://github.com/patilyogesh22)**

⭐ Star this repo if you found it useful!

</div>
