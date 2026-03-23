"""
quiz_engine.py
Quiz question bank, answer validation, and score tracking
"""

import random
from typing import Optional

# ─────────────────────────────────────────────
#  Question Bank
# ─────────────────────────────────────────────
QUESTIONS = [
    {
        "id": "q001",
        "question": "Which telecom plan is specifically designed for IoT and Machine-to-Machine (M2M) communication?",
        "options": {
            "A": "SmartDaily 5G",
            "B": "IoTConnect M2M",
            "C": "BusinessElite 5G",
            "D": "BasicConnect 4G"
        },
        "correct": "B",
        "topic": "IoT Plans",
        "difficulty": "easy",
        "rag_query": "IoT M2M machine-to-machine communication plan NB-IoT LTE-M",
    },
    {
        "id": "q002",
        "question": "The FamilyShare Pro plan allows data sharing among how many members maximum?",
        "options": {
            "A": "2 members",
            "B": "3 members",
            "C": "4 members",
            "D": "6 members"
        },
        "correct": "C",
        "topic": "Family Plans",
        "difficulty": "easy",
        "rag_query": "FamilyShare Pro plan members shared data family",
    },
    {
        "id": "q003",
        "question": "Which plan offers a Static IP address — critical for hosting servers and VPNs?",
        "options": {
            "A": "FamilyShare Pro",
            "B": "StreamMax 5G",
            "C": "BusinessElite 5G",
            "D": "TravelGlobal SIM"
        },
        "correct": "C",
        "topic": "Business Plans",
        "difficulty": "medium",
        "rag_query": "static IP VPN enterprise business plan server hosting",
    },
    {
        "id": "q004",
        "question": "What maximum data speed does the BusinessElite 5G plan deliver on its priority 5G network?",
        "options": {
            "A": "Up to 150 Mbps",
            "B": "Up to 500 Mbps",
            "C": "Up to 1 Gbps",
            "D": "Up to 2 Gbps"
        },
        "correct": "D",
        "topic": "Network Speeds",
        "difficulty": "medium",
        "rag_query": "BusinessElite 5G speed priority network Gbps",
    },
    {
        "id": "q005",
        "question": "StudentFlex zero-rates (doesn't count toward data) which category of applications?",
        "options": {
            "A": "Gaming apps",
            "B": "Social media apps",
            "C": "Education apps",
            "D": "Entertainment apps"
        },
        "correct": "C",
        "topic": "Special Plans",
        "difficulty": "easy",
        "rag_query": "StudentFlex zero rating education apps Coursera Khan Academy",
    },
    {
        "id": "q006",
        "question": "Which two low-power wireless protocols does the IoTConnect M2M plan explicitly support?",
        "options": {
            "A": "3G and 4G LTE",
            "B": "NB-IoT and LTE-M",
            "C": "WiFi 6 and Bluetooth 5",
            "D": "LoRa and Zigbee"
        },
        "correct": "B",
        "topic": "IoT Protocols",
        "difficulty": "hard",
        "rag_query": "NB-IoT LTE-M narrowband IoT low power LPWAN protocol",
    },
    {
        "id": "q007",
        "question": "The TravelGlobal SIM plan provides international coverage in how many countries?",
        "options": {
            "A": "50+ countries",
            "B": "75+ countries",
            "C": "100+ countries",
            "D": "150+ countries"
        },
        "correct": "D",
        "topic": "International Plans",
        "difficulty": "easy",
        "rag_query": "TravelGlobal SIM international roaming countries coverage",
    },
    {
        "id": "q008",
        "question": "Which plan includes Microsoft 365 Basic as a bundled enterprise benefit?",
        "options": {
            "A": "StudentFlex",
            "B": "FamilyShare Pro",
            "C": "BusinessElite 5G",
            "D": "SmartDaily 5G"
        },
        "correct": "C",
        "topic": "Plan Benefits",
        "difficulty": "medium",
        "rag_query": "Microsoft 365 enterprise business plan included benefit",
    },
    {
        "id": "q009",
        "question": "What is the validity period of the StudentFlex prepaid plan?",
        "options": {
            "A": "28 days",
            "B": "30 days",
            "C": "56 days",
            "D": "84 days"
        },
        "correct": "C",
        "topic": "Plan Validity",
        "difficulty": "easy",
        "rag_query": "StudentFlex validity days prepaid student plan duration",
    },
    {
        "id": "q010",
        "question": "The StreamMax 5G plan is specifically optimized for which maximum video streaming resolution?",
        "options": {
            "A": "720p HD",
            "B": "1080p Full HD",
            "C": "4K UHD",
            "D": "8K"
        },
        "correct": "C",
        "topic": "Streaming Plans",
        "difficulty": "medium",
        "rag_query": "StreamMax 5G 4K streaming optimization OTT bundle",
    },
    {
        "id": "q011",
        "question": "What key latency advantage does 5G provide over 4G LTE for real-time applications?",
        "options": {
            "A": "5G has 100ms vs 4G 50ms latency",
            "B": "5G achieves <1ms vs 4G's typical 20-50ms",
            "C": "Both technologies have identical latency",
            "D": "4G LTE actually has lower latency than 5G"
        },
        "correct": "B",
        "topic": "5G Technology",
        "difficulty": "hard",
        "rag_query": "5G latency milliseconds vs 4G LTE real-time applications autonomous",
    },
    {
        "id": "q012",
        "question": "Which plan includes airport lounge access as a bundled travel benefit?",
        "options": {
            "A": "BusinessElite 5G",
            "B": "FamilyShare Pro",
            "C": "TravelGlobal SIM",
            "D": "StreamMax 5G"
        },
        "correct": "C",
        "topic": "Travel Benefits",
        "difficulty": "medium",
        "rag_query": "airport lounge access travel benefit international SIM",
    },
    {
        "id": "q013",
        "question": "What SLA uptime percentage does the BusinessElite 5G plan guarantee?",
        "options": {
            "A": "95% uptime",
            "B": "98% uptime",
            "C": "99.5% uptime",
            "D": "99.9% uptime"
        },
        "correct": "D",
        "topic": "Enterprise SLA",
        "difficulty": "medium",
        "rag_query": "BusinessElite SLA uptime guarantee enterprise 99.9",
    },
    {
        "id": "q014",
        "question": "NB-IoT operates in which type of spectrum, making it reliable and interference-free?",
        "options": {
            "A": "Unlicensed ISM band (2.4GHz)",
            "B": "Licensed cellular spectrum",
            "C": "Free-space optical spectrum",
            "D": "TVWS (TV White Space)"
        },
        "correct": "B",
        "topic": "IoT Protocols",
        "difficulty": "hard",
        "rag_query": "NB-IoT licensed spectrum cellular band reliable interference",
    },
    {
        "id": "q015",
        "question": "Which plan offers a 'Binge-On' mode where video streaming on partner apps doesn't count toward data?",
        "options": {
            "A": "SmartDaily 5G",
            "B": "FamilyShare Pro",
            "C": "StreamMax 5G",
            "D": "BasicConnect 4G"
        },
        "correct": "C",
        "topic": "Streaming Plans",
        "difficulty": "medium",
        "rag_query": "StreamMax Binge-On mode zero-rated video streaming partner apps",
    },
]

# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def get_questions(difficulty: str = "all", count: int = 8) -> list:
    """Return shuffled questions filtered by difficulty (without answers)"""
    pool = QUESTIONS
    if difficulty != "all":
        pool = [q for q in QUESTIONS if q["difficulty"] == difficulty]
    if not pool:
        pool = QUESTIONS

    selected = random.sample(pool, min(count, len(pool)))

    # Strip answer from client response
    return [
        {
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "difficulty": q["difficulty"],
            "topic": q["topic"],
        }
        for q in selected
    ]


def get_question_by_id(qid: str) -> Optional[dict]:
    """Return full question record (including correct answer) by ID"""
    return next((q for q in QUESTIONS if q["id"] == qid), None)


def validate_answer(qid: str, user_answer: str) -> dict:
    """
    Check answer and return result dict.
    Returns: {is_correct, correct_key, correct_text, rag_query, topic, difficulty}
    """
    q = get_question_by_id(qid)
    if not q:
        return {"error": f"Question {qid} not found"}

    answer = user_answer.upper().strip()
    is_correct = answer == q["correct"]

    return {
        "is_correct": is_correct,
        "correct_key": q["correct"],
        "correct_text": q["options"][q["correct"]],
        "user_key": answer,
        "user_text": q["options"].get(answer, "Unknown"),
        "rag_query": q["rag_query"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question_text": q["question"],
        "all_options": q["options"],
    }


def get_topics() -> list:
    """Return unique topic list"""
    return sorted(set(q["topic"] for q in QUESTIONS))


def get_stats() -> dict:
    """Return question bank statistics"""
    difficulties = {"easy": 0, "medium": 0, "hard": 0}
    topics = {}
    for q in QUESTIONS:
        difficulties[q["difficulty"]] = difficulties.get(q["difficulty"], 0) + 1
        topics[q["topic"]] = topics.get(q["topic"], 0) + 1
    return {
        "total_questions": len(QUESTIONS),
        "by_difficulty": difficulties,
        "by_topic": topics,
        "topics": get_topics(),
    }