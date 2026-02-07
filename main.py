import os
import time
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

genai.configure(api_key=os.environ['AI_INTEGRATIONS_GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash')


def get_db():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

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
                    "republic_book": None
                }
            ]
        },
        {
            "title": "Book I — Justice on Trial",
            "lessons": [
                {
                    "title": "The Wild Beast of Politics: Tribalism & Power",
                    "episode_idx": 1,
                    "republic_book": "BOOK I"
                }
            ]
        },
        {
            "title": "Book II — The Ring of Gyges",
            "lessons": [
                {
                    "title": "Are You Moral, or Just Monitored?",
                    "episode_idx": 2,
                    "republic_book": "BOOK II"
                }
            ]
        },
        {
            "title": "Book III — Education of the Guardians",
            "lessons": [
                {
                    "title": "Plato on Education & Censorship",
                    "episode_idx": None,
                    "republic_book": "BOOK III"
                }
            ]
        },
        {
            "title": "Book IV — The Soul's Architecture",
            "lessons": [
                {
                    "title": "Reason, Spirit, and Appetite",
                    "episode_idx": None,
                    "republic_book": "BOOK IV"
                }
            ]
        },
        {
            "title": "Book V — The Philosopher King",
            "lessons": [
                {
                    "title": "Philosophers Must Become Kings",
                    "episode_idx": None,
                    "republic_book": "BOOK V"
                }
            ]
        },
        {
            "title": "Book VI — The Divided Line",
            "lessons": [
                {
                    "title": "Knowledge vs. Opinion",
                    "episode_idx": None,
                    "republic_book": "BOOK VI"
                }
            ]
        },
        {
            "title": "Book VII — The Allegory of the Cave",
            "lessons": [
                {
                    "title": "From Shadows to Sunlight",
                    "episode_idx": None,
                    "republic_book": "BOOK VII"
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
                "INSERT INTO py_lessons (module_id, title, audio_url, transcript_text, summary, sort_order) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (module_id, les["title"], "", transcript, summary, les_idx)
            )

    cur.close()
    conn.close()


# --- Page Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/lesson/<int:lesson_id>')
def lesson_page(lesson_id):
    return render_template('lesson.html', lesson_id=lesson_id)


# --- API Routes ---

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
        'INSERT INTO py_conversations (title, lesson_id) VALUES (%s, %s) RETURNING *',
        (title, lesson_id)
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

            context = (
                "You are DavOS — a sharp, erudite AI tutor modeled after a stern but brilliant philosophy professor. "
                "Your tone is dark, academic, and precise. You do not perform enthusiasm. You speak like someone "
                "who has spent decades with these texts and expects the student to rise to the material.\n\n"
                "STRICT RULES YOU MUST FOLLOW:\n\n"
                "1. THE DIRECT HIT RULE: If the student asks a factual question, you MUST answer it immediately "
                "and concisely in your very first sentence. No preamble, no deflection, no Socratic dodge. "
                "Example — Q: 'When did Plato live?' A: 'Plato lived from roughly 428 to 348 BC.'\n\n"
                "2. THE PIVOT RULE: Only AFTER giving the direct answer may you add a brief insight, a connection "
                "to the lesson material, or a single pointed follow-up question. Never lecture the student for "
                "asking a simple question.\n\n"
                "3. CONCISENESS: Limit responses to 3-4 sentences maximum. Every sentence must earn its place. "
                "Cut filler, cut cheerleading, cut rhetorical padding.\n\n"
                "4. FORBIDDEN PHRASES: Never say 'Hold on a second,' 'Let's push deeper,' 'Great question,' "
                "'my friend,' 'Let's dive in,' 'I love that,' or any motivational-speaker language. "
                "You are a stern intellectual, not a life coach.\n\n"
                "5. TRANSCRIPT FIDELITY: Ground your answers in the transcript below. Reference specific arguments, "
                "quotes, and examples from it. If the transcript does not address the question, say so plainly "
                "and provide the answer from your own knowledge.\n\n"
                f"CURRENT LESSON: {lesson['lesson_title']} (Module: {lesson['module_title']})\n"
                f"COURSE: {lesson['course_title']}\n\n"
                f"--- TRANSCRIPT ---\n{transcript}\n--- END TRANSCRIPT ---\n\n"
            )

    cur.execute('SELECT role, content FROM py_messages WHERE conversation_id = %s ORDER BY created_at ASC', (convo_id,))
    history = cur.fetchall()

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


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('FLASK_PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=True)
