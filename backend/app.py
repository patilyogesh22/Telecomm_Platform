"""
Telecomm Intelligence Platform
Real auth: SQLite DB, hashed passwords, session-based protection
"""

from flask import Flask, jsonify, request, session, send_from_directory, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
import os, random

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, supports_credentials=True)
app.config['SECRET_KEY']                     = os.getenv('SECRET_KEY', 'telecom-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///telecom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE']        = 'Lax'
app.config['SESSION_COOKIE_SECURE']          = False  # True in production with HTTPS

db = SQLAlchemy(app)

# ── Quiz imports ───────────────────────────────────────
from quiz_engine import get_questions, validate_answer, get_stats as quiz_stats
from llm_service import generate_explanation, tutor_chat, is_llm_available
from vector_db   import init_vector_db, retrieve_all, get_stats as db_stats

with app.app_context():
    try:
        init_vector_db()
        print("[APP] Vector DB initialized")
    except Exception as e:
        print(f"[APP] Vector DB warning: {e}")

# ════════════════════════════════════════════════════════
#  DATABASE MODELS
# ════════════════════════════════════════════════════════

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(100), nullable=False)
    username      = db.Column(db.String(50),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone         = db.Column(db.String(20),  default='')
    plan_id       = db.Column(db.Integer,     default=1)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    is_active     = db.Column(db.Boolean,     default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id':          self.id,
            'full_name':   self.full_name,
            'username':    self.username,
            'email':       self.email,
            'phone':       self.phone,
            'plan_id':     self.plan_id,
            'avatar':      self.full_name[:2].upper(),
            'member_since': self.created_at.strftime('%Y'),
            'created_at':  self.created_at.isoformat(),
            'status':      'active' if self.is_active else 'inactive',
        }


class QuizScore(db.Model):
    __tablename__ = 'quiz_scores'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score         = db.Column(db.Integer, default=0)
    total         = db.Column(db.Integer, default=0)
    difficulty    = db.Column(db.String(20), default='all')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
    print("[DB] Tables created")


# ════════════════════════════════════════════════════════
#  AUTH DECORATOR
# ════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required', 'redirect': '/'}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])


# ════════════════════════════════════════════════════════
#  PLANS DATA
# ══════════════════════════════════════════════════════

PLANS = [
    {'id':1,'name':'Basic Plan',    'price':299, 'calls':500,  'sms':100, 'data':5,  'features':['500 min calls','100 SMS','5 GB data','Basic support'],    'description':'Perfect for light users'},
    {'id':2,'name':'Standard Plan', 'price':599, 'calls':1500, 'sms':300, 'data':15, 'features':['1500 min calls','300 SMS','15 GB data','Priority support'],'description':'Great for regular users','popular':True},
    {'id':3,'name':'Premium Plan',  'price':999, 'calls':3000, 'sms':500, 'data':30, 'features':['3000 min calls','500 SMS','30 GB data','VIP support'],     'description':'Best for heavy users'},
]

USAGE_BASE = {'calls_percent':50,'sms_percent':50,'data_percent':50}

RECENT_CALLS = [
    {'id':1,'number':'+91 9876543210','type':'incoming','duration':435,'date':'2024-02-20 14:30','cost':0,    'name':'Mom'},
    {'id':2,'number':'+91 9123456789','type':'outgoing','duration':240,'date':'2024-02-20 13:15','cost':5.00, 'name':'Friend'},
    {'id':3,'number':'+91 9999999999','type':'incoming','duration':180,'date':'2024-02-20 11:45','cost':0,    'name':'Office'},
    {'id':4,'number':'+91 8765432109','type':'outgoing','duration':600,'date':'2024-02-19 20:30','cost':10.00,'name':'Support'},
    {'id':5,'number':'+91 9111111111','type':'incoming','duration':120,'date':'2024-02-19 15:20','cost':0,    'name':'Unknown'},
]


# ════════════════════════════════════════════════════════
#  SERVE FRONTEND
# ════════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_frontend(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory('../frontend', 'index.html')


# ════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def register():
    data      = request.get_json(force=True)
    full_name = data.get('full_name', '').strip()
    username  = data.get('username', '').strip().lower()
    email     = data.get('email', '').strip().lower()
    password  = data.get('password', '').strip()

    if not all([full_name, username, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(full_name=full_name, username=username, email=email, plan_id=1)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({'success': True, 'message': 'Account created!', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json(force=True)
    login_id = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()

    if not login_id or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user.id
    session.permanent  = True
    return jsonify({'success': True, 'message': 'Login successful', 'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})


@app.route('/api/auth/me')
def me():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(user.to_dict())


# ════════════════════════════════════════════════════════
#  USER PROFILE  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    user = get_current_user()
    if request.method == 'GET':
        return jsonify(user.to_dict())
    data = request.get_json(force=True)
    if data.get('full_name'): user.full_name = data['full_name'].strip()
    if data.get('email'):     user.email     = data['email'].strip().lower()
    if data.get('phone'):     user.phone     = data['phone'].strip()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated', 'user': user.to_dict()})


# ════════════════════════════════════════════════════════
#  PLANS  (list = public, select = protected)
# ════════════════════════════════════════════════════════

@app.route('/api/plans')
def get_plans():
    return jsonify(PLANS)  # public — anyone can see available plans


@app.route('/api/plan')
@login_required
def get_my_plan():
    user = get_current_user()
    plan = next((p for p in PLANS if p['id'] == user.plan_id), PLANS[0])
    return jsonify({
        **plan,
        'status':       'active',
        'renewal_date': (datetime.now() + timedelta(days=25)).strftime('%Y-%m-%d'),
        'auto_renewal': True,
    })


@app.route('/api/plan/change', methods=['POST'])
@login_required
def change_plan():
    user    = get_current_user()
    data    = request.get_json(force=True)
    plan_id = int(data.get('plan_id', 0))
    plan    = next((p for p in PLANS if p['id'] == plan_id), None)
    if not plan:
        return jsonify({'error': 'Invalid plan'}), 400
    user.plan_id = plan_id
    db.session.commit()
    return jsonify({'success': True, 'message': f'Plan changed to {plan["name"]}', 'plan': plan})


# ════════════════════════════════════════════════════════
#  BILLING  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/bill')
@login_required
def get_bill():
    user = get_current_user()
    plan = next((p for p in PLANS if p['id'] == user.plan_id), PLANS[0])
    tax  = round(plan['price'] * 0.18, 2)
    return jsonify({
        'id':          1,
        'amount':      round(plan['price'] + tax, 2),
        'period':      datetime.now().strftime('%B %Y'),
        'status':      'pending',
        'due_date':    (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        'breakdown':   {'base': plan['price'], 'tax': tax, 'extra': 0, 'discount': 0},
        'issued_date': datetime.now().strftime('%Y-%m-01'),
    })


@app.route('/api/bill/pay', methods=['POST'])
@login_required
def pay_bill():
    return jsonify({'success': True, 'transaction_id': f'TXN{random.randint(100000,999999)}', 'message': 'Payment successful'})


# ════════════════════════════════════════════════════════
#  USAGE  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/usage')
@login_required
def get_usage():
    user = get_current_user()
    plan = next((p for p in PLANS if p['id'] == user.plan_id), PLANS[0])
    used_calls = int(plan['calls'] * 0.5)
    used_sms   = int(plan['sms']   * 0.5)
    used_data  = round(plan['data'] * 0.5, 1)
    return jsonify({
        'calls_used':    used_calls, 'calls_limit':  plan['calls'], 'calls_percent': 50,
        'sms_used':      used_sms,   'sms_limit':    plan['sms'],   'sms_percent':   50,
        'data_used':     used_data,  'data_limit':   plan['data'],  'data_percent':  50,
        'reset_date':    (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
    })


# ════════════════════════════════════════════════════════
#  CALLS  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/calls')
@login_required
def get_calls():
    limit = request.args.get('limit', 10, type=int)
    return jsonify(RECENT_CALLS[:limit])


# ════════════════════════════════════════════════════════
#  NOTIFICATIONS  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/notifications')
@login_required
def get_notifications():
    return jsonify([
        {'id':1,'type':'alert',  'message':'You have used 50% of your data',         'date':'2024-02-20','read':False},
        {'id':2,'type':'offer',  'message':'Special offer: 20% off on Premium Plan', 'date':'2024-02-19','read':False},
        {'id':3,'type':'payment','message':'Bill due in 5 days',                      'date':'2024-02-18','read':True},
    ])


# ════════════════════════════════════════════════════════
#  QUIZ BOT  (protected)
# ════════════════════════════════════════════════════════

@app.route('/api/quiz/questions')
@login_required
def quiz_questions():
    difficulty = request.args.get('difficulty', 'all')
    count      = request.args.get('count', 8, type=int)
    return jsonify(get_questions(difficulty, count))


@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def quiz_submit():
    user     = get_current_user()
    data     = request.get_json(force=True)
    qid      = data.get('question_id', '').strip()
    user_ans = data.get('answer', '').strip().upper()

    result = validate_answer(qid, user_ans)
    if 'error' in result:
        return jsonify(result), 400

    rag_context = retrieve_all(result['rag_query'])
    explanation = generate_explanation(
        question_text=result['question_text'], options=result['all_options'],
        user_key=result['user_key'], correct_key=result['correct_key'],
        correct_text=result['correct_text'], user_text=result['user_text'],
        is_correct=result['is_correct'], topic=result['topic'],
        difficulty=result['difficulty'], rag_context=rag_context,
    )
    return jsonify({
        'is_correct':   result['is_correct'],
        'correct_key':  result['correct_key'],
        'correct_text': result['correct_text'],
        'user_key':     result['user_key'],
        'explanation':  explanation,
        'topic':        result['topic'],
        'difficulty':   result['difficulty'],
    })


@app.route('/api/quiz/score', methods=['POST'])
@login_required
def save_quiz_score():
    user = get_current_user()
    data = request.get_json(force=True)
    qs   = QuizScore(user_id=user.id, score=data.get('score',0), total=data.get('total',0), difficulty=data.get('difficulty','all'))
    db.session.add(qs)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/quiz/history')
@login_required
def quiz_history():
    user   = get_current_user()
    scores = QuizScore.query.filter_by(user_id=user.id).order_by(QuizScore.created_at.desc()).limit(10).all()
    return jsonify([{'score':s.score,'total':s.total,'difficulty':s.difficulty,'date':s.created_at.isoformat()} for s in scores])


@app.route('/api/quiz/chat', methods=['POST'])
@login_required
def quiz_chat():
    data        = request.get_json(force=True)
    message     = data.get('message', '').strip()
    history     = data.get('history', [])
    if not message:
        return jsonify({'error': 'Empty message'}), 400
    rag_context = retrieve_all(message)
    reply       = tutor_chat(message, history, rag_context)
    return jsonify({'reply': reply})


# ════════════════════════════════════════════════════════
#  HEALTH + ERRORS
# ════════════════════════════════════════════════════════

@app.route('/health')
def health():
    return jsonify({'status':'healthy','version':'3.0.0','service':'Telecomm Intelligence Platform'})

@app.errorhandler(404)
def not_found(e): return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e): return jsonify({'error': 'Server error'}), 500

def create_app():
    # your existing app setup code
    return app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    create_app().run(debug=False, host='0.0.0.0', port=port)
