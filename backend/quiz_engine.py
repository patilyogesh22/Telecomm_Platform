"""
quiz_engine.py
AI-Generated Quiz Engine.
- Gemini generates fresh questions every session via llm_service
- Answers stored server-side in _sessions dict (keyed by session_id)
- Falls back to 15 static questions if AI is unavailable
"""

import random
import uuid
from typing import Optional


# ─────────────────────────────────────────────────────────────
#  In-memory session store  { session_id: { q_id: full_q } }
# ─────────────────────────────────────────────────────────────
_sessions: dict = {}


def store_session(session_id: str, questions: list):
    _sessions[session_id] = {q["id"]: q for q in questions}
    if len(_sessions) > 200:                    # evict oldest
        del _sessions[next(iter(_sessions))]


def get_session_question(session_id: str, question_id: str) -> Optional[dict]:
    return _sessions.get(session_id, {}).get(question_id)


def clear_session(session_id: str):
    _sessions.pop(session_id, None)


def generate_session_id() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────
#  Static fallback question bank (15 questions)
# ─────────────────────────────────────────────────────────────
QUESTIONS = [
    {
        "id": "q001",
        "question": "Which telecom plan is specifically designed for IoT and Machine-to-Machine (M2M) communication?",
        "options": {"A": "SmartDaily 5G", "B": "IoTConnect M2M", "C": "BusinessElite 5G", "D": "BasicConnect 4G"},
        "correct": "B", "topic": "IoT Plans", "difficulty": "easy",
        "rag_query": "IoT M2M machine-to-machine communication plan NB-IoT LTE-M",
        "explanation_context": "IoTConnect M2M at ₹49/SIM supports NB-IoT and LTE-M protocols for low-power device communication.",
    },
    {
        "id": "q002",
        "question": "The FamilyShare Pro plan allows data sharing among how many members maximum?",
        "options": {"A": "2 members", "B": "3 members", "C": "4 members", "D": "6 members"},
        "correct": "C", "topic": "Family Plans", "difficulty": "easy",
        "rag_query": "FamilyShare Pro plan members shared data family",
        "explanation_context": "FamilyShare Pro at ₹999/month shares 100GB among up to 4 members with Disney+ Hotstar included.",
    },
    {
        "id": "q003",
        "question": "Which plan offers a Static IP address — critical for hosting servers and VPNs?",
        "options": {"A": "FamilyShare Pro", "B": "StreamMax 5G", "C": "BusinessElite 5G", "D": "TravelGlobal SIM"},
        "correct": "C", "topic": "Business Plans", "difficulty": "medium",
        "rag_query": "static IP VPN enterprise business plan server hosting",
        "explanation_context": "BusinessElite 5G at ₹1499/month includes Static IP, VPN, Microsoft 365, and 99.9% SLA.",
    },
    {
        "id": "q004",
        "question": "What maximum data speed does the BusinessElite 5G plan deliver on its priority 5G network?",
        "options": {"A": "Up to 150 Mbps", "B": "Up to 500 Mbps", "C": "Up to 1 Gbps", "D": "Up to 2 Gbps"},
        "correct": "D", "topic": "Network Speeds", "difficulty": "medium",
        "rag_query": "BusinessElite 5G speed priority network Gbps",
        "explanation_context": "BusinessElite 5G provides priority 5G at up to 2 Gbps — the fastest plan in the portfolio.",
    },
    {
        "id": "q005",
        "question": "StudentFlex zero-rates (doesn't count toward data) which category of applications?",
        "options": {"A": "Gaming apps", "B": "Social media apps", "C": "Education apps", "D": "Entertainment apps"},
        "correct": "C", "topic": "Special Plans", "difficulty": "easy",
        "rag_query": "StudentFlex zero rating education apps Coursera Khan Academy",
        "explanation_context": "StudentFlex zero-rates 50+ education apps including Coursera and Khan Academy.",
    },
    {
        "id": "q006",
        "question": "Which two low-power wireless protocols does the IoTConnect M2M plan explicitly support?",
        "options": {"A": "3G and 4G LTE", "B": "NB-IoT and LTE-M", "C": "WiFi 6 and Bluetooth 5", "D": "LoRa and Zigbee"},
        "correct": "B", "topic": "IoT Protocols", "difficulty": "hard",
        "rag_query": "NB-IoT LTE-M narrowband IoT low power LPWAN protocol",
        "explanation_context": "NB-IoT and LTE-M are 3GPP LPWAN standards using licensed spectrum with 10+ year battery life.",
    },
    {
        "id": "q007",
        "question": "The TravelGlobal SIM plan provides international coverage in how many countries?",
        "options": {"A": "50+ countries", "B": "75+ countries", "C": "100+ countries", "D": "150+ countries"},
        "correct": "D", "topic": "International Plans", "difficulty": "easy",
        "rag_query": "TravelGlobal SIM international roaming countries coverage",
        "explanation_context": "TravelGlobal SIM at ₹2499/month covers 150+ countries with zero roaming surcharges.",
    },
    {
        "id": "q008",
        "question": "Which plan includes Microsoft 365 Basic as a bundled enterprise benefit?",
        "options": {"A": "StudentFlex", "B": "FamilyShare Pro", "C": "BusinessElite 5G", "D": "SmartDaily 5G"},
        "correct": "C", "topic": "Plan Benefits", "difficulty": "medium",
        "rag_query": "Microsoft 365 enterprise business plan included benefit",
        "explanation_context": "BusinessElite 5G bundles Microsoft 365 Basic, 100GB cloud backup, and a dedicated account manager.",
    },
    {
        "id": "q009",
        "question": "What is the validity period of the StudentFlex prepaid plan?",
        "options": {"A": "28 days", "B": "30 days", "C": "56 days", "D": "84 days"},
        "correct": "C", "topic": "Plan Validity", "difficulty": "easy",
        "rag_query": "StudentFlex validity days prepaid student plan duration",
        "explanation_context": "StudentFlex offers 56-day validity at ₹149 — double the standard 28-day cycle.",
    },
    {
        "id": "q010",
        "question": "The StreamMax 5G plan is specifically optimized for which maximum video streaming resolution?",
        "options": {"A": "720p HD", "B": "1080p Full HD", "C": "4K UHD", "D": "8K"},
        "correct": "C", "topic": "Streaming Plans", "difficulty": "medium",
        "rag_query": "StreamMax 5G 4K streaming optimization OTT bundle",
        "explanation_context": "StreamMax 5G at ₹699/month includes 4K UHD optimization with full OTT bundle and Binge-On mode.",
    },
    {
        "id": "q011",
        "question": "What key latency advantage does 5G provide over 4G LTE for real-time applications?",
        "options": {"A": "5G has 100ms vs 4G 50ms", "B": "5G achieves <1ms vs 4G's 20-50ms", "C": "Both have identical latency", "D": "4G LTE has lower latency than 5G"},
        "correct": "B", "topic": "5G Technology", "difficulty": "hard",
        "rag_query": "5G latency milliseconds vs 4G LTE real-time applications",
        "explanation_context": "5G achieves sub-1ms latency enabling autonomous vehicles and real-time industrial control.",
    },
    {
        "id": "q012",
        "question": "Which plan includes airport lounge access as a bundled travel benefit?",
        "options": {"A": "BusinessElite 5G", "B": "FamilyShare Pro", "C": "TravelGlobal SIM", "D": "StreamMax 5G"},
        "correct": "C", "topic": "Travel Benefits", "difficulty": "medium",
        "rag_query": "airport lounge access travel benefit international SIM",
        "explanation_context": "TravelGlobal SIM includes 2 airport lounge accesses per month alongside global coverage.",
    },
    {
        "id": "q013",
        "question": "What SLA uptime percentage does the BusinessElite 5G plan guarantee?",
        "options": {"A": "95% uptime", "B": "98% uptime", "C": "99.5% uptime", "D": "99.9% uptime"},
        "correct": "D", "topic": "Enterprise SLA", "difficulty": "medium",
        "rag_query": "BusinessElite SLA uptime guarantee enterprise 99.9",
        "explanation_context": "99.9% SLA means less than 8.7 hours downtime per year — critical for enterprise operations.",
    },
    {
        "id": "q014",
        "question": "NB-IoT operates in which type of spectrum, making it reliable and interference-free?",
        "options": {"A": "Unlicensed ISM band (2.4GHz)", "B": "Licensed cellular spectrum", "C": "Free-space optical", "D": "TVWS (TV White Space)"},
        "correct": "B", "topic": "IoT Protocols", "difficulty": "hard",
        "rag_query": "NB-IoT licensed spectrum cellular band reliable interference",
        "explanation_context": "NB-IoT uses licensed spectrum (700–900 MHz) ensuring no interference unlike WiFi or LoRa.",
    },
    {
        "id": "q015",
        "question": "Which plan offers 'Binge-On' mode where video on partner apps doesn't count toward data?",
        "options": {"A": "SmartDaily 5G", "B": "FamilyShare Pro", "C": "StreamMax 5G", "D": "BasicConnect 4G"},
        "correct": "C", "topic": "Streaming Plans", "difficulty": "medium",
        "rag_query": "StreamMax Binge-On mode zero-rated video streaming partner apps",
        "explanation_context": "StreamMax 5G Binge-On zero-rates Netflix, Prime, Hotstar, SonyLIV and Zee5.",
    },
]


# ─────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────

def get_questions(difficulty: str = "all", count: int = 8) -> list:
    """Return shuffled fallback questions without correct answers."""
    pool = QUESTIONS if difficulty == "all" else [q for q in QUESTIONS if q["difficulty"] == difficulty]
    if not pool:
        pool = QUESTIONS
    selected = random.sample(pool, min(count, len(pool)))
    return [_strip_answer(q) for q in selected]


def validate_answer(qid: str, user_answer: str) -> dict:
    """Validate answer against static fallback bank."""
    q = next((x for x in QUESTIONS if x["id"] == qid), None)
    if not q:
        return {"error": f"Question {qid} not found"}
    answer = user_answer.upper().strip()
    return {
        "is_correct":          answer == q["correct"],
        "correct_key":         q["correct"],
        "correct_text":        q["options"][q["correct"]],
        "user_key":            answer,
        "user_text":           q["options"].get(answer, "Unknown"),
        "rag_query":           q["rag_query"],
        "topic":               q["topic"],
        "difficulty":          q["difficulty"],
        "question_text":       q["question"],
        "all_options":         q["options"],
        "explanation_context": q.get("explanation_context", ""),
    }


def validate_session_answer(session_id: str, question_id: str, user_answer: str) -> dict:
    """Validate answer from an AI-generated session."""
    q = get_session_question(session_id, question_id)
    if not q:
        return validate_answer(question_id, user_answer)   # session expired → fallback
    answer = user_answer.upper().strip()
    return {
        "is_correct":          answer == q["correct"],
        "correct_key":         q["correct"],
        "correct_text":        q["options"][q["correct"]],
        "user_key":            answer,
        "user_text":           q["options"].get(answer, "Unknown"),
        "rag_query":           q.get("rag_query", f"{q.get('topic','')} {q['question'][:60]}"),
        "topic":               q.get("topic", "Telecom"),
        "difficulty":          q.get("difficulty", "medium"),
        "question_text":       q["question"],
        "all_options":         q["options"],
        "explanation_context": q.get("explanation_context", ""),
    }


def get_question_by_id(qid: str) -> Optional[dict]:
    return next((q for q in QUESTIONS if q["id"] == qid), None)


def get_topics() -> list:
    return sorted(set(q["topic"] for q in QUESTIONS))


def get_stats() -> dict:
    difficulties = {"easy": 0, "medium": 0, "hard": 0}
    topics = {}
    for q in QUESTIONS:
        difficulties[q["difficulty"]] = difficulties.get(q["difficulty"], 0) + 1
        topics[q["topic"]] = topics.get(q["topic"], 0) + 1
    return {
        "total_questions": len(QUESTIONS),
        "by_difficulty":   difficulties,
        "by_topic":        topics,
        "topics":          get_topics(),
        "ai_generated":    True,
    }


def _strip_answer(q: dict) -> dict:
    return {
        "id":         q["id"],
        "question":   q["question"],
        "options":    q["options"],
        "difficulty": q["difficulty"],
        "topic":      q["topic"],
    }