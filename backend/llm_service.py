"""
llm_service.py  —  Gemini 2.5 Flash
Working model confirmed: gemini-2.5-flash
"""

import os, json, time, threading, hashlib
import urllib.request, urllib.error
from dotenv import load_dotenv
load_dotenv()

_api_key  = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL     = "gemini-2.5-flash"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

MAX_TOKENS_EXPLAIN = 350
MAX_TOKENS_CHAT    = 500

# ── Cache ─────────────────────────────────────────────
_cache, _cache_lock = {}, threading.Lock()

def _cache_get(k):
    with _cache_lock: return _cache.get(k)

def _cache_set(k, v):
    with _cache_lock:
        if len(_cache) > 300: del _cache[next(iter(_cache))]
        _cache[k] = v

def _hash(t): return hashlib.md5(t.encode()).hexdigest()

# ── Rate limiter ──────────────────────────────────────
_last, _rlock, MIN_GAP = 0.0, threading.Lock(), 2.0

def _throttle():
    global _last
    with _rlock:
        gap = time.time() - _last
        if gap < MIN_GAP: time.sleep(MIN_GAP - gap)
        _last = time.time()

def is_llm_available(): return bool(_api_key)

# ── Core API call ─────────────────────────────────────
def _call(contents: list, max_tokens: int) -> str:
    if not _api_key: return None
    url     = f"{_BASE_URL}/{MODEL}:generateContent?key={_api_key}"
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
    body = json.dumps(payload).encode()

    for attempt in range(4):
        _throttle()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
                return d["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            raw = e.read().decode() if e.fp else ""
            try:    msg = json.loads(raw).get("error",{}).get("message", raw)
            except: msg = raw
            if e.code == 429:
                wait = (attempt+1) * 8
                print(f"[LLM] 429 — waiting {wait}s (attempt {attempt+1}/4)")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini {e.code}: {msg}")
        except Exception as e:
            raise RuntimeError(f"Network error: {e}")
    return None

# ── Quiz explanation ──────────────────────────────────
def generate_explanation(
    question_text, options, user_key, correct_key,
    correct_text, user_text, is_correct, topic, difficulty, rag_context
) -> str:
    if not is_llm_available():
        return _fallback(is_correct, correct_text, topic)

    opts    = "\n".join(f"  {k}) {v}" for k, v in options.items())
    verdict = "✅ Excellent!" if is_correct else "❌ Not quite:"
    task    = (
        "Reinforce WHY correct. Add one advanced insight."
        if is_correct else
        "Explain why wrong, why correct answer is right using KB. Give real-world analogy. Be encouraging."
    )
    prompt = f"""You are TeleBot, expert telecom educator.
Q ({difficulty}/{topic}): {question_text}
{opts}
Student: {user_key}) {user_text} | Correct: {correct_key}) {correct_text} | {"RIGHT" if is_correct else "WRONG"}
KB: {rag_context[:800]}
Task: {task}
Reply in this format:
**{verdict}**
[1-2 sentence verdict]
**📡 Technical Context:**
[2-3 sentences citing plan names/specs]
**💡 Key Takeaway:**
[One memorable insight]
Max 130 words."""

    ck = _hash(f"{question_text}{user_key}{correct_key}")
    if cached := _cache_get(ck): return cached

    try:
        result = _call([{"role":"user","parts":[{"text":prompt}]}], MAX_TOKENS_EXPLAIN)
        if result:
            _cache_set(ck, result)
            return result
    except Exception as e:
        print(f"[LLM] explain error: {e}")
    return _fallback(is_correct, correct_text, topic)


def _fallback(is_correct, correct_text, topic):
    if is_correct:
        return f"**✅ Correct!** The answer is **{correct_text}**.\n\n**💡 Key Takeaway:** Explore **{topic}** in Plan Explorer to go deeper."
    return f"**❌ Not quite!** Correct answer: **{correct_text}**.\n\n**📡 Technical Context:** Review **{topic}** in Plan Explorer.\n\n**💡 Key Takeaway:** Every wrong answer builds knowledge — keep going! 💪"


# ── AI-Generated Quiz Questions ───────────────────────
def generate_quiz_questions(topic: str = 'Indian telecom plans', num_questions: int = 8) -> list:
    """Generate quiz questions on Indian telecom using Gemini."""
    if not is_llm_available():
        return []

    prompt = f"""You are TeleBot, expert Indian telecom educator.
Generate {num_questions} multiple-choice quiz questions about: "{topic}" — focusing on Jio, Airtel, Vi, BSNL plans, pricing, features, and telecom technology.

Return ONLY a valid JSON array. No markdown, no code fences, no extra text.
Each item must have exactly this structure:
{{
  "id": "ai_q1",
  "question": "Question text?",
  "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
  "correct": "A",
  "topic": "{topic}",
  "difficulty": "medium",
  "rag_query": "relevant search keywords"
}}

Make questions specific: use exact prices (₹209, ₹349), plan names, data amounts, validity periods, OTT benefits."""

    ck = _hash(f"aiquiz_{topic}_{num_questions}")
    if cached := _cache_get(ck): return cached

    try:
        result = _call([{"role": "user", "parts": [{"text": prompt}]}], 3000)
        if not result:
            return []
        text = result.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        questions = json.loads(text.strip())
        # Ensure IDs are unique
        for i, q in enumerate(questions):
            q['id'] = f'ai_q{i+1}_{_hash(q.get("question",""))[:4]}'
        _cache_set(ck, questions)
        return questions
    except Exception as e:
        print(f"[LLM] AI quiz generation error: {e}")
        return []



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

JIOFIBER BROADBAND:
• ₹399 (30Mbps, 3300GB), ₹699 (100Mbps, Unlimited + OTT), ₹999 (200Mbps + Netflix + Prime + Hotstar), ₹1499 (500Mbps + all OTT), ₹2499 (1Gbps + Netflix HD + all OTT)

AIRTEL XSTREAM FIBER:
• ₹499 (40Mbps), ₹799 (100Mbps + Prime), ₹999 (200Mbps + Netflix + Prime + Hotstar), ₹1999 (1Gbps + all OTT)

RULES:
- When user asks about plans for ANY operator (Jio/Airtel/Vi/BSNL), list ALL their plans with prices, validity, data, calls, and OTT benefits
- Format plan lists with bullet points, bold prices and key specs
- Compare plans side-by-side when asked
- Recommend plans based on user needs (budget, data, OTT preference, validity, 5G)
- Keep responses under 4 paragraphs, end with a helpful tip
- Use correct Indian telecom terminology (validity, recharge, data pack, etc.)
- Always mention if a plan includes 5G access"""


def tutor_chat(user_message: str, history: list, rag_context: str) -> str:
    if not is_llm_available():
        return "⚠️ **AI Tutor offline.** Add `GEMINI_API_KEY` to `backend/.env` and restart."

    system = f"{_SYS}\n\nKB:\n{rag_context[:1000]}"

    ck = _hash(user_message + str([m["content"] for m in history[-2:]]))
    if cached := _cache_get(ck): return cached

    # Gemini multi-turn: system as first user+model exchange
    contents = [
        {"role": "user",  "parts": [{"text": system}]},
        {"role": "model", "parts": [{"text": "Understood! I'm TeleBot, ready to help with telecom questions!"}]},
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
        return "⚠️ Empty response — please try again."
    except RuntimeError as e:
        msg = str(e)
        if "429" in msg:
            return "⏳ **Rate limit hit.** Please wait 15 seconds and try again."
        if "401" in msg or "API_KEY_INVALID" in msg:
            return "❌ **Invalid API key.** Check `GEMINI_API_KEY` in `backend/.env`."
        return f"❌ Error: {msg}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"