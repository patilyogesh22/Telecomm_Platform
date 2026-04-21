"""
triage_agent.py — Telecomm Support Triage Agent
Problem Statement 3: Agentic AI

Problem Statement Description:
  "Create a production-grade reactive triage agent for Telecomm communications,
   utilizing Large Language Models to automate initial response workflows.
   The system performs:
     1. Real-time classification of incoming text → urgency and intent   ✅
     2. Named Entity Recognition (NER) to extract IDs, dates, amounts    ✅
     3. AI-generated contextually accurate draft responses               ✅
   ...to accelerate resolution times."

Tools: Python, LangChain/CrewAI, LLM API  (we use Gemini via llm_service)

This module:
  - extract_entities()         →  NER (phone, account ID, amounts, dates, operators, ticket refs)
  - triage_message()           →  Full pipeline: NER → classify → draft → create ticket
  - get_ticket() / get_all_tickets() / update_ticket_status()  →  Ticket CRUD
  - get_ticket_stats()         →  Dashboard stats

Works fully offline (rule-based fallback) when Gemini keys are exhausted.
"""

import re
import json
import uuid
import time
import threading
from datetime import datetime


# ─── Safe LLM imports ─────────────────────────────────────────
# We import internals from llm_service because triage_agent is a
# peer module (same package). If llm_service is unavailable the
# agent gracefully falls back to rule-based classification.
_HAS_LLM = False
try:
    from llm_service import _call, _hash, _cache_get, _cache_set, is_llm_available
    _HAS_LLM = True
except ImportError:
    def is_llm_available(): return False
    def _call(*a, **kw): return None
    def _hash(t): return ""
    def _cache_get(k): return None
    def _cache_set(k, v): pass


# ═════════════════════════════════════════════════════════════
#  CONSTANTS
# ═════════════════════════════════════════════════════════════

URGENCY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# Maps raw intent key → human-readable label
INTENT_LABELS = {
    "outage":       "Service Outage",
    "billing":      "Billing Issue",
    "plan_change":  "Plan Change Request",
    "recharge":     "Recharge Assistance",
    "roaming":      "Roaming Issue",
    "speed":        "Speed / Connectivity",
    "complaint":    "General Complaint",
    "cancellation": "Service Cancellation",
    "upgrade":      "Plan Upgrade",
    "porting":      "Number Porting",
    "device":       "Device Issue",
    "account":      "Account Management",
    "general":      "General Inquiry",
}

# Keywords for each urgency level (order = priority — CRITICAL checked first)
URGENCY_KEYWORDS = {
    "CRITICAL": [
        "emergency", "urgent", "no service", "completely down", "not working at all",
        "cannot call", "hospital", "life-threatening", "critical", "immediate",
        "ambulance", "fire", "police", "dead signal", "zero signal", "total outage",
        "cant call anyone", "completely lost network",
    ],
    "HIGH": [
        "outage", "down", "not working", "failed", "broken", "issue", "problem",
        "charged twice", "wrong charge", "fraud", "unauthorized", "data not working",
        "calls dropping", "network error", "sim not working", "roaming not working",
        "no internet", "no network", "service disruption", "recharge not done",
    ],
    "MEDIUM": [
        "slow", "intermittent", "sometimes", "occasionally", "billing question",
        "want to change", "upgrade", "downgrade", "plan details", "how to",
        "can you help", "need help", "port", "transfer", "inquiry about",
    ],
    "LOW": [
        "inquiry", "question", "info", "when", "what is", "could you",
        "i would like", "interested in", "tell me about", "general information",
    ],
}

# Keywords for intent classification
INTENT_KEYWORDS = {
    "outage":       ["outage", "no service", "network down", "no signal", "not working", "dead zone", "service down"],
    "billing":      ["bill", "charge", "invoice", "payment", "deducted", "amount", "refund", "overcharged", "duplicate charge", "double charged"],
    "plan_change":  ["change plan", "switch plan", "different plan", "upgrade plan", "downgrade", "new plan"],
    "recharge":     ["recharge", "top up", "balance", "validity", "expired", "renew", "recharge failed"],
    "roaming":      ["roaming", "international", "abroad", "overseas", "traveling", "outside india", "foreign country"],
    "speed":        ["slow", "speed", "mbps", "fast", "bandwidth", "data speed", "buffering", "slow internet", "low speed"],
    "complaint":    ["complaint", "not satisfied", "terrible", "worst", "disgusting", "rude", "bad service", "pathetic", "very bad"],
    "cancellation": ["cancel", "disconnect", "terminate", "close account", "stop service", "discontinue"],
    "upgrade":      ["upgrade", "better plan", "more data", "higher plan", "premium", "unlimited"],
    "porting":      ["port", "mnp", "number portability", "switch operator", "move to", "number transfer"],
    "account":      ["account", "login", "password", "profile", "registered", "sim swap", "number change"],
}


# ═════════════════════════════════════════════════════════════
#  IN-MEMORY TICKET STORE
#  (replace with DB in production — SQLAlchemy model recommended)
# ═════════════════════════════════════════════════════════════

_tickets:      dict            = {}
_tickets_lock: threading.Lock = threading.Lock()


def _save_ticket(ticket: dict):
    with _tickets_lock:
        _tickets[ticket["ticket_id"]] = ticket


def _get_ticket(ticket_id: str) -> dict | None:
    with _tickets_lock:
        return _tickets.get(ticket_id)


def _all_tickets() -> list:
    with _tickets_lock:
        return sorted(_tickets.values(), key=lambda t: t["created_at"], reverse=True)


# ═════════════════════════════════════════════════════════════
#  NAMED ENTITY RECOGNITION  (NER)
#  Problem Statement requirement:
#    "applies Named Entity Recognition (NER) to extract critical
#     data points such as IDs and dates"
# ═════════════════════════════════════════════════════════════

def extract_entities(text: str) -> dict:
    """
    Regex-based NER — always runs, no API required.

    Extracts:
      phone_numbers  — Indian 10-digit (with or without +91)
      account_ids    — CA/ACC/CUST/ID prefix patterns
      ticket_refs    — TKT/TICKET/REF/TXN/SR prefix patterns
      amounts        — ₹, Rs, INR monetary values
      dates          — DD/MM/YYYY, named months, relative dates
      operators      — Jio, Airtel, Vi, BSNL name mentions
      plan_names     — plan/pack/recharge mention patterns
    """
    entities: dict = {
        "phone_numbers": [],
        "account_ids":   [],
        "ticket_refs":   [],
        "amounts":       [],
        "dates":         [],
        "operators":     [],
        "plan_names":    [],
    }

    # ── Phone numbers — Indian 10-digit, optional +91 prefix ──
    phones = re.findall(r'(?:\+91[\s\-]?)?[6-9]\d{9}', text)
    entities["phone_numbers"] = list(set(phones))

    # ── Account / Customer IDs ────────────────────────────────
    accounts = re.findall(r'\b(?:CA|ACC|CUST|ID)[\s\-]?[A-Z0-9]{4,12}\b', text.upper())
    entities["account_ids"] = list(set(accounts))

    # ── Ticket / Transaction references ───────────────────────
    refs = re.findall(r'\b(?:TKT|TICKET|REF|TXN|SR)[A-Z0-9\-]{4,14}\b', text.upper())
    entities["ticket_refs"] = list(set(refs))

    # ── Monetary amounts — ₹, Rs, INR ─────────────────────────
    amounts_raw = re.findall(r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
    entities["amounts"] = [a.replace(",", "") for a in amounts_raw]

    # ── Dates ─────────────────────────────────────────────────
    date_patterns = [
        r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
        r'\b(?:yesterday|today|last\s+(?:week|month|night|Tuesday|Monday|Wednesday|Thursday|Friday|Saturday|Sunday))\b',
        r'\bsince\s+(?:yesterday|last\s+\w+|\d+\s+(?:days?|hours?|weeks?))\b',
    ]
    for pat in date_patterns:
        entities["dates"].extend(re.findall(pat, text, re.IGNORECASE))
    entities["dates"] = list(set(entities["dates"]))

    # ── Operator names ────────────────────────────────────────
    text_lower = text.lower()
    op_map = {
        "Jio":    ["jio", "reliance jio"],
        "Airtel": ["airtel", "bharti airtel"],
        "Vi":     [" vi ", "vodafone", " idea ", "vodafone-idea", "vi's", "vi."],
        "BSNL":   ["bsnl", "bharat sanchar", "mtnl"],
    }
    for op_name, keywords in op_map.items():
        if any(kw in text_lower for kw in keywords):
            entities["operators"].append(op_name)
    entities["operators"] = list(set(entities["operators"]))

    # ── Plan / pack name patterns ─────────────────────────────
    plan_patterns = [
        r'\b(?:jio|airtel|vi|bsnl)\s+(?:prepaid|postpaid|plan|pack|recharge|sim)\b',
        r'\b(?:₹|Rs\.?)\s*\d+\s*(?:plan|pack|recharge)\b',
        r'\b\d+\s*(?:GB|MB)\s*(?:plan|pack|data)?\b',
        r'\b(?:unlimited|basic|standard|premium|annual|yearly|monthly)\s+(?:plan|pack|data)?\b',
    ]
    for pat in plan_patterns:
        found = re.findall(pat, text, re.IGNORECASE)
        entities["plan_names"].extend([f.strip() for f in found])
    entities["plan_names"] = list(set(entities["plan_names"]))

    return entities


# ═════════════════════════════════════════════════════════════
#  LOCAL CLASSIFICATION  (fast, no API required)
# ═════════════════════════════════════════════════════════════

def _classify_urgency_local(text: str) -> str:
    """
    Keyword-based urgency classification.
    Checks CRITICAL first (highest priority) → LOW last.
    Returns 'MEDIUM' if no keywords match.
    """
    text_lower = text.lower()
    for level in URGENCY_LEVELS:          # CRITICAL, HIGH, MEDIUM, LOW
        if any(kw in text_lower for kw in URGENCY_KEYWORDS[level]):
            return level
    return "MEDIUM"


def _classify_intent_local(text: str) -> str:
    """
    Keyword-based intent classification.
    Counts keyword hits per intent; returns the intent with highest count.
    Returns 'general' if no keywords match.
    """
    text_lower = text.lower()
    scores: dict = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw in text_lower)
    best_intent = max(scores, key=scores.get)
    return best_intent if scores[best_intent] > 0 else "general"


# ═════════════════════════════════════════════════════════════
#  AI CLASSIFICATION + DRAFT GENERATION  (Gemini)
#  Problem Statement requirement:
#    "generates contextually accurate draft responses using an LLM API"
# ═════════════════════════════════════════════════════════════

_TRIAGE_PROMPT = """You are a production telecom support triage AI agent.
Analyze this customer support message and return ONLY valid JSON with no markdown, no code fences, no extra text.

Customer message: "{message}"

Extracted entities (for context): {entities}

Return EXACTLY this JSON structure:
{{
  "urgency": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "urgency_reason": "one clear sentence explaining urgency level",
  "intent": "outage" | "billing" | "plan_change" | "recharge" | "roaming" | "speed" | "complaint" | "cancellation" | "upgrade" | "porting" | "account" | "general",
  "intent_label": "Human readable label e.g. Billing Issue",
  "confidence": 0.0 to 1.0,
  "sentiment": "frustrated" | "angry" | "neutral" | "satisfied" | "confused",
  "key_issues": ["specific issue 1", "specific issue 2"],
  "draft_response": "Professional empathetic reply (max 60 words). Start with 'Dear Customer'. Sign as 'TeleBot Support Team'. Acknowledge the issue, ask for account details, promise follow-up.",
  "resolution_steps": ["Specific step 1", "Specific step 2", "Specific step 3", "Specific step 4"],
  "handle_time": "2-5 minutes" | "5-15 minutes" | "15-30 minutes" | "30+ minutes",
  "escalate": true | false,
  "escalation_reason": "reason if escalate true, else empty string"
}}

Urgency rules:
- CRITICAL: complete outage, emergency, hospital/fire/police context, total network failure
- HIGH: partial outage, billing fraud, duplicate charge, roaming failure, data not working
- MEDIUM: slow speeds, plan query, account question, general complaint
- LOW: general information request, plan comparison, non-urgent inquiry

Always provide specific, actionable resolution_steps tailored to the intent."""


def analyze_with_ai(message: str, entities: dict) -> dict | None:
    """
    Use Gemini to:
    1. Classify urgency (CRITICAL/HIGH/MEDIUM/LOW)
    2. Detect intent (outage/billing/roaming/etc.)
    3. Generate a professional draft response
    4. Suggest ordered resolution steps

    Returns None if AI is unavailable — caller uses rule-based fallback.
    Retries on 503 (Gemini overloaded), gives up on other errors.
    """
    if not _HAS_LLM:
        return None

    try:
        if not is_llm_available():
            return None
    except Exception:
        return None

    # Format entities context (skip empty lists)
    entity_ctx = json.dumps(
        {k: v for k, v in entities.items() if v},
        ensure_ascii=False
    )

    prompt = _TRIAGE_PROMPT.format(
        message=message,
        entities=entity_ctx,
    )

    # Cache — avoid re-classifying identical messages
    cache_key = _hash(f"triage_{message[:200]}")
    cached    = _cache_get(cache_key)
    if cached:
        return cached

    raw       = None
    last_err  = None

    for attempt in range(3):
        try:
            raw = _call(
                [{"role": "user", "parts": [{"text": prompt}]}],
                max_tokens=1500
            )
            break
        except RuntimeError as e:
            last_err = e
            if "503" in str(e) and attempt < 2:
                wait = (attempt + 1) * 5
                print(f"[TRIAGE] Gemini 503 — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[TRIAGE] AI call failed: {e}")
                return None

    if not raw:
        return None

    # Strip markdown fences if model adds them
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Repair truncated JSON — if response was cut off, try to close brace
    if not raw.endswith("}"):
        last_good = max(
            raw.rfind(',"escalate"'),
            raw.rfind(',"confidence"'),
            raw.rfind(',"intent"'),
        )
        if last_good > 0:
            raw = raw[:last_good] + "}"
            print("[TRIAGE] ⚠️  Repaired truncated JSON")
        else:
            print("[TRIAGE] JSON too truncated to repair — using fallback")
            return None

    try:
        result = json.loads(raw)
        _cache_set(cache_key, result)
        return result
    except json.JSONDecodeError as e:
        print(f"[TRIAGE] JSON parse error: {e}")
        return None


# ═════════════════════════════════════════════════════════════
#  RULE-BASED FALLBACK RESPONSE
# ═════════════════════════════════════════════════════════════

def _build_fallback_response(
    message:  str,
    urgency:  str,
    intent:   str,
    entities: dict,
) -> dict:
    """
    Builds a complete triage result using rules + templates.
    Used when Gemini is offline or all keys exhausted.
    Still satisfies Problem Statement 3 — classification and NER
    run entirely without an API.
    """
    intent_label = INTENT_LABELS.get(intent, "General Inquiry")

    # Greeting based on urgency
    greetings = {
        "CRITICAL": "We sincerely apologize for the critical service disruption you are experiencing.",
        "HIGH":     "Thank you for bringing this urgent issue to our attention.",
        "MEDIUM":   "Thank you for contacting TeleBot Support.",
        "LOW":      "Thank you for reaching out to us.",
    }

    # Acknowledgement based on intent
    issue_acks = {
        "outage":       "We understand you are experiencing a service outage — this is our highest priority.",
        "billing":      "We understand you have a billing concern and we take this very seriously.",
        "plan_change":  "We'd be happy to help you find the right plan for your needs.",
        "roaming":      "We understand you're experiencing roaming issues and will resolve this quickly.",
        "speed":        "We understand you're facing slow network speeds and will investigate immediately.",
        "complaint":    "We sincerely apologize for the experience you've had and want to make this right.",
        "recharge":     "We're here to help you with your recharge or balance query right away.",
        "cancellation": "We've received your request and want to address your concerns before proceeding.",
        "upgrade":      "We'll help you find the best upgraded plan for your usage needs.",
        "porting":      "We'll guide you through the number porting process step by step.",
        "account":      "We'll help you resolve your account issue securely and quickly.",
        "general":      "We've received your query and our support team is ready to assist.",
    }

    draft = (
        f"Dear Customer,\n\n"
        f"{greetings[urgency]} {issue_acks.get(intent, issue_acks['general'])} "
        f"To serve you better, could you please share your registered mobile number and account ID? "
        f"A specialist will contact you shortly.\n\n"
        f"Warm regards,\nTeleBot Support Team"
    )

    # Resolution steps per intent
    steps_map = {
        "outage":       ["Verify customer account and network status", "Check outage map for customer's area", "Escalate to NOC if area-wide outage confirmed", "Provide ETR (Estimated Time to Restore)"],
        "billing":      ["Pull up account billing history for last 3 cycles", "Identify the disputed charge or duplicate transaction", "Verify against payment gateway records", "Process refund within 5-7 business days if valid"],
        "plan_change":  ["Understand customer's data/OTT/budget requirements", "Present best-fit plans from current portfolio", "Confirm new plan details and effective date", "Process plan change and send confirmation SMS"],
        "roaming":      ["Verify international roaming activation status", "Check partner network coverage in customer's location", "Enable roaming remotely if not activated", "Explain roaming charges and data caps"],
        "speed":        ["Run automated network diagnostics for customer's number", "Check tower load and congestion in area", "Remotely reset network profile if needed", "Escalate to field engineering if issue persists"],
        "complaint":    ["Acknowledge complaint and log in CRM", "Review full interaction history", "Escalate to senior support if needed", "Follow up within 24 hours with resolution"],
        "recharge":     ["Check current balance, validity, and last transaction", "Verify if recharge amount was debited from bank", "Process recharge manually if deducted but not credited", "Send confirmation SMS after successful credit"],
        "cancellation": ["Understand reason for cancellation", "Present retention offers and plan alternatives", "If proceeding, initiate disconnection request", "Confirm last bill date and port-out process if needed"],
        "upgrade":      ["Identify customer's current plan and usage pattern", "Recommend best upgrade options within budget", "Process upgrade and confirm new benefits", "Follow up to ensure activation"],
        "porting":      ["Explain MNP process and timeline (7 business days)", "Verify customer eligibility for porting", "Generate UPC code and send to customer", "Track porting status and confirm completion"],
        "account":      ["Verify customer identity with OTP", "Access account details securely", "Resolve account issue (reset/update/unlock)", "Confirm changes via registered mobile"],
        "general":      ["Understand the complete customer query", "Provide accurate and complete information", "Offer related helpful information proactively", "Confirm customer is fully satisfied before closing"],
    }

    resolution_steps  = steps_map.get(intent, steps_map["general"])
    escalate          = urgency in ("CRITICAL", "HIGH") or intent in ("outage", "cancellation")
    handle_time_map   = {
        "CRITICAL": "2-5 minutes",
        "HIGH":     "5-15 minutes",
        "MEDIUM":   "15-30 minutes",
        "LOW":      "30+ minutes",
    }

    return {
        "urgency":           urgency,
        "urgency_reason":    f"Detected {urgency.lower()} priority signal in customer message",
        "intent":            intent,
        "intent_label":      intent_label,
        "confidence":        0.75,
        "key_issues":        [intent_label],
        "sentiment":         "frustrated" if urgency in ("CRITICAL", "HIGH") else "neutral",
        "draft_response":    draft,
        "resolution_steps":  resolution_steps,
        "handle_time":       handle_time_map[urgency],
        "escalate":          escalate,
        "escalation_reason": "High-priority issue requiring immediate specialist" if escalate else "",
        "ai_powered":        False,
    }


# ═════════════════════════════════════════════════════════════
#  MAIN TRIAGE PIPELINE
#  Problem Statement 3 — Full Agentic Workflow
# ═════════════════════════════════════════════════════════════

def triage_message(
    message:     str,
    channel:     str = "chat",
    customer_id: str = None,
) -> dict:
    """
    Full reactive triage pipeline (Problem Statement 3):

    Step 1 — NER (Named Entity Recognition)
              Extract phone numbers, account IDs, amounts, dates,
              operators, plan names, ticket references.
              → Runs with zero API calls (regex-based).

    Step 2 — Urgency Classification  (CRITICAL / HIGH / MEDIUM / LOW)
              Intent Detection        (outage, billing, roaming, etc.)
              → Tries Gemini first, falls back to keyword rules.

    Step 3 — Draft Response Generation
              → Gemini generates professional, empathetic response.
              → Falls back to template-based draft if AI offline.

    Step 4 — Ticket Creation
              Assigns TKT-YYYYMMDD-XXXXXX ID, stores in memory.

    Step 5 — Return full triage report to API caller.
    """
    if not message or len(message.strip()) < 3:
        return {"error": "Message too short to analyze"}

    start_time = time.time()

    # ── Step 1: NER ───────────────────────────────────────────
    entities = extract_entities(message)

    # ── Steps 2 & 3: AI classification + draft ───────────────
    ai_result  = analyze_with_ai(message, entities)
    ai_powered = ai_result is not None

    if ai_result:
        result             = ai_result
        result["ai_powered"] = True
    else:
        # Fully offline path
        urgency = _classify_urgency_local(message)
        intent  = _classify_intent_local(message)
        result  = _build_fallback_response(message, urgency, intent, entities)

    # ── Step 4: Create ticket ─────────────────────────────────
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    ticket = {
        "ticket_id":         ticket_id,
        "customer_id":       customer_id or "ANONYMOUS",
        "channel":           channel,
        "original_message":  message,
        # Classification
        "urgency":           result.get("urgency",      "MEDIUM"),
        "urgency_reason":    result.get("urgency_reason",""),
        "intent":            result.get("intent",       "general"),
        "intent_label":      result.get("intent_label", "General Inquiry"),
        "sentiment":         result.get("sentiment",    "neutral"),
        "confidence":        result.get("confidence",   0.75),
        "key_issues":        result.get("key_issues",   []),
        # NER output
        "entities":          entities,
        # Response
        "draft_response":    result.get("draft_response",   ""),
        "resolution_steps":  result.get("resolution_steps", []),
        "handle_time":       result.get("handle_time",      "15-30 minutes"),
        "escalate":          result.get("escalate",         False),
        "escalation_reason": result.get("escalation_reason",""),
        # Metadata
        "ai_powered":        ai_powered,
        "status":            "OPEN",
        "created_at":        datetime.utcnow().isoformat(),
        "updated_at":        datetime.utcnow().isoformat(),
        "processing_ms":     round((time.time() - start_time) * 1000),
    }

    _save_ticket(ticket)
    return ticket


# ═════════════════════════════════════════════════════════════
#  TICKET MANAGEMENT
# ═════════════════════════════════════════════════════════════

def get_ticket(ticket_id: str) -> dict | None:
    """Retrieve a single ticket by ID."""
    return _get_ticket(ticket_id)


def get_all_tickets(limit: int = 20) -> list:
    """Return all tickets sorted newest-first."""
    return _all_tickets()[:limit]


def update_ticket_status(
    ticket_id: str,
    status:    str,
    notes:     str = "",
) -> dict | None:
    """
    Update ticket status along the lifecycle:
    OPEN → IN_PROGRESS → RESOLVED → CLOSED
    Optionally attach agent notes.
    """
    ticket = _get_ticket(ticket_id)
    if not ticket:
        return None
    ticket["status"]     = status
    ticket["updated_at"] = datetime.utcnow().isoformat()
    if notes:
        ticket["agent_notes"] = notes
    _save_ticket(ticket)
    return ticket


def get_ticket_stats() -> dict:
    """
    Aggregate statistics for the triage dashboard:
    - Total tickets
    - Counts by urgency, intent, status
    - Average AI confidence
    - Escalation count
    - AI-powered vs rule-based count
    """
    tickets = _all_tickets()
    if not tickets:
        return {
            "total": 0, "by_urgency": {},
            "by_intent": {}, "by_status": {},
            "avg_confidence": 0, "escalations": 0, "ai_powered": 0,
        }

    by_urgency:  dict = {}
    by_intent:   dict = {}
    by_status:   dict = {}
    confidences: list = []

    for t in tickets:
        u = t.get("urgency", "MEDIUM")
        i = t.get("intent",  "general")
        s = t.get("status",  "OPEN")
        by_urgency[u] = by_urgency.get(u, 0) + 1
        by_intent[i]  = by_intent.get(i, 0)  + 1
        by_status[s]  = by_status.get(s, 0)  + 1
        confidences.append(t.get("confidence", 0))

    return {
        "total":          len(tickets),
        "by_urgency":     by_urgency,
        "by_intent":      by_intent,
        "by_status":      by_status,
        "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
        "escalations":    sum(1 for t in tickets if t.get("escalate")),
        "ai_powered":     sum(1 for t in tickets if t.get("ai_powered")),
    }