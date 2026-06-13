# Student Management System

**Developer:** Hameem Ahmed | **ID:** F2024408155 | **Course:** Open Source Software Development | **UMT**

Web app to manage students, courses, attendance, grades, and announcements with Admin, Teacher, and Student roles.

> **Presenting to your teacher?** Read [SIMPLE_GUIDE.md](SIMPLE_GUIDE.md) — plain-language explanation of every file.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python + FastAPI |
| Database | SQLite (local) or PostgreSQL (Supabase) |
| Auth | JWT + bcrypt |

## Quick Start

### Backend
```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

### Frontend
```powershell
cd frontend
python -m http.server 5500
```
- App: http://127.0.0.1:5500

### Demo Logins
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@ums.edu | admin123 |
| Teacher | teacher@ums.edu | teacher123 |
| Student | student@ums.edu | student123 |

## Project Structure (Simplified)

```
frontend/           10 HTML pages + css/style.css + js/api.js
backend/app/
  main.py           Starts the server
  routes.py         ALL API endpoints (login, students, courses…)
  auth.py           Password + JWT login
  models.py         Database tables
  schemas.py        Input/output validation
  database.py       DB connection
  config.py         Settings from .env
  utils.py          Grade/GPA helpers
database/schema.sql PostgreSQL schema (for Supabase)
```

## Optional: Supabase + Vercel

1. Run `database/schema.sql` in Supabase SQL Editor
2. Copy connection string into `backend/.env` as `DATABASE_URL`
3. Deploy `frontend/` folder to Vercel (static site)
4. Update `frontend/js/config.js` with your backend URL

## License

Academic project — University of Management and Technology.
