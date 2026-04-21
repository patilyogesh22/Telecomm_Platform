"""
app.py  ─  TeleBot Telecomm Intelligence Platform  v3.0.0

Problem Statement 1 : IaC / Docker deployment  (Dockerfile + CI/CD use this)
Problem Statement 2 : Telecomm Quiz / Tutor Bot (AI generation, RAG, Gemini)
Problem Statement 3 : Support Triage Agent      (NER, classification, drafts)
"""

from flask import Flask, jsonify, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
import os, random, time

load_dotenv()

# ─── Flask app ────────────────────────────────────────────────
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, supports_credentials=True)
app.config["SECRET_KEY"]                     = os.getenv("SECRET_KEY", "telecom-secret-2024")
app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///telecom.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"]        = "Lax"
app.config["SESSION_COOKIE_SECURE"]          = False   # set True in prod with HTTPS

db = SQLAlchemy(app)

# ─── Internal module imports ──────────────────────────────────
from quiz_engine import (
    get_questions, validate_answer, validate_session_answer,
    store_session, generate_session_id, get_stats as quiz_stats,
)
from llm_service import (
    generate_explanation, generate_quiz_questions,
    tutor_chat, is_llm_available, get_key_status,
)
from vector_db import init_vector_db, retrieve_all, get_stats as db_stats
from operator_data import (
    detect_operator, get_operator_plans, get_all_operators,
    get_plan_by_id, get_ai_plans_context, format_plans_for_ai,
    OPERATOR_PLANS, DTH_OPERATORS, DTH_PLANS,
    BROADBAND_OPERATORS, BROADBAND_PLANS,
    ELECTRICITY_BOARDS, GAS_PROVIDERS, WATER_BOARDS, LANDLINE_PROVIDERS,
)
from triage_agent import (
    triage_message, get_ticket, get_all_tickets,
    update_ticket_status, get_ticket_stats, extract_entities,
)

# ─── Bootstrap Vector DB ──────────────────────────────────────
with app.app_context():
    try:
        init_vector_db()
        print("[APP] Vector DB initialized")
    except Exception as e:
        print(f"[APP] Vector DB warning: {e}")


# ═════════════════════════════════════════════════════════════
#  DATABASE MODELS
# ═════════════════════════════════════════════════════════════

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer,     primary_key=True)
    full_name     = db.Column(db.String(100), nullable=False)
    username      = db.Column(db.String(50),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone         = db.Column(db.String(20),  default="")
    plan_id       = db.Column(db.Integer,     default=1)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    is_active     = db.Column(db.Boolean,     default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id":           self.id,
            "full_name":    self.full_name,
            "username":     self.username,
            "email":        self.email,
            "phone":        self.phone,
            "plan_id":      self.plan_id,
            "avatar":       self.full_name[:2].upper(),
            "member_since": self.created_at.strftime("%Y"),
            "created_at":   self.created_at.isoformat(),
            "status":       "active" if self.is_active else "inactive",
        }


class QuizScore(db.Model):
    __tablename__ = "quiz_scores"
    id         = db.Column(db.Integer,    primary_key=True)
    user_id    = db.Column(db.Integer,    db.ForeignKey("users.id"), nullable=False)
    score      = db.Column(db.Integer,    default=0)
    total      = db.Column(db.Integer,    default=0)
    difficulty = db.Column(db.String(20), default="all")
    created_at = db.Column(db.DateTime,   default=datetime.utcnow)


with app.app_context():
    db.create_all()
    print("[DB] Tables ready")


# ═════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ═════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required", "redirect": "/"}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if "user_id" not in session:
        return None
    return db.session.get(User, session["user_id"])


# ═════════════════════════════════════════════════════════════
#  STATIC DATA
# ═════════════════════════════════════════════════════════════

PLANS = [
    {
        "id": 1, "name": "Basic Plan", "price": 299,
        "calls": 500, "sms": 100, "data": 5,
        "features": ["500 min calls", "100 SMS", "5 GB data", "Basic support"],
        "description": "Perfect for light users",
    },
    {
        "id": 2, "name": "Standard Plan", "price": 599,
        "calls": 1500, "sms": 300, "data": 15,
        "features": ["1500 min calls", "300 SMS", "15 GB data", "Priority support"],
        "description": "Great for regular users", "popular": True,
    },
    {
        "id": 3, "name": "Premium Plan", "price": 999,
        "calls": 3000, "sms": 500, "data": 30,
        "features": ["3000 min calls", "500 SMS", "30 GB data", "VIP support"],
        "description": "Best for heavy users",
    },
]

RECENT_CALLS = [
    {"id": 1, "number": "+91 9876543210", "type": "incoming", "duration": 435, "date": "2024-02-20 14:30", "cost": 0,     "name": "Mom"},
    {"id": 2, "number": "+91 9123456789", "type": "outgoing", "duration": 240, "date": "2024-02-20 13:15", "cost": 5.00,  "name": "Friend"},
    {"id": 3, "number": "+91 9999999999", "type": "incoming", "duration": 180, "date": "2024-02-20 11:45", "cost": 0,     "name": "Office"},
    {"id": 4, "number": "+91 8765432109", "type": "outgoing", "duration": 600, "date": "2024-02-19 20:30", "cost": 10.00, "name": "Support"},
    {"id": 5, "number": "+91 9111111111", "type": "incoming", "duration": 120, "date": "2024-02-19 15:20", "cost": 0,     "name": "Unknown"},
]


# ═════════════════════════════════════════════════════════════
#  FRONTEND SERVING
# ═════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


@app.route("/<path:path>")
def serve_frontend(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory("../frontend", "index.html")


# ═════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def register():
    data      = request.get_json(force=True)
    full_name = data.get("full_name", "").strip()
    username  = data.get("username",  "").strip().lower()
    email     = data.get("email",     "").strip().lower()
    password  = data.get("password",  "").strip()

    if not all([full_name, username, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(full_name=full_name, username=username, email=email, plan_id=1)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"success": True, "message": "Account created!", "user": user.to_dict()}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    login_id = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not login_id or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user.id
    session.permanent  = True
    return jsonify({"success": True, "message": "Login successful", "user": user.to_dict()})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"})


@app.route("/api/auth/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user.to_dict())


# ═════════════════════════════════════════════════════════════
#  USER PROFILE
# ═════════════════════════════════════════════════════════════

@app.route("/api/user/profile", methods=["GET", "POST"])
@login_required
def user_profile():
    user = get_current_user()
    if request.method == "GET":
        return jsonify(user.to_dict())
    data = request.get_json(force=True)
    if data.get("full_name"): user.full_name = data["full_name"].strip()
    if data.get("email"):     user.email     = data["email"].strip().lower()
    if data.get("phone"):     user.phone     = data["phone"].strip()
    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated", "user": user.to_dict()})


# ═════════════════════════════════════════════════════════════
#  PLATFORM PLANS & BILLING
# ═════════════════════════════════════════════════════════════

@app.route("/api/plans")
def get_plans():
    return jsonify(PLANS)


@app.route("/api/plan")
@login_required
def get_my_plan():
    user = get_current_user()
    plan = next((p for p in PLANS if p["id"] == user.plan_id), PLANS[0])
    return jsonify({
        **plan,
        "status":       "active",
        "renewal_date": (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d"),
        "auto_renewal": True,
    })


@app.route("/api/plan/change", methods=["POST"])
@login_required
def change_plan():
    user    = get_current_user()
    data    = request.get_json(force=True)
    plan_id = int(data.get("plan_id", 0))
    plan    = next((p for p in PLANS if p["id"] == plan_id), None)
    if not plan:
        return jsonify({"error": "Invalid plan ID"}), 400
    user.plan_id = plan_id
    db.session.commit()
    return jsonify({"success": True, "message": f"Switched to {plan['name']}", "plan": plan})


@app.route("/api/bill")
@login_required
def get_bill():
    user = get_current_user()
    plan = next((p for p in PLANS if p["id"] == user.plan_id), PLANS[0])
    tax  = round(plan["price"] * 0.18, 2)
    return jsonify({
        "id":          1,
        "amount":      round(plan["price"] + tax, 2),
        "period":      datetime.now().strftime("%B %Y"),
        "status":      "pending",
        "due_date":    (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "breakdown":   {"base": plan["price"], "tax": tax, "extra": 0, "discount": 0},
        "issued_date": datetime.now().strftime("%Y-%m-01"),
    })


@app.route("/api/bill/pay", methods=["POST"])
@login_required
def pay_bill():
    return jsonify({
        "success":        True,
        "transaction_id": f"TXN{random.randint(100000, 999999)}",
        "message":        "Bill paid successfully",
    })


@app.route("/api/usage")
@login_required
def get_usage():
    user = get_current_user()
    plan = next((p for p in PLANS if p["id"] == user.plan_id), PLANS[0])
    return jsonify({
        "calls_used": int(plan["calls"] * 0.5), "calls_limit": plan["calls"], "calls_percent": 50,
        "sms_used":   int(plan["sms"]   * 0.5), "sms_limit":   plan["sms"],   "sms_percent":   50,
        "data_used":  round(plan["data"] * 0.5, 1), "data_limit": plan["data"], "data_percent": 50,
        "reset_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
    })


@app.route("/api/calls")
@login_required
def get_calls():
    limit = request.args.get("limit", 10, type=int)
    return jsonify(RECENT_CALLS[:limit])


@app.route("/api/notifications")
@login_required
def get_notifications():
    return jsonify([
        {"id": 1, "type": "alert",   "message": "You have used 50% of your data",         "date": "2024-02-20", "read": False},
        {"id": 2, "type": "offer",   "message": "Special offer: 20% off on Premium Plan", "date": "2024-02-19", "read": False},
        {"id": 3, "type": "payment", "message": "Bill due in 5 days",                      "date": "2024-02-18", "read": True},
    ])


# ═════════════════════════════════════════════════════════════
#  QUIZ / TUTOR BOT  — Problem Statement 2
# ═════════════════════════════════════════════════════════════

@app.route("/api/quiz/questions")
@login_required
def quiz_questions():
    """
    Generate quiz questions.
    1. Try Gemini AI generation first (fresh questions every session)
    2. Store correct answers server-side in session store
    3. Send questions WITHOUT correct answers to client
    4. Fall back to static bank if Gemini unavailable
    """
    difficulty = request.args.get("difficulty", "all")
    count      = request.args.get("count", 8, type=int)
    session_id = None
    questions  = []

    if is_llm_available():
        try:
            rag_ctx   = retrieve_all(f"telecom plans pricing features {difficulty} protocols")
            raw_qs    = generate_quiz_questions(difficulty=difficulty, count=count, rag_context=rag_ctx)
            if raw_qs:
                session_id = generate_session_id()
                store_session(session_id, raw_qs)
                # Strip correct answers before sending to client
                questions = [
                    {
                        "id":         q["id"],
                        "question":   q["question"],
                        "options":    q["options"],
                        "difficulty": q["difficulty"],
                        "topic":      q["topic"],
                    }
                    for q in raw_qs
                ]
                print(f"[Quiz] ✅ AI generated {len(questions)} Qs | session={session_id[:8]}…")
        except Exception as e:
            print(f"[Quiz] ⚠️ AI error: {e}")

    if not questions:
        print("[Quiz] ⚠️ Using static fallback bank")
        questions = get_questions(difficulty, count)

    return jsonify({
        "questions":    questions,
        "total":        len(questions),
        "session_id":   session_id,
        "ai_generated": session_id is not None,
    })


@app.route("/api/quiz/submit", methods=["POST"])
@login_required
def quiz_submit():
    """
    Validate answer, retrieve RAG context, generate AI explanation.
    Correct answer is looked up server-side — never exposed to client.
    """
    data       = request.get_json(force=True)
    qid        = data.get("question_id", "").strip()
    user_ans   = data.get("answer", "").strip().upper()
    session_id = data.get("session_id", "").strip()

    if not qid or not user_ans:
        return jsonify({"error": "question_id and answer are required"}), 400

    # Validate — session (AI) or static bank
    if session_id:
        result = validate_session_answer(session_id, qid, user_ans)
    else:
        result = validate_answer(qid, user_ans)

    if "error" in result:
        return jsonify(result), 400

    # RAG retrieval for explanation context
    rag_context = retrieve_all(result["rag_query"])

    # AI-generated rich explanation
    explanation = generate_explanation(
        question_text       = result["question_text"],
        options             = result["all_options"],
        user_key            = result["user_key"],
        correct_key         = result["correct_key"],
        correct_text        = result["correct_text"],
        user_text           = result["user_text"],
        is_correct          = result["is_correct"],
        topic               = result["topic"],
        difficulty          = result["difficulty"],
        rag_context         = rag_context,
        explanation_context = result.get("explanation_context", ""),
    )

    return jsonify({
        "is_correct":   result["is_correct"],
        "correct_key":  result["correct_key"],
        "correct_text": result["correct_text"],
        "user_key":     result["user_key"],
        "explanation":  explanation,
        "topic":        result["topic"],
        "difficulty":   result["difficulty"],
    })


@app.route("/api/quiz/score", methods=["POST"])
@login_required
def save_quiz_score():
    user = get_current_user()
    data = request.get_json(force=True)
    qs   = QuizScore(
        user_id    = user.id,
        score      = data.get("score", 0),
        total      = data.get("total", 0),
        difficulty = data.get("difficulty", "all"),
    )
    db.session.add(qs)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/quiz/history")
@login_required
def quiz_history():
    user   = get_current_user()
    scores = (QuizScore.query
              .filter_by(user_id=user.id)
              .order_by(QuizScore.created_at.desc())
              .limit(10).all())
    return jsonify([
        {
            "score":      s.score,
            "total":      s.total,
            "difficulty": s.difficulty,
            "date":       s.created_at.isoformat(),
        }
        for s in scores
    ])


@app.route("/api/quiz/chat", methods=["POST"])
@login_required
def quiz_chat():
    """
    AI Tutor chat endpoint.
    Detects operator keywords and injects full live plan data into Gemini context.
    Adds RAG retrieval on top.
    """
    data    = request.get_json(force=True)
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message is empty"}), 400

    msg_lower    = message.lower()
    plan_context = ""

    # Smart operator detection: inject operator's full plan list
    operator_map = {
        "jio": "Jio", "reliance": "Jio",
        "airtel": "Airtel", "bharti": "Airtel",
        "vi": "Vi", "vodafone": "Vi", "idea": "Vi",
        "bsnl": "BSNL", "bharat sanchar": "BSNL",
    }
    for keyword, op_name in operator_map.items():
        if keyword in msg_lower:
            plan_context = format_plans_for_ai(op_name)
            break

    # Generic plan query: inject all operators
    if not plan_context and any(
        w in msg_lower for w in [
            "plan", "plans", "recharge", "pack", "offer",
            "data", "prepaid", "postpaid", "best plan",
        ]
    ):
        plan_context = get_ai_plans_context()

    rag_context  = retrieve_all(message)
    full_context = f"{rag_context}\n\n{plan_context}" if plan_context else rag_context

    reply = tutor_chat(message, history, full_context)
    return jsonify({"reply": reply})


# ═════════════════════════════════════════════════════════════
#  PAYMENT DASHBOARD
# ═════════════════════════════════════════════════════════════

@app.route("/api/payment/operators")
@login_required
def payment_operators():
    """Return operators list for the selected service type."""
    service = request.args.get("service", "mobile")
    service_map = {
        "mobile":      get_all_operators(),
        "postpaid":    get_all_operators(),
        "dth":         DTH_OPERATORS,
        "broadband":   BROADBAND_OPERATORS,
        "electricity": ELECTRICITY_BOARDS,
        "gas":         GAS_PROVIDERS,
        "water":       WATER_BOARDS,
        "landline":    LANDLINE_PROVIDERS,
    }
    if service not in service_map:
        return jsonify({"error": f"Unknown service: {service}"}), 400
    return jsonify({"operators": service_map[service], "service": service})


@app.route("/api/payment/plans")
@login_required
def payment_plans():
    """Return plans for a given operator + service type."""
    operator  = request.args.get("operator", "")
    plan_type = request.args.get("type", "prepaid")
    service   = request.args.get("service", "mobile")

    if service in ("mobile", "postpaid"):
        plans   = get_operator_plans(operator, plan_type)
        op_info = OPERATOR_PLANS.get(operator, {})
        return jsonify({
            "plans":    plans,
            "operator": operator,
            "type":     plan_type,
            "logo":     op_info.get("logo", "📱"),
            "color":    op_info.get("color", "#6366f1"),
        })

    if service == "dth":
        return jsonify({"plans": DTH_PLANS.get(operator, []), "operator": operator})

    if service == "broadband":
        return jsonify({"plans": BROADBAND_PLANS.get(operator, []), "operator": operator})

    return jsonify({"plans": [], "operator": operator})


@app.route("/api/payment/detect", methods=["POST"])
@login_required
def detect_number():
    """Detect operator from mobile number prefix (4-digit → 2-digit fallback)."""
    data   = request.get_json(force=True)
    mobile = data.get("mobile", "").strip()

    if not mobile or len("".join(filter(str.isdigit, mobile))) < 10:
        return jsonify({"error": "Enter a valid 10-digit mobile number"}), 400

    operator = detect_operator(mobile)
    if operator == "Unknown":
        return jsonify({"error": "Operator not detected for this number"}), 400

    op_info = OPERATOR_PLANS.get(operator, {})
    return jsonify({
        "mobile":   mobile,
        "operator": operator,
        "logo":     op_info.get("logo", "📱"),
        "color":    op_info.get("color", "#6366f1"),
        "detected": True,
    })


@app.route("/api/payment/my-plan", methods=["POST"])
@login_required
def get_my_mobile_plan():
    """
    Detect operator from number, simulate current plan (mid-range prepaid),
    return full list of alternatives sorted by price.
    """
    data     = request.get_json(force=True)
    mobile   = data.get("mobile", "").strip()
    operator = data.get("operator", "").strip() or detect_operator(mobile)

    op_data   = OPERATOR_PLANS.get(operator, {})
    all_pre   = op_data.get("prepaid", [])
    all_post  = op_data.get("postpaid", [])
    all_plans = all_pre + all_post

    if not all_plans:
        return jsonify({"error": f"No plans found for operator: {operator}"}), 404

    # Simulate current plan as mid-range prepaid
    mid     = len(all_pre) // 2 if all_pre else 0
    current = all_pre[mid] if all_pre else all_plans[0]

    alternatives = sorted(
        [p for p in all_plans if p["id"] != current["id"]],
        key=lambda x: x["price"],
    )

    return jsonify({
        "mobile":       mobile,
        "operator":     operator,
        "logo":         op_data.get("logo", "📱"),
        "color":        op_data.get("color", "#6366f1"),
        "current_plan": current,
        "alternatives": alternatives,
        "total_plans":  len(all_plans),
    })


@app.route("/api/payment/recharge", methods=["POST"])
@login_required
def do_recharge():
    """Process a recharge / bill payment (simulated — no real payment gateway)."""
    data     = request.get_json(force=True)
    service  = data.get("service",  "mobile")
    number   = data.get("number",   "").strip()
    plan_id  = data.get("plan_id",  "").strip()
    amount   = data.get("amount",   0)
    operator = data.get("operator", "").strip()

    if not number or not amount:
        return jsonify({"error": "Number and amount are required"}), 400

    txn_id    = f"TXN{random.randint(10000000, 99999999)}"
    plan_name = "Custom Recharge"
    if plan_id:
        plan = get_plan_by_id(plan_id)
        if plan:
            plan_name = plan.get("name", plan_id)
            amount    = plan.get("price", amount)

    return jsonify({
        "success":        True,
        "transaction_id": txn_id,
        "service":        service,
        "operator":       operator,
        "number":         number,
        "plan":           plan_name,
        "amount":         amount,
        "status":         "SUCCESS",
        "message":        f"₹{amount} recharge successful for {number}",
        "timestamp":      datetime.utcnow().isoformat(),
    })


@app.route("/api/payment/transactions")
@login_required
def payment_transactions():
    """Recent transaction history (simulated data)."""
    return jsonify({
        "transactions": [
            {
                "id":       "TXN001", "service": "Mobile",
                "operator": "Jio",       "number":  "9876543210",
                "amount":   299, "status": "SUCCESS",
                "date":     "2024-03-20 14:30", "plan": "Jio Daily 2GB",
            },
            {
                "id":       "TXN002", "service": "DTH",
                "operator": "Tata Play", "number":  "1234567890",
                "amount":   249, "status": "SUCCESS",
                "date":     "2024-03-18 10:15", "plan": "Maxi HD",
            },
            {
                "id":       "TXN003", "service": "Mobile",
                "operator": "Airtel",    "number":  "9811234567",
                "amount":   329, "status": "SUCCESS",
                "date":     "2024-03-15 09:45", "plan": "Airtel 3GB/day",
            },
            {
                "id":       "TXN004", "service": "Electricity",
                "operator": "BSES",      "number":  "CA123456",
                "amount":   850, "status": "SUCCESS",
                "date":     "2024-03-10 16:20", "plan": "Bill Payment",
            },
            {
                "id":       "TXN005", "service": "Mobile",
                "operator": "Vi",        "number":  "9212345678",
                "amount":   239, "status": "FAILED",
                "date":     "2024-03-08 11:00", "plan": "Vi 2GB/day",
            },
        ]
    })


# ═════════════════════════════════════════════════════════════
#  TRIAGE AGENT  — Problem Statement 3
# ═════════════════════════════════════════════════════════════

@app.route("/api/triage/analyze", methods=["POST"])
@login_required
def triage_analyze():
    """
    Full triage pipeline:
      1. NER — extract phone numbers, account IDs, amounts, dates, operators
      2. Urgency classification — CRITICAL / HIGH / MEDIUM / LOW
      3. Intent detection — outage / billing / roaming / complaint / plan_change / etc.
      4. AI draft response via Gemini (falls back to rule-based if offline)
      5. Resolution steps + handle time + escalation recommendation
      6. Ticket creation with TKT-YYYYMMDD-XXXXXX ID
    """
    data    = request.get_json(force=True)
    message = data.get("message", "").strip()
    channel = data.get("channel", "chat")

    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) < 5:
        return jsonify({"error": "Message too short to analyze"}), 400

    user        = get_current_user()
    customer_id = f"USER-{user.id}" if user else "ANONYMOUS"

    result = None
    last_error = None
    for attempt in range(3):
        try:
            result = triage_message(message, channel=channel, customer_id=customer_id)
            break
        except Exception as e:
            last_error = e
            if "503" in str(e) and attempt < 2:
                print(f"[TRIAGE] Gemini 503, retrying in {3 * (attempt + 1)}s… (attempt {attempt + 1})")
                time.sleep(3 * (attempt + 1))
            else:
                raise

    if result is None:
        raise last_error

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/api/triage/entities", methods=["POST"])
@login_required
def triage_entities():
    """Quick NER — extract entities only, no full triage pipeline."""
    data    = request.get_json(force=True)
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    return jsonify({"entities": extract_entities(message), "message": message})


@app.route("/api/triage/tickets")
@login_required
def triage_tickets():
    """Ticket queue with optional urgency and status filters."""
    limit   = request.args.get("limit",   20, type=int)
    urgency = request.args.get("urgency", "").upper().strip()
    status  = request.args.get("status",  "").upper().strip()

    tickets = get_all_tickets(limit=100)
    if urgency:
        tickets = [t for t in tickets if t.get("urgency") == urgency]
    if status:
        tickets = [t for t in tickets if t.get("status")  == status]

    return jsonify({"tickets": tickets[:limit], "total": len(tickets)})


@app.route("/api/triage/tickets/<ticket_id>")
@login_required
def triage_ticket_detail(ticket_id):
    """Get a single ticket by its ID."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket)


@app.route("/api/triage/tickets/<ticket_id>/status", methods=["POST"])
@login_required
def triage_update_status(ticket_id):
    """Update ticket status: OPEN → IN_PROGRESS → RESOLVED → CLOSED"""
    data   = request.get_json(force=True)
    status = data.get("status", "").upper().strip()
    notes  = data.get("notes",  "").strip()
    valid  = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    if status not in valid:
        return jsonify({"error": f"Status must be one of: {', '.join(valid)}"}), 400
    ticket = update_ticket_status(ticket_id, status, notes)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket)


@app.route("/api/triage/stats")
@login_required
def triage_stats():
    """Dashboard stats — counts by urgency, intent, status, escalations."""
    return jsonify(get_ticket_stats())


# ═════════════════════════════════════════════════════════════
#  HEALTH CHECK + ERROR HANDLERS
# ═════════════════════════════════════════════════════════════

@app.route("/health")
@app.route("/api/health")          # ← alias so frontend polling /api/health gets 200
def health():
    vdb = {}
    try:
        vdb = db_stats()
    except Exception:
        pass
    key_info = []
    try:
        key_info = get_key_status()
    except Exception:
        pass
    return jsonify({
        "status":        "healthy",
        "version":       "3.0.0",
        "service":       "TeleBot Telecomm Intelligence Platform",
        "llm_available": is_llm_available(),
        "api_keys":      key_info,
        "vectordb":      vdb,
    })

@app.route("/favicon.ico")
def favicon():
    return "", 204
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


def create_app():
    return app


# ─── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    create_app().run(debug=False, host="0.0.0.0", port=port)