import os
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'md', 'text'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

genai.configure(api_key=os.environ['AI_INTEGRATIONS_GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash')


def get_db():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = True
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_courses (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            cover_image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_documents (
            id SERIAL PRIMARY KEY,
            course_id INTEGER REFERENCES py_courses(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_conversations (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            course_id INTEGER REFERENCES py_courses(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS py_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES py_conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('SELECT COUNT(*) FROM py_courses')
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute('''
            INSERT INTO py_courses (title, description, cover_image_url) VALUES
            (%s, %s, %s),
            (%s, %s, %s),
            (%s, %s, %s)
        ''', (
            'The Republic: Book I - Justice',
            'Socrates discusses the meaning of justice with Cephalus, Polemarchus, and Thrasymachus. Is justice merely speaking the truth and paying debts, or is it the advantage of the stronger?',
            'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=800',
            'The Republic: Book VII - The Cave',
            'Plato\'s famous Allegory of the Cave concerning the nature of education and enlightenment. The journey from shadows on the wall to the brilliant light of the sun.',
            'https://images.unsplash.com/photo-1535905557558-afc4877a26fc?w=800',
            'The Republic: Book V - The Philosopher King',
            'The argument that philosophers must become kings, or kings must learn philosophy. The nature of true knowledge versus mere opinion.',
            'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=800',
        ))
    cur.close()
    conn.close()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    return render_template('course.html', course_id=course_id)


@app.route('/chat/<int:conversation_id>')
def chat_page(conversation_id):
    return render_template('chat.html', conversation_id=conversation_id)


@app.route('/api/courses', methods=['GET'])
def get_courses():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_courses ORDER BY created_at DESC')
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
    cur.close()
    conn.close()
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    return jsonify(dict(course))


@app.route('/api/courses/<int:course_id>/documents', methods=['GET'])
def get_documents(course_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM py_documents WHERE course_id = %s ORDER BY created_at DESC', (course_id,))
    docs = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(d) for d in docs])


@app.route('/api/documents', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400

    file = request.files['file']
    course_id = request.form.get('courseId')
    title = request.form.get('title', '')

    if not course_id:
        return jsonify({'message': 'Course ID is required'}), 400
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'message': 'Only .txt and .md files are allowed'}), 400

    content = file.read().decode('utf-8')
    filename = secure_filename(file.filename)
    if not title:
        title = filename

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'INSERT INTO py_documents (course_id, title, content, filename) VALUES (%s, %s, %s, %s) RETURNING *',
        (int(course_id), title, content, filename)
    )
    doc = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(dict(doc)), 201


@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM py_documents WHERE id = %s', (doc_id,))
    cur.close()
    conn.close()
    return '', 204


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    course_id = request.args.get('courseId')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if course_id:
        cur.execute('SELECT * FROM py_conversations WHERE course_id = %s ORDER BY created_at DESC', (int(course_id),))
    else:
        cur.execute('SELECT * FROM py_conversations ORDER BY created_at DESC')
    convos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(c) for c in convos])


@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    data = request.get_json()
    title = data.get('title', 'New Dialogue')
    course_id = data.get('courseId')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        'INSERT INTO py_conversations (title, course_id) VALUES (%s, %s) RETURNING *',
        (title, course_id)
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
    if convo['course_id']:
        cur.execute('SELECT title, content FROM py_documents WHERE course_id = %s', (convo['course_id'],))
        docs = cur.fetchall()
        if docs:
            context = "You are a scholarly tutor specializing in Plato's Republic. Use these uploaded texts as your primary source material:\n\n"
            for d in docs:
                context += f"--- {d['title']} ---\n{d['content']}\n\n"
            context += "Answer the student's question based on these texts. Be thorough, cite specific passages when possible, and maintain a scholarly tone.\n\n"

    cur.execute('SELECT role, content FROM py_messages WHERE conversation_id = %s ORDER BY created_at ASC', (convo_id,))
    history = cur.fetchall()

    chat_history = []
    for msg in history[:-1]:
        role = 'user' if msg['role'] == 'user' else 'model'
        chat_history.append({'role': role, 'parts': [msg['content']]})

    prompt = f"{context}Student's question: {content}" if context else content

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
        cur.close()
        conn.close()
        return jsonify({'message': f'AI error: {str(e)}'}), 500


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
