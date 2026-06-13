# How to Explain This Project to Your Teacher

**Student:** Hameem Ahmed | **ID:** F2024408155 | **Course:** Open Source Software Development

---

## 1. What does this project do? (30 seconds)

A **Student Management System** for a university. It lets:

- **Admin** — manage students, courses, view dashboard
- **Teacher** — mark attendance, enter grades, post announcements
- **Student** — view profile, grades, attendance, announcements

---

## 2. How is it built? (3 parts only)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  FRONTEND   │ ───► │   BACKEND   │ ───► │  DATABASE   │
│  (Browser)  │      │  (Python)   │      │  (SQLite)   │
│  HTML + JS  │      │  FastAPI    │      │  .db file   │
└─────────────┘      └─────────────┘      └─────────────┘
   frontend/            backend/         student_management.db
```

| Part | Folder | Technology | What it does |
|------|--------|------------|--------------|
| Frontend | `frontend/` | HTML, CSS, JavaScript | Pages the user sees and clicks |
| Backend | `backend/` | Python + FastAPI | Handles login, saves data, returns JSON |
| Database | `backend/student_management.db` | SQLite | Stores users, students, courses, etc. |

---

## 3. Backend files — what to say about each

Only **8 Python files** matter:

| File | One-line explanation |
|------|---------------------|
| `main.py` | Starts the server |
| `routes.py` | **All API URLs** (login, students, courses, etc.) |
| `auth.py` | Password hashing + JWT login tokens |
| `models.py` | Database table definitions (User, Student, Course…) |
| `schemas.py` | Validates data coming in/out (email format, required fields) |
| `database.py` | Connects to the database |
| `config.py` | Reads settings from `.env` file |
| `utils.py` | Converts marks to letter grades and GPA |

**Key point for teacher:** All API endpoints are in **one file** — `routes.py` — grouped by feature (Auth, Students, Courses…).

---

## 4. Frontend files — what to say about each

| File | Purpose |
|------|---------|
| `index.html`, `about.html` | Public pages |
| `login.html` | Login + registration |
| `dashboard.html` | Admin home |
| `students.html`, `courses.html` | Admin CRUD |
| `attendance.html`, `grades.html` | Teacher tools |
| `profile.html` | Student dashboard |
| `announcements.html` | News/announcements |
| `js/api.js` | Sends requests to Python backend (not a second API!) |
| `js/config.js` | Backend URL (`http://127.0.0.1:8000`) |
| `css/style.css` | All styling |

---

## 5. How login works (easy to demo)

1. User enters email + password on `login.html`
2. Frontend sends `POST /api/auth/login` to Python
3. Python checks password (bcrypt hash) in database
4. Python returns a **JWT token** (like a temporary ID card)
5. Frontend saves token in browser storage
6. Every next request sends: `Authorization: Bearer <token>`
7. Python checks token → allows or blocks access

**Demo accounts (created automatically):**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@ums.edu | admin123 |
| Teacher | teacher@ums.edu | teacher123 |
| Student | student@ums.edu | student123 |

---

## 6. Database tables (7 tables)

| Table | Stores |
|-------|--------|
| `users` | Login accounts (admin/teacher/student) |
| `students` | Student details (roll number, department…) |
| `courses` | Course list |
| `enrollments` | Which student is in which course |
| `attendance` | Present/Absent/Late per day |
| `grades` | Marks and letter grades |
| `announcements` | News posted by admin/teacher |

Schema file: `database/schema.sql` (for Supabase/PostgreSQL if deploying online)

---

## 7. How to run (for live demo)

**Terminal 1 — Backend:**
```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
Open http://127.0.0.1:8000/docs to show all API endpoints.

**Terminal 2 — Frontend:**
```powershell
cd frontend
python -m http.server 5500
```
Open http://127.0.0.1:5500 and log in as admin.

---

## 8. Demo script (5 minutes)

1. Show **Swagger docs** at `/docs` — "This is our REST API with 30 endpoints"
2. Login as **admin** → show dashboard stats
3. Open **Students** → add or search a student
4. Open **Courses** → create a course, enroll a student
5. Login as **teacher** → mark attendance, add a grade
6. Login as **student** → show profile with grades and attendance

---

## 9. Tech stack (one sentence each)

- **HTML/CSS/JS** — frontend (no React, kept simple)
- **FastAPI** — modern Python web framework for APIs
- **SQLAlchemy** — talks to the database using Python classes
- **JWT + bcrypt** — secure login
- **SQLite** — local database file (no server setup needed)
- **Supabase** (optional) — cloud PostgreSQL for deployment
- **Vercel** (optional) — hosts the frontend HTML files online

---

## 10. Common teacher questions

**Q: Why FastAPI and not plain PHP?**  
A: FastAPI auto-generates API docs, validates data, and is industry-standard for Python APIs.

**Q: What is JWT?**  
A: A signed token that proves the user logged in, without storing session on server.

**Q: What are roles?**  
A: Admin can do everything. Teacher can mark attendance/grades. Student can only see their own data.

**Q: Where is the API?**  
A: In `backend/app/routes.py` — one file, clearly labeled sections.

**Q: What is `api.js`?**  
A: Frontend code that **calls** the Python API. It is not a second backend.

---

## Project folder map (simplified)

```
os student managemt/
├── frontend/          ← 10 HTML pages + CSS + JS
├── backend/
│   └── app/
│       ├── main.py    ← Start here
│       ├── routes.py  ← All API endpoints
│       ├── auth.py    ← Login logic
│       ├── models.py  ← Database tables
│       ├── schemas.py ← Data validation
│       ├── database.py
│       ├── config.py
│       └── utils.py
├── database/
│   └── schema.sql     ← SQL for Supabase (optional)
├── SIMPLE_GUIDE.md    ← This file
└── README.md          ← Setup instructions
```
