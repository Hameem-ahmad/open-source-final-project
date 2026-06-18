from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_settings
from app.database import Base, SessionLocal, engine
from app.models import Student, User
from app.routes import setup_all_routes

app_settings = load_settings()

app = FastAPI(
    title="Student Management System API",
    description="REST API for students, courses, attendance, grades, and announcements.",
    version="1.0.0",
)
allowed_websites = [
    site.strip()
    for site in app_settings.cors_origins.split(",")
    if site.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_websites if allowed_websites != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
setup_all_routes(app)


def add_demo_users():
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.email == "admin@ums.edu").first()
        if not admin_exists:
            db.add(
                User(
                    full_name="System Administrator",
                    email="admin@ums.edu",
                    password_hash="admin123",
                    role="admin",
                )
            )
        teacher_exists = db.query(User).filter(User.email == "teacher@ums.edu").first()
        if not teacher_exists:
            db.add(
                User(
                    full_name="Demo Teacher",
                    email="teacher@ums.edu",
                    password_hash="teacher123",
                    role="teacher",
                )
            )
        student_exists = db.query(User).filter(User.email == "student@ums.edu").first()
        if not student_exists:
            new_student_user = User(
                full_name="Demo Student",
                email="student@ums.edu",
                password_hash="student123",
                role="student",
            )
            db.add(new_student_user)
            db.flush()

            db.add(
                Student(
                    user_id=new_student_user.id,
                    roll_number="F2024408999",
                    department="Computer Science",
                    semester=4,
                    enrollment_year=2024,
                    contact="03001234567",
                )
            )

        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    """Run when server starts: create tables and demo users."""
    Base.metadata.create_all(bind=engine)
    add_demo_users()


@app.get("/")
def home_page():
    return {
        "message": "Student Management System API",
        "docs": "/docs",
        "student": "Hameem Ahmed",
        "id": "F2024408155",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
