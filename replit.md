# The Republic - Plato Study Platform

## Overview
A Dark Academia-themed course platform for studying Plato's "The Republic" with the "DavOS" AI tutor (Google Gemini). Users can upload text files (.txt, .md) and interact with an AI that uses uploaded documents as context. The AI persona is "DavOS" — inspired by Dr. David Hopkins' Intellectual Freedom Podcast — prioritizing podcast transcripts as primary sources over generic reference texts.

## Architecture
- **Backend**: Python Flask (main.py) running on port 5001 internally
- **Proxy**: Node.js Express (server/routes.ts) spawns Flask and proxies all requests from port 5000
- **Database**: PostgreSQL with tables prefixed `py_` (py_courses, py_modules, py_lessons, py_conversations, py_messages)
- **AI**: Google Gemini via `google.generativeai` library, API key from `AI_INTEGRATIONS_GEMINI_API_KEY`
- **Frontend**: Server-rendered Jinja2 templates with vanilla JS, served from templates/ and static/

## Key Files
- `main.py` - Flask application with all API routes and database setup
- `server/routes.ts` - Node.js proxy that spawns Flask and forwards requests
- `templates/base.html` - Base template with toast notifications
- `templates/index.html` - Landing page with course overview and module grid
- `templates/lesson.html` - 3-column lesson view with sidebar nav, transcript, and DavOS chat
- `static/css/style.css` - Dark Academia theme CSS

## Database Schema
- **py_courses**: id, title, description, cover_image_url
- **py_modules**: id, course_id (FK), title, sort_order — one per Book of The Republic
- **py_lessons**: id, module_id (FK), title, audio_url, transcript_text, summary, sort_order
- **py_conversations**: id, lesson_id (FK), title
- **py_messages**: id, conversation_id (FK), role, content

## API Routes
- `GET /api/courses` - List all courses
- `GET /api/courses/:id` - Get single course
- `GET /api/courses/:id/modules` - List modules with nested lessons
- `GET /api/lessons/:id` - Get lesson with transcript and module/course info
- `GET /api/lessons/:id/conversations` - List conversations for a lesson
- `POST /api/conversations` - Create conversation (JSON: {title, lessonId})
- `GET /api/conversations/:id` - Get conversation with messages
- `POST /api/conversations/:id/messages` - Send message to DavOS AI tutor

## AI Prompt System
- **Persona**: "DavOS" — energetic, intellectually bold AI tutor inspired by Dr. David Hopkins' podcast style
- **Document priority**: Podcast transcripts (titles containing "episode", "davos", or "podcast") are PRIMARY sources; all other documents are SECONDARY reference material
- **Context limit**: 200K characters max per lesson transcript to stay within Gemini token limits
- **Per-lesson context**: Only the current lesson's transcript is loaded into context, not the entire book
- **Retry logic**: Automatic retry with exponential backoff on 429 rate-limit errors (up to 3 attempts)

## UI Layout
- **Landing page**: Hero section with course title, module grid with lesson links
- **Lesson page**: 3-column layout
  - Left sidebar (260px): Collapsible accordion of modules with lesson links
  - Center: Sticky header with lesson/module title, scrollable transcript reader
  - Right sidebar (340px): DavOS chat widget, always open

## Design
Dark Academia aesthetic: deep browns (#1a1410), forest greens, gold accents (#c5a55a), serif fonts (Playfair Display, Merriweather).
