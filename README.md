# Student Management System

Developer: Hameem Ahmed  ID: F2024408155  Course: Open Source Software Development  

Web app to manage students, courses, attendance, grades, and announcements with Admin, Teacher, and Student roles.



 

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python + FastAPI |
| Database | SQLite (local) or PostgreSQL (Supabase) |
| Auth | JWT + bcrypt |


 Backend
powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000


- Docs: https://student-management-api-production-a951.up.railway.app/docs

 Frontend
powershell
cd frontend
python -m http.server 5500

- App: https://open-source-final-project.vercel.app/

 Demo Logins
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@ums.edu | admin123 |
| Teacher | teacher@ums.edu | teacher123 |
| Student | student@ums.edu | student123 |

 Project Structure 


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



