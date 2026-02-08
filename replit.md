# The Republic - Plato Study Platform

## Overview
A Dark Academia-themed course platform for studying Plato's "The Republic" with the "DavOS" AI tutor (Google Gemini). Users can sign up, log in, and interact with an AI that uses uploaded documents as context. The AI persona is "DavOS" — inspired by Dr. David Hopkins' Intellectual Freedom Podcast — prioritizing podcast transcripts as primary sources over generic reference texts.

## Architecture
- **Backend**: Python Flask (main.py) running on port 5001 internally
- **Proxy**: Node.js Express (server/routes.ts) spawns Flask and proxies all requests from port 5000
- **Auth**: Flask-Login with werkzeug password hashing (email/password accounts)
- **Database**: PostgreSQL with tables prefixed `py_` (py_users, py_courses, py_modules, py_lessons, py_conversations, py_messages)
- **AI**: Google Gemini via `google.generativeai` library, API key from `AI_INTEGRATIONS_GEMINI_API_KEY`
- **Frontend**: Server-rendered Jinja2 templates with vanilla JS, served from templates/ and static/

## Key Files
- `main.py` - Flask application with all API routes, auth, and database setup
- `server/routes.ts` - Node.js proxy that spawns Flask and forwards requests (including form POST data)
- `templates/base.html` - Base template with toast notifications and auth nav loader
- `templates/index.html` - Landing page with course overview and module grid
- `templates/lesson.html` - 3-column lesson view with sidebar nav, transcript, and DavOS chat
- `templates/signup.html` - Sign up page (Dark Academia style)
- `templates/login.html` - Login page
- `templates/profile.html` - Citizen Profile page showing user info and active courses
- `static/css/style.css` - Dark Academia theme CSS

## Database Schema
- **py_users**: id, email (unique), password_hash, name, is_admin, unlocked_courses (JSON string), created_at
- **py_courses**: id, title, description, cover_image_url
- **py_modules**: id, course_id (FK), title, sort_order — one per Book of The Republic
- **py_lessons**: id, module_id (FK), title, audio_url, video_url, transcript_text, summary, sort_order, reflection_prompt
- **py_conversations**: id, lesson_id (FK), title
- **py_messages**: id, conversation_id (FK), role, content
- **py_user_reflections**: id, user_id (FK), lesson_id (FK), answer, feedback, created_at — UNIQUE(user_id, lesson_id)
- **py_user_progress**: id, user_id (FK), lesson_id (FK), is_completed, completed_at — UNIQUE(user_id, lesson_id)

## Page Routes
- `GET /` - Landing page (public)
- `GET /signup` / `POST /signup` - Sign up form
- `GET /login` / `POST /login` - Login form
- `GET /logout` - Log out and redirect home
- `GET /profile` - Citizen Profile page (login required)
- `GET /lesson/:id` - Lesson view (login required, redirects to login if unauthenticated)

## API Routes
- `GET /api/auth/me` - Get current user info (or null if not logged in)
- `GET /api/courses` - List all courses
- `GET /api/courses/:id` - Get single course
- `GET /api/courses/:id/modules` - List modules with nested lessons
- `GET /api/lessons/:id` - Get lesson with transcript and module/course info
- `GET /api/lessons/:id/conversations` - List conversations for a lesson
- `POST /api/conversations` - Create conversation (JSON: {title, lessonId})
- `GET /api/conversations/:id` - Get conversation with messages
- `POST /api/conversations/:id/messages` - Send message to DavOS AI tutor
- `POST /api/conversations/:id/messages/inject` - Inject a message into conversation history (JSON: {role, content})
- `GET /api/lessons/:id/reflection` - Get user's reflection for a lesson (login required)
- `POST /api/lessons/:id/reflection` - Submit reflection for DavOS analysis (JSON: {answer}, login required)
- `GET /api/lessons/:id/progress` - Get completion status (login required)
- `POST /api/lessons/:id/progress` - Toggle lesson completion (login required)
- `GET /api/progress` - List all completed lesson IDs for current user (login required)

## AI Prompt System
- **Persona**: "DavOS" — stern, erudite AI tutor; dark academic tone; no cheerleader phrases
- **Direct Hit Rule**: Factual questions get immediate answers in the first sentence
- **Pivot Rule**: Insight/follow-up only after the direct answer
- **Conciseness**: 3-4 sentences max per response
- **Personalization**: DavOS addresses the logged-in user by first name
- **Context limit**: 200K characters max per lesson transcript to stay within Gemini token limits
- **Per-lesson context**: Only the current lesson's transcript is loaded into context, not the entire book
- **Retry logic**: Automatic retry with exponential backoff on 429 rate-limit errors (up to 3 attempts)

## Authentication
- Flask-Login with session-based auth
- Passwords hashed with werkzeug.security
- Login required for lesson pages; landing page is public
- Nav dynamically shows Login/Join or Profile Name/Sign Out based on auth state (fetched via /api/auth/me)

## UI Layout
- **Landing page**: Hero section with course title, module grid with lesson links, auth nav
- **Lesson page**: 3-column layout
  - Left sidebar (260px): Collapsible accordion of modules with lesson links (green checkmarks for completed), auth links
  - Center: Sticky header with lesson/module title, YouTube video embed (if available), scrollable transcript reader
  - Right sidebar (340px): DavOS header, Control Deck (Start Socratic Challenge + Mark Lesson Complete buttons), chat messages, chat input
- **Auth pages**: Centered card forms with Dark Academia styling
- **Profile page**: Avatar initial, account details, active courses list

## Design
Dark Academia aesthetic: deep browns (#1a1410), forest greens, gold accents (#c5a55a), serif fonts (Playfair Display, Merriweather).
