# The Republic - Plato Study Platform

## Overview
A Dark Academia-themed course platform for studying Plato's "The Republic" with an AI-powered tutor (Google Gemini). Users can upload text files (.txt, .md) and interact with an AI that uses uploaded documents as context for scholarly discussions.

## Architecture
- **Backend**: Python Flask (main.py) running on port 5001 internally
- **Proxy**: Node.js Express (server/routes.ts) spawns Flask and proxies all requests from port 5000
- **Database**: PostgreSQL with tables prefixed `py_` (py_courses, py_documents, py_conversations, py_messages)
- **AI**: Google Gemini via `google.generativeai` library, API key from `AI_INTEGRATIONS_GEMINI_API_KEY`
- **Frontend**: Server-rendered Jinja2 templates with vanilla JS, served from templates/ and static/

## Key Files
- `main.py` - Flask application with all API routes and database setup
- `server/routes.ts` - Node.js proxy that spawns Flask and forwards requests
- `templates/base.html` - Base template with nav and toast notifications
- `templates/index.html` - Homepage with course library grid
- `templates/course.html` - Course detail with document upload and conversation management
- `templates/chat.html` - Chat interface for AI tutor conversations
- `static/css/style.css` - Dark Academia theme CSS

## API Routes
- `GET /api/courses` - List all courses
- `GET /api/courses/:id` - Get single course
- `GET /api/courses/:id/documents` - List documents for a course
- `POST /api/documents` - Upload a text file (multipart/form-data)
- `DELETE /api/documents/:id` - Remove a document
- `GET /api/conversations?courseId=` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/:id` - Get conversation with messages
- `POST /api/conversations/:id/messages` - Send message to AI tutor

## Design
Dark Academia aesthetic: deep browns (#1a1410), forest greens, gold accents (#c5a55a), serif fonts (Playfair Display, Merriweather).
