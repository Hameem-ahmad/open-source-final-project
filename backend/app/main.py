from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import hash_password
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Student, User
from app.routes import register_routes

settings = get_settings()

app = FastAPI(
    title="Student Management System API",
    description="REST API for students, courses, attendance, grades, and announcements.",
    version="1.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app)


def seed_default_users():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@ums.edu").first():
            db.add(
                User(
                    full_name="System Administrator",
                    email="admin@ums.edu",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )

        if not db.query(User).filter(User.email == "teacher@ums.edu").first():
            db.add(
                User(
                    full_name="Demo Teacher",
                    email="teacher@ums.edu",
                    password_hash=hash_password("teacher123"),
                    role="teacher",
                )
            )

        if not db.query(User).filter(User.email == "student@ums.edu").first():
            student_user = User(
                full_name="Demo Student",
                email="student@ums.edu",
                password_hash=hash_password("student123"),
                role="student",
            )
            db.add(student_user)
            db.flush()
            db.add(
                Student(
                    user_id=student_user.id,
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
    Base.metadata.create_all(bind=engine)
    seed_default_users()


@app.get("/")
def root():
    return {
        "message": "Student Management System API",
        "docs": "/docs",
        "student": "Hameem Ahmed",
        "id": "F2024408155",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
