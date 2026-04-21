"""
llm_service.py  —  Gemini AI Service with Multi-Key Rotation

MULTI-API-KEY SUPPORT:
  Add keys to your .env file:
    GEMINI_API_KEY=AIza...          ← primary key (always read)
    GEMINI_API_KEY_1=AIza...        ← key slot 1
    GEMINI_API_KEY_2=AIza...        ← key slot 2
    GEMINI_API_KEY_3=AIza...        ← key slot 3
    (add as many as you have)

  When a key hits 429 (quota exhausted) the system automatically
  rotates to the next available key. Falls back to offline mode
  only when ALL keys are exhausted.

FEATURES:
  - generate_quiz_questions()   →  AI-generated MCQs every session
  - generate_explanation()      →  rich why-right / why-wrong feedback
  - tutor_chat()                →  conversational RAG-grounded answers
  - _call()                     →  shared low-level caller (used by triage_agent too)
"""

import os, json, time, threading, hashlib, datetime, uuid
import urllib.request, urllib.error
from dotenv import load_dotenv
load_dotenv()
import requests
# ─── Model ────────────────────────────────────────────────────
MODEL     = "gemini-2.0-flash"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

MAX_TOKENS_QUIZ    = 3000
MAX_TOKENS_EXPLAIN = 500
MAX_TOKENS_CHAT    = 800

# ─── Multi-key pool ───────────────────────────────────────────
def _load_api_keys() -> list:
    """
    Collect all API keys from environment.
    Reads GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, … GEMINI_API_KEY_9
    Returns a deduplicated list of non-empty key strings.
    """
    keys = []
    # Primary key
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        keys.append(k)
    # Numbered keys  _1 through _9
    for i in range(1, 10):
        k = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys
def _load_provider_keys(prefix, max_keys=10):
    keys = []

    for i in range(max_keys):
        name = prefix if i == 0 else f"{prefix}_{i}"
        val = os.getenv(name, "").strip()

        if val:
            keys.append(val)

    return keys

_hf_keys = _load_provider_keys("HF_API_KEY")
_groq_keys   = _load_provider_keys("GROQ_API_KEY")

def _call_groq(prompt: str, max_tokens=800):

    for key in _groq_keys:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens
                },
                timeout=30
            )

            if r.status_code == 200:
                print("[LLM] Groq active.")
                return r.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print("GROQ Error:", e)
            continue

    return None
# Pool state — protected by _pool_lock
_pool_lock   = threading.Lock()
_api_keys    = _load_api_keys()          # list of key strings
_key_index   = 0                         # current active key index
_key_states  = {}                        # { key: {"exhausted": bool, "reset_at": datetime|None} }

for _k in _api_keys:
    _key_states[_k] = {"exhausted": False, "reset_at": None}

def _current_key() -> str | None:
    """Return the currently active non-exhausted key, or None."""
    with _pool_lock:
        if not _api_keys:
            return None
        # Try from current index, wrapping around
        for i in range(len(_api_keys)):
            idx = (_key_index + i) % len(_api_keys)
            k   = _api_keys[idx]
            st  = _key_states.get(k, {})
            if not st.get("exhausted", False):
                return k
        return None

def _rotate_key(exhausted_key: str):
    """Mark a key as exhausted and advance the index to the next key."""
    global _key_index
    with _pool_lock:
        if exhausted_key in _key_states:
            _key_states[exhausted_key]["exhausted"]  = True
            _key_states[exhausted_key]["reset_at"]   = None  # no auto-reset; manual or restart
            print(f"[LLM] Daily quota reached. Switching to backup Gemini key...")
        # Find next non-exhausted key
        for i in range(1, len(_api_keys) + 1):
            idx = (_key_index + i) % len(_api_keys)
            k   = _api_keys[idx]
            if not _key_states.get(k, {}).get("exhausted", False):
                _key_index = idx
                print("[LLM] Backup Gemini key activated.")
                return
        # All keys exhausted

def _reset_all_keys():
    """Reset all keys (call at midnight or on server restart)."""
    with _pool_lock:
        for k in _api_keys:
            _key_states[k]["exhausted"] = False
        print("[LLM] 🔄 All API keys reset")

def is_llm_available():
    return (
        _current_key() is not None
        or len(_hf_keys) > 0
        or len(_groq_keys) > 0
    )

def get_key_status() -> list:
    """Return status of all keys (for health endpoint)."""
    with _pool_lock:
        return [
            {
                "key_suffix":  k[-6:],
                "exhausted":   _key_states.get(k, {}).get("exhausted", False),
                "active":      (_api_keys[_key_index] == k) if _api_keys else False,
            }
            for k in _api_keys
        ]

# ─── Midnight reset thread ────────────────────────────────────
def _midnight_reset_loop():
    """Background thread that resets all keys at midnight every day."""
    while True:
        now      = datetime.datetime.now()
        midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=5, microsecond=0
        )
        wait_sec = (midnight - now).total_seconds()
        time.sleep(max(wait_sec, 1))
        _reset_all_keys()

_reset_thread = threading.Thread(target=_midnight_reset_loop, daemon=True)
_reset_thread.start()

# ─── Daily quota guard per key ────────────────────────────────
DAILY_CALL_LIMIT = 80          # per-key soft limit to stay under free tier

_quota     = {}   # { key: {"date": str, "calls": int} }
_quota_lock = threading.Lock()

def _quota_ok(key: str) -> bool:
    """Return True if this key has not hit its daily soft limit."""
    with _quota_lock:
        today = datetime.date.today().isoformat()
        if key not in _quota or _quota[key]["date"] != today:
            _quota[key] = {"date": today, "calls": 0}
        _quota[key]["calls"] += 1
        if _quota[key]["calls"] > DAILY_CALL_LIMIT:
            print(f"[LLM] Key …{key[-6:]} hit daily soft limit ({DAILY_CALL_LIMIT} calls)")
            return False
        return True

# ─── Cache ────────────────────────────────────────────────────
_cache, _cache_lock = {}, threading.Lock()

def _cache_get(k):
    with _cache_lock: return _cache.get(k)

def _cache_set(k, v):
    with _cache_lock:
        if len(_cache) > 300:
            del _cache[next(iter(_cache))]
        _cache[k] = v

def clear_cache():
    with _cache_lock: _cache.clear()

def _hash(t): return hashlib.md5(t.encode()).hexdigest()

# ─── Rate limiter (global) ────────────────────────────────────
_last, _rlock, MIN_GAP = 0.0, threading.Lock(), 4.0

def _throttle():
    global _last
    with _rlock:
        gap = time.time() - _last
        if gap < MIN_GAP:
            time.sleep(MIN_GAP - gap)
        _last = time.time()


# ═════════════════════════════════════════════════════════════
#  CORE API CALLER  — multi-key rotation built-in
# ═════════════════════════════════════════════════════════════

def _call(contents: list, max_tokens: int, temperature: float = 0.7) -> str:
    """
    Low-level Gemini API caller with automatic key rotation.

    Retry logic:
      - 429 (rate limit)  → mark key exhausted, rotate, retry immediately
      - 503 (overloaded)  → wait 5/10/15 s, retry same key
      - other HTTP error  → raise RuntimeError
      - All keys gone     → return None (offline mode)

    Called by: generate_explanation, generate_quiz_questions,
               tutor_chat, triage_agent.analyze_with_ai
    """
    max_attempts = min(len(_api_keys) * 3 + 3, 12)

    for attempt in range(max_attempts):
        key = _current_key()
        if not key:
            print("[LLM] Gemini exhausted. Trying backups...")
            break

        if not _quota_ok(key):
            _rotate_key(key)
            continue

        _throttle()

        url     = f"{_BASE_URL}/{MODEL}:generateContent?key={key}"
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     temperature,
            },
        }
        body = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
                return d["candidates"][0]["content"]["parts"][0]["text"]

        except urllib.error.HTTPError as e:
            raw = e.read().decode() if e.fp else ""
            try:    msg = json.loads(raw).get("error", {}).get("message", raw)
            except: msg = raw

            if e.code == 429:
                # Quota exhausted on this key — rotate and retry
                print(f"[LLM] Gemini quota reached for current key. Switching key...")
                _rotate_key(key)
                continue  # retry with next key

            if e.code == 503:
                wait = (attempt + 1) * 5
                print(f"[LLM] 503 overloaded — waiting {wait}s (attempt {attempt+1})")
                time.sleep(wait)
                continue

            if e.code in (500, 502):
                wait = 3
                print(f"[LLM] {e.code} server error — waiting {wait}s")
                time.sleep(wait)
                continue

            raise RuntimeError(f"Gemini {e.code}: {msg}")

        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(3)
                continue
            raise RuntimeError(f"Network error: {e}")

        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")

    prompt_text = contents[-1]["parts"][0]["text"]


    print("[LLM] Gemini failed. Trying Groq...")
    backup = _call_groq(prompt_text, max_tokens)

    if backup:
        return backup
    print("[LLM] Groq unavailable. Switching to offline mode...")
    return None



# ═════════════════════════════════════════════════════════════
#  QUIZ GENERATION
# ═════════════════════════════════════════════════════════════

# Full telecom knowledge injected into quiz generation prompt
_PLAN_KNOWLEDGE = """
PLATFORM PLANS (name | price | key specs):
1. BasicConnect 4G    | ₹199/28d  | 1GB 4G 25Mbps, 100min, no contract, data rollover
2. SmartDaily 5G      | ₹299/28d  | 2GB/day 5G 1Gbps, unlimited calls, Netflix basic, Wi-Fi calling
3. FamilyShare Pro    | ₹999/30d  | 100GB shared 5G 500Mbps, 4 members, Disney+Hotstar, 20-country roaming
4. BusinessElite 5G   | ₹1499/30d | Unlimited 5G priority 2Gbps, Static IP, VPN, Microsoft365 Basic, 99.9% SLA
5. TravelGlobal SIM   | ₹2499/30d | 5GB intl + unlimited domestic, 150+ countries, 200 intl min, lounge 2x/month
6. IoTConnect M2M     | ₹49/SIM/30d | 500MB, NB-IoT + LTE-M, bulk API, FOTA, 50 SMS alerts
7. StudentFlex        | ₹149/56d  | 1.5GB/day 4G 150Mbps, edu zero-rating 50+ apps, Google One 15GB, night unlimited
8. StreamMax 5G       | ₹699/30d  | 75GB 5G 1.5Gbps, 4K UHD, Netflix+Prime+Hotstar+SonyLIV+Zee5, Binge-On mode

REAL OPERATOR PLANS:
JIO:    ₹155(24d/1.5GB) ₹209(28d/2GB+Netflix) ₹299(28d/3GB+Netflix) ₹349(28d/5G) ₹533(84d/2GB) ₹2999(365d)
AIRTEL: ₹99(budget/1GB) ₹179(1.5GB) ₹239(2GB) ₹329(3GB+Prime) ₹409(5G+Prime) ₹3359(annual)
VI:     ₹99(budget) ₹179(1.5GB+Rollover) ₹239(2GB+Binge) ₹299(3GB+Hotstar) ₹359(5G Ready)
BSNL:   ₹94(28d/2GB cheapest) ₹197(54d/2GB) ₹247(30d/3GB) ₹1515(365d)

TECH CONCEPTS:
- 5G: <1ms latency vs 4G 20-50ms, 20Gbps peak, 3 bands (sub-1GHz/mid-band/mmWave)
- NB-IoT: 3GPP Rel-13, licensed 700-900MHz, 10yr+ battery, 50K devices/cell
- LTE-M: voice+mobility+FOTA, 1Mbps, PSM+eDRX battery saving
- VoLTE: HD voice over IMS, <1s call setup, simultaneous voice+data
- Static IP: fixed public IP for servers/CCTV/VPN/SCADA
- Network Slicing: eMBB/URLLC/mMTC virtual networks on 5G core
- QoS/QCI: QCI-1 VoLTE, QCI-4 gaming, QCI-9 best-effort
- eSIM: GSMA SGP.22, remote provisioning, no physical SIM swap
"""


def generate_quiz_questions(
    difficulty:    str  = "all",
    count:         int  = 8,
    rag_context:   str  = "",
    topic:         str  = "Indian telecom plans",     # kept for backward compat
    num_questions: int  = None,                        # kept for backward compat
) -> list:
    """
    Generate fresh quiz MCQs using Gemini.

    Accepts both calling conventions:
      generate_quiz_questions(difficulty="medium", count=8, rag_context="…")   ← app.py style
      generate_quiz_questions(topic="…", num_questions=8)                       ← legacy style

    Returns list of full question dicts (with correct answers) for server-side storage.
    Returns [] on any failure — caller falls back to static question bank.
    """
    if not is_llm_available():
        return []

    # Handle legacy call style
    if num_questions is not None:
        count = num_questions

    # Difficulty instruction
    if difficulty == "easy":
        diff_note = f"ALL {count} questions EASY — direct lookups of plan names, prices, basic features."
    elif difficulty == "medium":
        diff_note = f"ALL {count} questions MEDIUM — comparisons, protocol basics, numeric specs."
    elif difficulty == "hard":
        diff_note = f"ALL {count} questions HARD — deep protocol details (NB-IoT specs, 5G bands, QCI values)."
    else:
        n_e = count // 3
        n_h = count // 3
        n_m = count - n_e - n_h
        diff_note = f"Mix: {n_e} easy, {n_m} medium, {n_h} hard."

    extra_ctx = f"\nExtra context:\n{rag_context[:400]}" if rag_context else ""

    prompt = f"""You are a telecom quiz generator. Generate exactly {count} multiple-choice questions about: "{topic}".

KNOWLEDGE BASE:
{_PLAN_KNOWLEDGE}{extra_ctx}

DIFFICULTY: {diff_note}

STRICT RULES:
- Exactly 4 options per question: A, B, C, D
- Exactly ONE correct answer per question
- All 4 options must be plausible (no obviously silly distractors)
- Every question must be answerable from the knowledge base — no invented facts
- Vary topics: plan pricing, features, protocols, speeds, validity, OTT, operators
- No duplicate questions
- Use real plan names, prices (₹), speeds (Mbps/Gbps), and specific numbers

OUTPUT: Return ONLY a raw JSON array, no markdown, no backticks, no explanation.
[
  {{
    "question": "Which plan offers Binge-On mode?",
    "options": {{"A": "SmartDaily 5G", "B": "FamilyShare Pro", "C": "StreamMax 5G", "D": "BasicConnect 4G"}},
    "correct": "C",
    "topic": "Streaming Plans",
    "difficulty": "medium",
    "explanation_context": "StreamMax 5G at ₹699 includes Binge-On mode that zero-rates Netflix, Prime, Hotstar.",
    "rag_query": "StreamMax Binge-On zero-rated streaming OTT"
  }}
]

Generate exactly {count} questions now:"""

    # Cache check (skip cache for hard/mixed so questions stay fresh)
    ck = _hash(f"quiz_{difficulty}_{count}_{topic}")
    if difficulty not in ("hard", "all"):
        cached = _cache_get(ck)
        if cached:
            return cached

    try:
        raw = _call(
            [{"role": "user", "parts": [{"text": prompt}]}],
            MAX_TOKENS_QUIZ,
            temperature=0.9
        )
        if not raw:
            return []

        # Strip markdown fences if model adds them
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        questions = json.loads(raw)

        # Validate and assign unique IDs
        valid = []
        for i, q in enumerate(questions):
            if not all(k in q for k in ("question", "options", "correct")):
                continue
            if not isinstance(q["options"], dict) or len(q["options"]) < 4:
                continue
            if q["correct"] not in q["options"]:
                continue
            q["id"]         = f"ai_q{i+1}_{_hash(q.get('question',''))[:6]}"
            q["topic"]      = q.get("topic", topic)
            q["difficulty"] = q.get("difficulty", "medium")
            q.setdefault("explanation_context", "")
            q.setdefault("rag_query", f"{q['topic']} {q['question'][:60]}")
            valid.append(q)

        print(f"[LLM] ✅ Generated {len(valid)}/{count} AI quiz questions")
        if valid and difficulty not in ("hard", "all"):
            _cache_set(ck, valid)
        return valid

    except json.JSONDecodeError as e:
        print(f"[LLM] ❌ JSON parse error in quiz generation: {e}")
        return []
    except Exception as e:
        print(f"[LLM] ❌ Quiz generation failed: {e}")
        return []


# ═════════════════════════════════════════════════════════════
#  QUIZ EXPLANATION
# ═════════════════════════════════════════════════════════════

def generate_explanation(
    question_text:       str,
    options:             dict,
    user_key:            str,
    correct_key:         str,
    correct_text:        str,
    user_text:           str,
    is_correct:          bool,
    topic:               str,
    difficulty:          str,
    rag_context:         str,
    explanation_context: str = "",
) -> str:
    """
    Generate a rich AI explanation:
    - Why the correct answer is right (with real specs/prices)
    - Why each wrong option is wrong (one sentence each)
    - Key takeaway
    Falls back to a simple template if AI is offline.
    """
    if not is_llm_available():
        return _fallback_explanation(is_correct, correct_text, topic)

    ck = _hash(f"{question_text}{user_key}{correct_key}")
    cached = _cache_get(ck)
    if cached:
        return cached

    wrong_options = "\n".join(
        f"  - {k}) {v}"
        for k, v in options.items()
        if k != correct_key
    )

    prompt = f"""You are TeleBot, expert telecom educator.

QUESTION ({difficulty} / {topic}):
{question_text}

OPTIONS:
{chr(10).join(f"  {k}) {v}" for k, v in options.items())}

CORRECT: {correct_key}) {correct_text}
STUDENT: {"RIGHT ✅" if is_correct else f"WRONG ❌ — chose {user_key}) {user_text}"}

KNOWLEDGE:
{explanation_context}
{rag_context[:600]}

Write in this exact format (use **bold** markdown):

{"**✅ Excellent!**" if is_correct else "**❌ Not quite!**"} [One sentence {"confirming the answer" if is_correct else f"stating correct answer is {correct_key}) {correct_text}"}.] 

**📡 Why {correct_key}) {correct_text} is correct:**
[2–3 sentences with specific facts, real prices ₹, speeds Mbps/Gbps, feature names from knowledge base.]

**🚫 Why the other options are wrong:**
{wrong_options}
[For EACH wrong option above: one short sentence explaining why it is incorrect.]

**💡 Key Takeaway:**
[One memorable sentence — the most important thing to remember about this topic.]

Keep total under 160 words. Be specific and factual."""

    try:
        result = _call(
            [{"role": "user", "parts": [{"text": prompt}]}],
            MAX_TOKENS_EXPLAIN,
            temperature=0.6
        )
        if result:
            _cache_set(ck, result)
            return result
    except Exception as e:
        print(f"[LLM] explanation error: {e}")

    return _fallback_explanation(is_correct, correct_text, topic)


def _fallback_explanation(is_correct: bool, correct_text: str, topic: str) -> str:
    if is_correct:
        return (
            f"**✅ Correct!** The answer is **{correct_text}**.\n\n"
            f"**💡 Key Takeaway:** Explore **{topic}** in Plan Explorer to go deeper."
        )
    return (
        f"**❌ Not quite!** Correct answer: **{correct_text}**.\n\n"
        f"**📡 Technical Context:** Review **{topic}** in Plan Explorer.\n\n"
        f"**💡 Key Takeaway:** Every wrong answer builds knowledge — keep going! 💪"
    )


# ═════════════════════════════════════════════════════════════
#  AI TUTOR CHAT
# ═════════════════════════════════════════════════════════════

_SYS = """You are TeleBot — expert AI telecom tutor and assistant for an Indian telecom platform.

You know ALL Indian telecom operator plans in detail:

JIO PREPAID:
• ₹155 (24d, 1.5GB/day, Unlimited calls)
• ₹209 (28d, 2GB/day, Unlimited calls, Netflix Mobile 28d)
• ₹299 (28d, 3GB/day, Unlimited calls, Netflix Basic 28d)
• ₹349 (28d, Unlimited 5G data, Unlimited calls — True 5G plan)
• ₹533 (84d, 2GB/day, Unlimited calls)
• ₹601 (84d, 3GB/day, Unlimited calls, Netflix 84d)
• ₹2999 (365d, 2.5GB/day, Unlimited calls — Annual plan)

JIO POSTPAID:
• ₹399 (75GB), ₹599 (125GB + Netflix + Prime), ₹999 (Unlimited + Netflix Standard + Prime + Hotstar)

AIRTEL PREPAID:
• ₹99 (28d, 1GB, 100 min — Budget plan)
• ₹179 (28d, 1.5GB/day, Unlimited calls)
• ₹239 (28d, 2GB/day, Unlimited calls)
• ₹329 (28d, 3GB/day, Unlimited calls, Amazon Prime 30d)
• ₹409 (28d, Unlimited 5G, Unlimited calls, Amazon Prime)
• ₹479 (56d, 1.5GB/day, Unlimited calls)
• ₹569 (84d, 2GB/day, Unlimited calls)
• ₹3359 (365d, 2.5GB/day, Unlimited calls — Annual plan)

AIRTEL POSTPAID:
• ₹399 (75GB + Prime + Hotstar), ₹499 (Unlimited + Netflix + Prime + Hotstar), ₹999 (Unlimited + Netflix + Prime + Hotstar + International Roaming)

VI (VODAFONE IDEA) PREPAID:
• ₹99 (28d, 1GB — Budget plan)
• ₹179 (28d, 1.5GB/day, Unlimited calls, Weekend Data Rollover)
• ₹239 (28d, 2GB/day, Unlimited calls, Binge All Night free)
• ₹299 (28d, 3GB/day, Unlimited calls, Hotstar 30d)
• ₹359 (28d, 2.5GB/day, Unlimited calls — 5G Ready)
• ₹553 (84d, 1.5GB/day, Unlimited calls)
• ₹2899 (365d, 1.5GB/day, Unlimited calls — Annual plan)

VI POSTPAID:
• ₹399 (75GB + Prime), ₹499 (100GB + Netflix + Prime), ₹699 (Unlimited + Netflix + Prime + Hotstar)

BSNL PREPAID:
• ₹94 (28d, 2GB/day, Unlimited calls — Most affordable)
• ₹197 (54d, 2GB/day, Unlimited calls — Best value per day)
• ₹247 (30d, 3GB/day, Unlimited calls)
• ₹398 (81d, 3GB/day, Unlimited calls)
• ₹1515 (365d, 2GB/day, Unlimited calls — Annual plan)

JIO FIBER BROADBAND:
• ₹399 (30Mbps, 3300GB), ₹699 (100Mbps, Unlimited+OTT), ₹999 (200Mbps+Netflix+Prime+Hotstar), ₹1499 (500Mbps+all OTT), ₹2499 (1Gbps+Netflix HD+all OTT)

AIRTEL XSTREAM FIBER:
• ₹499 (40Mbps), ₹799 (100Mbps+Prime), ₹999 (200Mbps+Netflix+Prime+Hotstar), ₹1999 (1Gbps+all OTT)

RULES:
- When user asks about plans for ANY operator (Jio/Airtel/Vi/BSNL), list ALL their plans
- Format with bullet points, bold prices and key specs
- Compare plans side-by-side when asked
- Recommend plans based on user needs (budget, data, OTT, validity, 5G)
- Keep responses concise but complete — end with a helpful tip
- Use correct Indian telecom terminology
- Always mention if a plan includes 5G access"""


def _offline_tutor(message: str) -> str:
    """Rule-based tutor response when all Gemini keys are exhausted."""
    m = message.lower()

    if any(w in m for w in ["jio", "reliance"]):
        return ("**Jio Prepaid Plans:**\n"
                "• ₹155 — 1.5GB/day, 24 days, Unlimited calls\n"
                "• ₹209 — 2GB/day, 28 days, Netflix Mobile\n"
                "• ₹299 — 3GB/day, 28 days, Netflix Basic\n"
                "• ₹349 — Unlimited 5G, 28 days\n"
                "• ₹533 — 2GB/day, 84 days\n"
                "• ₹2999 — 2.5GB/day, 365 days (Annual)\n\n"
                "💡 **Tip:** ₹349 is the best 5G plan. ₹2999 is best value annually.")

    if any(w in m for w in ["airtel", "bharti"]):
        return ("**Airtel Prepaid Plans:**\n"
                "• ₹99 — 1GB, 28 days, 100 min\n"
                "• ₹179 — 1.5GB/day, 28 days\n"
                "• ₹239 — 2GB/day, 28 days\n"
                "• ₹329 — 3GB/day, 28 days, Amazon Prime\n"
                "• ₹409 — Unlimited 5G, 28 days, Amazon Prime\n"
                "• ₹569 — 2GB/day, 84 days\n"
                "• ₹3359 — 2.5GB/day, 365 days (Annual)\n\n"
                "💡 **Tip:** ₹409 for 5G. ₹329 gives Prime + 3GB/day.")

    if any(w in m for w in ["vi ", "vodafone", "idea"]):
        return ("**Vi Prepaid Plans:**\n"
                "• ₹99 — 1GB, 28 days\n"
                "• ₹179 — 1.5GB/day, 28 days, Weekend Rollover\n"
                "• ₹239 — 2GB/day, 28 days, Binge All Night\n"
                "• ₹299 — 3GB/day, 28 days, Hotstar\n"
                "• ₹359 — 2.5GB/day, 28 days, 5G Ready\n"
                "• ₹2899 — 1.5GB/day, 365 days (Annual)\n\n"
                "💡 **Tip:** ₹239 includes free night data. ₹299 gives Hotstar.")

    if "bsnl" in m:
        return ("**BSNL Prepaid Plans:**\n"
                "• ₹94 — 2GB/day, 28 days — Most affordable!\n"
                "• ₹197 — 2GB/day, 54 days — Best value\n"
                "• ₹247 — 3GB/day, 30 days\n"
                "• ₹398 — 3GB/day, 81 days\n"
                "• ₹1515 — 2GB/day, 365 days (Annual)\n\n"
                "💡 **Tip:** BSNL ₹94 is the cheapest 2GB/day plan in India.")

    if any(w in m for w in ["5g", "five g"]):
        return ("**Best 5G Plans in India:**\n"
                "• Jio ₹349 — Unlimited 5G, 28 days\n"
                "• Airtel ₹409 — Unlimited 5G + Amazon Prime, 28 days\n"
                "• Vi ₹359 — 2.5GB/day 5G Ready, 28 days\n\n"
                "💡 **Tip:** Airtel has widest 5G coverage. Jio has most 5G cities.")

    if any(w in m for w in ["annual", "yearly", "365", "year"]):
        return ("**Best Annual Plans (365 days):**\n"
                "• Jio ₹2999 — 2.5GB/day, Unlimited calls\n"
                "• Airtel ₹3359 — 2.5GB/day, Unlimited calls\n"
                "• Vi ₹2899 — 1.5GB/day, Unlimited calls\n"
                "• BSNL ₹1515 — 2GB/day, Unlimited calls\n\n"
                "💡 **Best value:** BSNL ₹1515 — cheapest annual plan with good data.")

    if any(w in m for w in ["compare", "vs", "better", "best", "recommend"]):
        return ("**Quick Comparison — 2GB/day plans:**\n"
                "| Operator | Price | Validity | Extra |\n"
                "|---|---|---|---|\n"
                "| Jio | ₹209 | 28d | Netflix Mobile |\n"
                "| Airtel | ₹239 | 28d | — |\n"
                "| Vi | ₹239 | 28d | Binge All Night |\n"
                "| BSNL | ₹197 | 54d | — |\n\n"
                "💡 **Winner:** BSNL for value, Jio for OTT benefits.")

    return ("⚠️ **AI Tutor offline** — all API keys exhausted for today. Built-in knowledge:\n\n"
            "**Cheapest:** BSNL ₹94 (2GB/day, 28d)\n"
            "**Best 5G:** Jio ₹349 or Airtel ₹409\n"
            "**Best OTT:** Jio ₹209 (Netflix) or Airtel ₹329 (Prime)\n"
            "**Best annual:** BSNL ₹1515 or Jio ₹2999\n\n"
            "Keys reset at midnight. Ask me anything specific!")


def tutor_chat(user_message: str, history: list, rag_context: str) -> str:
    """
    Multi-turn AI Tutor chat.
    Injects full plan knowledge + RAG context into Gemini.
    Falls back to offline_tutor() when all keys are exhausted.
    """
    if not is_llm_available():
        return ("⚠️ **AI Tutor offline** (all API keys exhausted for today). "
                "Here is what I know from built-in knowledge:\n\n"
                + _offline_tutor(user_message))

    system = f"{_SYS}\n\nKNOWLEDGE BASE CONTEXT:\n{rag_context[:1000]}"

    ck = _hash(user_message + str([m["content"] for m in history[-2:]]))
    cached = _cache_get(ck)
    if cached:
        return cached

    contents = [
        {"role": "user",  "parts": [{"text": system}]},
        {"role": "model", "parts": [{"text": "Understood! I'm TeleBot, ready to help with all telecom questions!"}]},
    ]
    for m in history[-8:]:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        result = _call(contents, MAX_TOKENS_CHAT)
        if result:
            _cache_set(ck, result)
            return result
        # _call returned None — all keys exhausted
        return ("⚠️ **AI Tutor offline** (daily quota reached). "
                "Here is what I know:\n\n" + _offline_tutor(user_message))
    except RuntimeError as e:
        msg = str(e)
        if "401" in msg or "API_KEY_INVALID" in msg:
            return "❌ **Invalid API key.** Check `GEMINI_API_KEY` in `backend/.env`."
        return f"❌ Error: {msg}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"