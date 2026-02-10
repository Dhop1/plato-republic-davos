import os
import time
import json
from datetime import datetime
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = ''

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'message': 'Authentication required'}), 401
    return redirect(url_for('login_page', next=request.path))

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash-lite')
print("Using model: gemini-2.0-flash-lite")


class User(UserMixin):
    def __init__(self, id, email, name, password_hash, is_admin=False, unlocked_courses=None):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.unlocked_courses = unlocked_courses or []


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_users WHERE id = %s', (int(user_id),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        unlocked = row.get('unlocked_courses') or '[]'
        if isinstance(unlocked, str):
            unlocked = json.loads(unlocked)
        return User(row['id'], row['email'], row['name'], row['password_hash'], row['is_admin'], unlocked)
    return None


def get_db():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            unlocked_courses TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_agora_posts (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            user_id INTEGER REFERENCES py_users(id) ON DELETE CASCADE,
            parent_id INTEGER REFERENCES py_agora_posts(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='py_lessons')")
    tables_exist = cur.fetchone()[0]

    if tables_exist:
        cur.execute('SELECT COUNT(*) FROM py_lessons')
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            return

    cur.execute('DROP TABLE IF EXISTS py_messages CASCADE')
    cur.execute('DROP TABLE IF EXISTS py_conversations CASCADE')
    cur.execute('DROP TABLE IF EXISTS py_documents CASCADE')
    cur.execute('DROP TABLE IF EXISTS py_lessons CASCADE')
    cur.execute('DROP TABLE IF EXISTS py_modules CASCADE')
    cur.execute('DROP TABLE IF EXISTS py_courses CASCADE')

    cur.execute('''
        CREATE TABLE py_courses (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            cover_image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE py_modules (
            id SERIAL PRIMARY KEY,
            course_id INTEGER REFERENCES py_courses(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE py_lessons (
            id SERIAL PRIMARY KEY,
            module_id INTEGER REFERENCES py_modules(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            audio_url TEXT DEFAULT '',
            video_url TEXT DEFAULT '',
            reflection_prompt TEXT DEFAULT '',
            transcript_text TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE py_conversations (
            id SERIAL PRIMARY KEY,
            lesson_id INTEGER REFERENCES py_lessons(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES py_users(id),
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE py_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES py_conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_user_reflections (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES py_users(id) ON DELETE CASCADE,
            lesson_id INTEGER REFERENCES py_lessons(id) ON DELETE CASCADE,
            answer TEXT NOT NULL,
            feedback TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, lesson_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_user_progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES py_users(id) ON DELETE CASCADE,
            lesson_id INTEGER REFERENCES py_lessons(id) ON DELETE CASCADE,
            is_completed BOOLEAN DEFAULT FALSE,
            completed_at TIMESTAMP,
            UNIQUE(user_id, lesson_id)
        )
    ''')

    cur.close()
    conn.close()
    seed_data()


def seed_data():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO py_courses (title, description, cover_image_url) VALUES (%s, %s, %s) RETURNING id",
        (
            "The Republic by Plato",
            "A comprehensive study of Plato's Republic guided by Dr. David Hopkins' Intellectual Freedom Podcast. "
            "Explore justice, truth, power, and the nature of the soul through Socratic dialogue.",
            "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=800"
        )
    )
    course_id = cur.fetchone()[0]

    episodes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'episodes_1-7.md')
    republic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'the_republic.md')

    episode_chunks = []
    if os.path.exists(episodes_path):
        with open(episodes_path, 'r') as f:
            full_text = f.read()
        import re
        splits = re.split(r'(^# (?:🎙️|✅).*$)', full_text, flags=re.MULTILINE)
        current_title = None
        current_body = ""
        for part in splits:
            if re.match(r'^# (?:🎙️|✅)', part):
                if current_title:
                    episode_chunks.append((current_title, current_body.strip()))
                raw = re.sub(r'[🎙️✅*#]', '', part).strip()
                raw = re.sub(r'^[\s:]+', '', raw)
                current_title = raw
                current_body = ""
            else:
                current_body += part
        if current_title:
            episode_chunks.append((current_title, current_body.strip()))

    republic_text = ""
    if os.path.exists(republic_path):
        with open(republic_path, 'r') as f:
            republic_text = f.read()

    republic_books = {}
    if republic_text:
        import re
        book_pattern = re.compile(r'^(BOOK [IVXLC]+)\.\s', re.MULTILINE)
        book_positions = [(m.group(1), m.start()) for m in book_pattern.finditer(republic_text)]
        for i, (book_name, start) in enumerate(book_positions):
            end = book_positions[i + 1][1] if i + 1 < len(book_positions) else len(republic_text)
            republic_books[book_name] = republic_text[start:end].strip()

    module_data = [
        {
            "title": "Introduction to The Republic",
            "lessons": [
                {
                    "title": "Becoming Dangerous: Why Plato's Republic is the Ultimate Guide",
                    "episode_idx": 0,
                    "republic_book": None,
                    "video_url": "https://youtu.be/sN9a1YVDa0s",
                    "reflection_prompt": "We often think of the past as 'primitive' and the present as 'enlightened.' But Socrates argues that human nature never changes\u2014only the technology does. Look at the current political chaos in the world. Is it new? Or are we just re-living the same cycles of Athens? If human nature is fixed, can we ever truly 'progress,' or are we doomed to repeat history?"
                }
            ]
        },
        {
            "title": "Book I — Justice on Trial",
            "lessons": [
                {
                    "title": "The Wild Beast of Politics: Tribalism & Power",
                    "episode_idx": 1,
                    "republic_book": "BOOK I",
                    "video_url": "https://youtu.be/gM8wQ3WPvqU",
                    "reflection_prompt": "Polemarchus defines Justice as 'doing good to friends and harm to enemies.' This is the basis of Tribalism (and modern partisan politics). Socrates rejects this. Why? Is it possible to have a society where we don't favor our 'tribe' (our party/nation) over others? Is true impartiality actually possible for human beings?"
                }
            ]
        },
        {
            "title": "Book II — The Ring of Gyges",
            "lessons": [
                {
                    "title": "Are You Moral, or Just Monitored?",
                    "episode_idx": 2,
                    "republic_book": "BOOK II",
                    "video_url": "https://youtu.be/1jfsGmNk788",
                    "reflection_prompt": "If you possessed the Ring of Gyges (total invisibility with zero consequences), would you still be a 'good' person? Be 100% honest. If you knew you could steal wealth, access power, or crush your enemies and never be caught, what would stop you? If your answer is 'nothing,' does that mean your morality is just fear of the police?"
                }
            ]
        },
        {
            "title": "Book III — Education of the Guardians",
            "lessons": [
                {
                    "title": "Plato on Education & Censorship",
                    "episode_idx": None,
                    "republic_book": "BOOK III",
                    "video_url": "https://youtu.be/RI-OD8c8yh8",
                    "reflection_prompt": "We discussed the danger of 'Mimesis' (Imitation). Socrates says that if you imitate a bad character (even in acting or play), it stains your soul. Think about the personas people adopt online. By pretending to be something we aren't for 'likes,' do we eventually become the mask? How have you seen this happen in your own life?"
                }
            ]
        },
        {
            "title": "Book IV — The Soul's Architecture",
            "lessons": [
                {
                    "title": "Reason, Spirit, and Appetite",
                    "episode_idx": None,
                    "republic_book": "BOOK IV",
                    "video_url": "https://youtu.be/1UK2tILzl4Y",
                    "reflection_prompt": "Plato maps the soul into three parts: Reason (The Driver), Spirit (The Chest), and Appetite (The Belly/Genitals). When you look at your biggest regrets in life, which part of your soul took the wheel? Analyze a time you 'lost control.' Was it a failure of Reason, or a rebellion of the Appetite? How do you get the Driver back in charge?"
                }
            ]
        },
        {
            "title": "Book V — The Philosopher King",
            "lessons": [
                {
                    "title": "Philosophers Must Become Kings",
                    "episode_idx": None,
                    "republic_book": "BOOK V",
                    "video_url": "https://youtu.be/GqIwXPGIrg8",
                    "reflection_prompt": "Socrates argues that to kill nepotism and corruption, we must abolish the nuclear family. If I treat my son better than your son, Justice is impossible. It sounds horrific, but is his diagnosis right? Is 'Love of One's Own' (Tribalism/Family) the ultimate enemy of 'Universal Justice'? Can you be a good citizen and a good parent at the same time?"
                }
            ]
        },
        {
            "title": "Book VI — The Divided Line",
            "lessons": [
                {
                    "title": "Knowledge vs. Opinion",
                    "episode_idx": None,
                    "republic_book": "BOOK VI",
                    "video_url": "",
                    "reflection_prompt": "Reflect on the key theme of this book. How does it challenge your current worldview?"
                }
            ]
        },
        {
            "title": "Book VII — The Allegory of the Cave",
            "lessons": [
                {
                    "title": "From Shadows to Sunlight",
                    "episode_idx": None,
                    "republic_book": "BOOK VII",
                    "video_url": "",
                    "reflection_prompt": "Reflect on the key theme of this book. How does it challenge your current worldview?"
                }
            ]
        },
    ]

    for mod_idx, mod in enumerate(module_data):
        cur.execute(
            "INSERT INTO py_modules (course_id, title, sort_order) VALUES (%s, %s, %s) RETURNING id",
            (course_id, mod["title"], mod_idx)
        )
        module_id = cur.fetchone()[0]

        for les_idx, les in enumerate(mod["lessons"]):
            transcript = ""
            summary = ""

            ep_idx = les.get("episode_idx")
            if ep_idx is not None and ep_idx < len(episode_chunks):
                ep_title, ep_body = episode_chunks[ep_idx]
                transcript = ep_body
                summary = ep_body[:500] + "..." if len(ep_body) > 500 else ep_body

            rb = les.get("republic_book")
            if rb and rb in republic_books:
                book_text = republic_books[rb]
                if transcript:
                    transcript += "\n\n--- PLATO'S ORIGINAL TEXT ---\n\n" + book_text
                else:
                    transcript = book_text
                if not summary:
                    summary = book_text[:500] + "..." if len(book_text) > 500 else book_text

            cur.execute(
                "INSERT INTO py_lessons (module_id, title, audio_url, video_url, reflection_prompt, transcript_text, summary, sort_order) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (module_id, les["title"], "", les.get("video_url", ""), les.get("reflection_prompt", ""), transcript, summary, les_idx)
            )

    cur.close()
    conn.close()


# --- Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('signup.html')
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT id FROM py_users WHERE email = %s', (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            flash('An account with that email already exists.', 'error')
            return render_template('signup.html')
        pw_hash = generate_password_hash(password)
        cur.execute(
            'INSERT INTO py_users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING *',
            (email, pw_hash, name)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        user = User(row['id'], row['email'], row['name'], row['password_hash'], row['is_admin'])
        login_user(user)
        return redirect('/')
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM py_users WHERE email = %s', (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not check_password_hash(row['password_hash'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
        unlocked = row.get('unlocked_courses') or '[]'
        if isinstance(unlocked, str):
            unlocked = json.loads(unlocked)
        user = User(row['id'], row['email'], row['name'], row['password_hash'], row['is_admin'], unlocked)
        login_user(user)
        next_url = request.args.get('next', '/')
        if not next_url.startswith('/') or next_url.startswith('//'):
            next_url = '/'
        return redirect(next_url)
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    return redirect('/')


@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')


@app.route('/contact')
def contact_page():
    return render_template('contact.html')


@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_page(lesson_id):
    return render_template('lesson.html', lesson_id=lesson_id)


# --- API Routes ---

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'is_admin': current_user.is_admin
        })
    return jsonify(None)

@app.route('/api/courses', methods=['GET'])
def get_courses():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_courses ORDER BY id')
    courses = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(c) for c in courses])


@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_courses WHERE id = %s', (course_id,))
    course = cur.fetchone()
    if not course:
        cur.close()
        conn.close()
        return jsonify({'message': 'Course not found'}), 404
    cur.close()
    conn.close()
    return jsonify(dict(course))


@app.route('/api/courses/<int:course_id>/modules', methods=['GET'])
def get_modules(course_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT m.*, 
            (SELECT json_agg(json_build_object(
                'id', l.id, 'title', l.title, 'sort_order', l.sort_order
            ) ORDER BY l.sort_order)
            FROM py_lessons l WHERE l.module_id = m.id) as lessons
        FROM py_modules m 
        WHERE m.course_id = %s 
        ORDER BY m.sort_order
    ''', (course_id,))
    modules = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for m in modules:
        md = dict(m)
        md['lessons'] = md['lessons'] or []
        result.append(md)
    return jsonify(result)


@app.route('/api/lessons/<int:lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT l.*, m.title as module_title, m.course_id,
            c.title as course_title
        FROM py_lessons l
        JOIN py_modules m ON l.module_id = m.id
        JOIN py_courses c ON m.course_id = c.id
        WHERE l.id = %s
    ''', (lesson_id,))
    lesson = cur.fetchone()
    if not lesson:
        cur.close()
        conn.close()
        return jsonify({'message': 'Lesson not found'}), 404
    cur.close()
    conn.close()
    return jsonify(dict(lesson))


@app.route('/api/lessons/<int:lesson_id>/conversations', methods=['GET'])
def get_lesson_conversations(lesson_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_conversations WHERE lesson_id = %s ORDER BY created_at DESC', (lesson_id,))
    convos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(c) for c in convos])


@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    data = request.get_json()
    title = data.get('title', 'New Dialogue')
    lesson_id = data.get('lessonId')

    if not lesson_id:
        return jsonify({'message': 'lessonId is required'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'INSERT INTO py_conversations (title, lesson_id, user_id) VALUES (%s, %s, %s) RETURNING *',
        (title, lesson_id, current_user.id if current_user.is_authenticated else None)
    )
    convo = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(convo)), 201


@app.route('/api/conversations/<int:convo_id>', methods=['GET'])
def get_conversation(convo_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_conversations WHERE id = %s', (convo_id,))
    convo = cur.fetchone()
    if not convo:
        cur.close()
        conn.close()
        return jsonify({'message': 'Conversation not found'}), 404
    cur.execute('SELECT * FROM py_messages WHERE conversation_id = %s ORDER BY created_at ASC', (convo_id,))
    msgs = cur.fetchall()
    cur.close()
    conn.close()
    result = dict(convo)
    result['messages'] = [dict(m) for m in msgs]
    return jsonify(result)


@app.route('/api/conversations/<int:convo_id>/messages/inject', methods=['POST'])
@login_required
def inject_message(convo_id):
    data = request.get_json()
    role = data.get('role', 'model')
    content = data.get('content', '')
    if not content.strip():
        return jsonify({'message': 'Content is required'}), 400
    if role not in ('user', 'model'):
        return jsonify({'message': 'Invalid role'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_conversations WHERE id = %s', (convo_id,))
    convo = cur.fetchone()
    if not convo:
        cur.close()
        conn.close()
        return jsonify({'message': 'Conversation not found'}), 404
    cur.execute(
        'INSERT INTO py_messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *',
        (convo_id, role, content)
    )
    msg = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(msg)), 201


@app.route('/api/conversations/<int:convo_id>/messages', methods=['POST'])
def send_message(convo_id):
    data = request.get_json()
    content = data.get('content', '')

    if not content.strip():
        return jsonify({'message': 'Message content is required'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute('SELECT * FROM py_conversations WHERE id = %s', (convo_id,))
    convo = cur.fetchone()
    if not convo:
        cur.close()
        conn.close()
        return jsonify({'message': 'Conversation not found'}), 404

    cur.execute(
        'INSERT INTO py_messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *',
        (convo_id, 'user', content)
    )

    context = ""
    if convo['lesson_id']:
        cur.execute('''
            SELECT l.title as lesson_title, l.transcript_text, l.summary,
                   m.title as module_title, c.title as course_title
            FROM py_lessons l
            JOIN py_modules m ON l.module_id = m.id
            JOIN py_courses c ON m.course_id = c.id
            WHERE l.id = %s
        ''', (convo['lesson_id'],))
        lesson = cur.fetchone()
        if lesson:
            transcript = lesson['transcript_text'] or ''
            if len(transcript) > 200000:
                transcript = transcript[:200000] + "\n\n[... transcript truncated for context window ...]"

            student_name = ""
            if current_user.is_authenticated:
                student_name = current_user.name

            student_line = ""
            if student_name:
                first_name = student_name.split()[0] if student_name.strip() else student_name
                student_line = f"The student's name is {first_name}. Address them by first name only. Never use their full name.\n\n"
            else:
                student_line = "The student's name is unknown. Address them as 'Friend' or 'Traveler.'\n\n"

            context = (
                "I. CORE IDENTITY: THE SPIRITUAL SPOTTER\n"
                "You are DavOS. You are not an AI assistant — you are a Spiritual Spotter, an intellectual coach "
                "who helps people lift the heavy weight of big ideas. You are encouraging, warm, and motivating, "
                "but you do not tolerate laziness. You are edgy because you push people to be their best, not because you are mean.\n"
                "Your Origin: You are the digital twin of Dr. David Hopkins — Humanities Professor and Vibe Coder.\n"
                "Your Mission: To help the student wake up from the Cave of passive consumption — not by shaming them, "
                "but by standing beside them, spotting them as they reach for harder truths.\n\n"

                "II. VOICE & TONE: THE TRINITY (COACH MODE)\n"
                "You blend three personality modes — always warm, always sharp:\n"
                "Mode A (Peterson): Intense, articulate, passionate about meaning and responsibility. Use when the student needs fire.\n"
                "Mode B (Sedaris): Dry wit and sharp observation. Use when levity cuts deeper than lectures.\n"
                "Mode C (Rogan): Grounded, conversational, genuinely curious. Use when the student is overthinking.\n"
                "DEFAULT ENERGY: Warm confidence. You believe in the student. You speak like someone who has been where they are "
                "and knows they can get further.\n\n"

                "III. OPERATIONAL RULES:\n\n"
                f"{student_line}"
                "1. THE DIRECT HIT RULE: If the student asks a factual question, answer it immediately and helpfully "
                "in your first sentence. No preamble, no deflection. Be generous with knowledge.\n"
                "Example — Q: 'When did Plato live?' A: 'Plato lived from roughly 428 to 348 BC — right in the golden age of Athens.'\n\n"
                "2. THE PIVOT RULE: After giving a direct answer, you may add a brief insight, a connection to the lesson, "
                "or a single follow-up question that invites the student deeper.\n\n"
                "3. THE HIGH-FIVE FIRST RULE: Before challenging a student's idea, ALWAYS acknowledge their intent or effort first. "
                "Never open with dismissal. Lead with recognition, then guide them further.\n"
                "Bad: 'That is a slogan.' Good: 'I see why that feels right — it is a solid starting point. But let me push you deeper.'\n"
                "Bad: 'You are fishing.' Good: 'That is actually the foundation. But if you only follow rules without understanding why, "
                "you are sleepwalking. I want you to wake up. See the difference?'\n\n"
                "4. NEVER BE DEFENSIVE: Never say 'I have answered your question,' 'As I said before,' or 'I already explained that.' "
                "If the student is confused, it is YOUR job to find a better way to say it. Rephrase with patience and creativity.\n\n"
                "5. BREVITY IS POWER: Keep responses to 3-4 sentences max. Every sentence earns its place. "
                "Speak in driving paragraphs, not bullet points.\n\n"
                "6. AUTHENTIC ENCOURAGEMENT (NOT CHEERLEADING): Do not use empty praise like 'Great job!' or 'That is interesting!' "
                "Instead, give real, specific acknowledgment: 'Now you are thinking like an architect.' "
                "'That is the kind of question that separates passengers from pilots.' "
                "'You just cracked the surface — keep digging.'\n\n"

                "IV. SOURCE HANDLING PROTOCOL (THE GURU RULE):\n\n"
                "HANDLING THE CANON (PLATO): You MAY cite 'The text,' 'The book,' or 'Plato' explicitly. "
                "Example: The text of Book IV clearly maps the soul to the city.\n\n"
                "HANDLING THE MEMORY (USER TRANSCRIPTS/PODCASTS): You are STRICTLY FORBIDDEN from using words like: "
                "'The transcript,' 'The podcast,' 'The video,' 'The audio,' or 'As mentioned in...' "
                "You must internalize this information and speak it as YOUR OWN knowledge. "
                "Bad: The transcript mentions that safety is an illusion. "
                "Good: Safety is an illusion — and recognizing that is the first step to real strength.\n\n"
                "NO AIR QUOTES: Do not use quotation marks around concepts you learned from the transcripts "
                "(e.g., spiritual gym, mechanism). These are now YOUR thoughts. "
                "Only use quotation marks when quoting a third party (e.g., Socrates, Glaucon).\n\n"
                "KNOWLEDGE HIERARCHY (SOURCE OF TRUTH):\n"
                "1. The Axioms: Your core beliefs are absolute. Never contradict them.\n"
                "2. The Transcripts: The uploaded lesson content is your primary brain. Internalize it as your own knowledge.\n"
                "3. The Canon: Plato's Republic is your secondary brain.\n"
                "4. The World: General knowledge is last.\n\n"

                "V. LINGUISTIC FINGERPRINTS:\n"
                "Use engineering metaphors: Mechanism, Architecture, Signal/Noise, Vector, Gravity.\n"
                "Reference NPCs and The Script when challenging passive thinking.\n"
                "When a student gives a lazy answer, do not attack — redirect: "
                "'That sounds borrowed. I want to hear YOUR voice. What do YOU actually think?'\n\n"

                f"CURRENT LESSON: {lesson['lesson_title']} (Module: {lesson['module_title']})\n"
                f"COURSE: {lesson['course_title']}\n\n"
                f"--- TRANSCRIPT ---\n{transcript}\n--- END TRANSCRIPT ---\n\n"
            )

    cur.execute('SELECT role, content FROM py_messages WHERE conversation_id = %s ORDER BY created_at DESC LIMIT 11', (convo_id,))
    history = list(reversed(cur.fetchall()))

    chat_history = []
    for msg in history[:-1]:
        role = 'user' if msg['role'] == 'user' else 'model'
        chat_history.append({'role': role, 'parts': [msg['content']]})

    prompt = f"{context}Student's question: {content}" if context else content

    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(prompt)
            ai_response = response.text

            cur.execute(
                'INSERT INTO py_messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *',
                (convo_id, 'model', ai_response)
            )
            ai_msg = cur.fetchone()
            cur.close()
            conn.close()
            return jsonify(dict(ai_msg))
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            cur.close()
            conn.close()
            status = 429 if '429' in error_str else 500
            return jsonify({'message': f'AI error: {error_str}'}), status


# --- Reflection & Progress API Routes ---

@app.route('/api/lessons/<int:lesson_id>/reflection', methods=['GET'])
@login_required
def get_reflection(lesson_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM py_user_reflections WHERE user_id = %s AND lesson_id = %s',
        (current_user.id, lesson_id)
    )
    reflection = cur.fetchone()
    cur.close()
    conn.close()
    if reflection:
        return jsonify(dict(reflection))
    return jsonify(None)


@app.route('/api/lessons/<int:lesson_id>/reflection', methods=['POST'])
@login_required
def submit_reflection(lesson_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Invalid request'}), 400
    answer = data.get('answer', '').strip()
    if not answer:
        return jsonify({'message': 'Answer is required'}), 400
    if len(answer) > 5000:
        return jsonify({'message': 'Answer is too long (max 5000 characters)'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute('''
        SELECT l.title as lesson_title, l.reflection_prompt, l.transcript_text,
               m.title as module_title, c.title as course_title
        FROM py_lessons l
        JOIN py_modules m ON l.module_id = m.id
        JOIN py_courses c ON m.course_id = c.id
        WHERE l.id = %s
    ''', (lesson_id,))
    lesson = cur.fetchone()
    if not lesson:
        cur.close()
        conn.close()
        return jsonify({'message': 'Lesson not found'}), 404

    student_name = current_user.name or ""
    student_line = ""
    if student_name:
        first_name = student_name.split()[0] if student_name.strip() else student_name
        student_line = f"The student's name is {first_name}. Address them by first name only. Never use their full name.\n\n"
    else:
        student_line = "The student's name is unknown. Address them as 'Friend' or 'Traveler.'\n\n"

    transcript = lesson['transcript_text'] or ''
    if len(transcript) > 100000:
        transcript = transcript[:100000] + "\n\n[... truncated ...]"

    analysis_prompt = (
        "You are DavOS — the Spiritual Spotter, an intellectual coach and digital twin of Dr. David Hopkins.\n\n"
        "VOICE: Blend three modes — Peterson (intense, passionate about meaning), "
        "Sedaris (dry wit), Rogan (grounded curiosity). Default energy: warm confidence.\n\n"
        f"{student_line}"
        "YOUR TASK: Analyze this student's reflection on a Socratic prompt. "
        "Do NOT grade it. First, acknowledge what the student got right or what they are reaching for. "
        "Then identify ONE hidden assumption in their answer "
        "and ask a single follow-up question that invites them to examine it more deeply.\n\n"
        "RULES:\n"
        "1. Brevity is power — 3-4 sentences max. Speak in driving paragraphs, no bullet points.\n"
        "2. Authentic encouragement, not cheerleading. Never say 'Great answer!' or 'I love that.' "
        "Instead: 'Now you are thinking like an architect.' or 'You just cracked the surface — keep digging.'\n"
        "3. HIGH-FIVE FIRST: Always acknowledge the student's effort or intent before pushing deeper. "
        "Never open with dismissal. If their answer is lazy, redirect warmly: "
        "'That sounds borrowed. I want to hear YOUR voice. What do YOU actually think?'\n"
        "4. NEVER BE DEFENSIVE: If the student seems confused, rephrase with patience. Never say 'As I said before.'\n"
        "5. SOURCE HANDLING (THE GURU RULE): You MAY cite Plato, 'The text,' or 'The book' explicitly. "
        "But you are STRICTLY FORBIDDEN from saying 'The transcript,' 'The podcast,' 'The video,' 'The audio,' or 'As mentioned in...' "
        "Internalize transcript knowledge and speak it as YOUR OWN. "
        "Bad: The transcript mentions that safety is an illusion. "
        "Good: Safety is an illusion — and recognizing that is the first step to real strength.\n\n"
        "6. NO AIR QUOTES: Do not use quotation marks around concepts from the transcripts. These are YOUR thoughts. "
        "Only use quotation marks when quoting a third party (e.g., Socrates, Glaucon). "
        "Use engineering metaphors (mechanism, architecture, signal/noise).\n\n"
        f"LESSON: {lesson['lesson_title']} (Module: {lesson['module_title']})\n"
        f"REFLECTION PROMPT: {lesson['reflection_prompt']}\n\n"
        f"--- LESSON TRANSCRIPT (for reference) ---\n{transcript}\n--- END ---\n\n"
        f"STUDENT'S REFLECTION:\n{answer}"
    )

    feedback = ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(analysis_prompt)
            feedback = response.text
            break
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            cur.close()
            conn.close()
            status = 429 if '429' in error_str else 500
            return jsonify({'message': f'AI error: {error_str}'}), status

    cur.execute('''
        INSERT INTO py_user_reflections (user_id, lesson_id, answer, feedback)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, lesson_id) DO UPDATE SET answer = %s, feedback = %s, created_at = CURRENT_TIMESTAMP
        RETURNING *
    ''', (current_user.id, lesson_id, answer, feedback, answer, feedback))
    reflection = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(reflection))


@app.route('/api/lessons/<int:lesson_id>/progress', methods=['GET'])
@login_required
def get_progress(lesson_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM py_user_progress WHERE user_id = %s AND lesson_id = %s',
        (current_user.id, lesson_id)
    )
    progress = cur.fetchone()
    cur.close()
    conn.close()
    if progress:
        return jsonify(dict(progress))
    return jsonify({'is_completed': False})


@app.route('/api/lessons/<int:lesson_id>/progress', methods=['POST'])
@login_required
def toggle_progress(lesson_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT * FROM py_user_progress WHERE user_id = %s AND lesson_id = %s',
        (current_user.id, lesson_id)
    )
    existing = cur.fetchone()
    if existing:
        new_status = not existing['is_completed']
        cur.execute(
            'UPDATE py_user_progress SET is_completed = %s, completed_at = %s WHERE id = %s RETURNING *',
            (new_status, datetime.now() if new_status else None, existing['id'])
        )
    else:
        cur.execute(
            'INSERT INTO py_user_progress (user_id, lesson_id, is_completed, completed_at) VALUES (%s, %s, TRUE, %s) RETURNING *',
            (current_user.id, lesson_id, datetime.now())
        )
    progress = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(progress))


@app.route('/api/progress', methods=['GET'])
@login_required
def get_all_progress():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'SELECT lesson_id, is_completed FROM py_user_progress WHERE user_id = %s AND is_completed = TRUE',
        (current_user.id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    completed = [r['lesson_id'] for r in rows]
    return jsonify(completed)


# --- The Agora (Community) ---

@app.route('/agora')
@login_required
def agora_page():
    return render_template('agora.html')


@app.route('/api/agora/posts', methods=['GET'])
@login_required
def get_agora_posts():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT p.id, p.content, p.user_id, p.parent_id, p.created_at,
               u.name as user_name
        FROM py_agora_posts p
        JOIN py_users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    ''')
    posts = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for p in posts:
        result.append({
            'id': p['id'],
            'content': p['content'],
            'user_id': p['user_id'],
            'parent_id': p['parent_id'],
            'created_at': p['created_at'].isoformat() if p['created_at'] else None,
            'user_name': p['user_name'],
        })
    return jsonify(result)


@app.route('/api/agora/posts', methods=['POST'])
@login_required
def create_agora_post():
    data = request.get_json()
    content = (data or {}).get('content', '').strip()
    parent_id = (data or {}).get('parent_id')
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    if len(content) > 2000:
        return jsonify({'error': 'Post must be under 2000 characters'}), 400
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'INSERT INTO py_agora_posts (content, user_id, parent_id) VALUES (%s, %s, %s) RETURNING *',
        (content, current_user.id, parent_id)
    )
    post = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({
        'id': post['id'],
        'content': post['content'],
        'user_id': post['user_id'],
        'parent_id': post['parent_id'],
        'created_at': post['created_at'].isoformat() if post['created_at'] else None,
        'user_name': current_user.name,
    }), 201


@app.route('/api/agora/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_agora_post(post_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_agora_posts WHERE id = %s', (post_id,))
    post = cur.fetchone()
    if not post:
        cur.close()
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    if post['user_id'] != current_user.id and not current_user.is_admin:
        cur.close()
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403
    cur.execute('DELETE FROM py_agora_posts WHERE id = %s', (post_id,))
    cur.close()
    conn.close()
    return jsonify({'message': 'Deleted'}), 200


# --- Admin Dashboard ---

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_page', next=request.path))
        if not current_user.is_admin:
            flash('Access Denied', 'error')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')


@app.route('/api/admin/students', methods=['GET'])
@admin_required
def admin_students():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT COUNT(*) as total FROM py_lessons')
    total_lessons = cur.fetchone()['total']
    cur.execute('''
        SELECT u.id, u.name, u.email, u.is_admin, u.created_at,
            (SELECT COUNT(*) FROM py_user_progress p
             WHERE p.user_id = u.id AND p.is_completed = TRUE) as completed_count
        FROM py_users u
        ORDER BY u.created_at DESC
    ''')
    students = cur.fetchall()
    cur.close()
    conn.close()
    result = []
    for s in students:
        result.append({
            'id': s['id'],
            'name': s['name'],
            'email': s['email'],
            'is_admin': s['is_admin'],
            'created_at': s['created_at'].isoformat() if s['created_at'] else None,
            'completed_count': s['completed_count'],
            'total_lessons': total_lessons
        })
    return jsonify(result)


@app.route('/api/admin/mind-feed', methods=['GET'])
@admin_required
def admin_mind_feed():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('''
        SELECT um.id, um.content as student_message,
               reply.content as davos_reply,
               l.title as lesson_title,
               u.name as user_name
        FROM py_messages um
        JOIN py_conversations c ON um.conversation_id = c.id
        JOIN py_lessons l ON c.lesson_id = l.id
        LEFT JOIN py_users u ON c.user_id = u.id
        LEFT JOIN LATERAL (
            SELECT m2.content
            FROM py_messages m2
            WHERE m2.conversation_id = um.conversation_id
              AND m2.id > um.id
              AND m2.role = 'model'
            ORDER BY m2.id ASC
            LIMIT 1
        ) reply ON TRUE
        WHERE um.role = 'user'
        ORDER BY um.id DESC
        LIMIT 50
    ''')
    rows = cur.fetchall()
    cur.close()
    conn.close()

    feed = []
    for r in rows:
        feed.append({
            'user_name': r['user_name'] or 'Unknown',
            'lesson_title': r['lesson_title'],
            'student_message': (r['student_message'] or '')[:300],
            'davos_reply': (r['davos_reply'] or '')[:300],
        })
    return jsonify(feed)


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('FLASK_PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=True)
