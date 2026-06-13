"""
All API endpoints in one file (login, students, courses, etc.).
Each section is grouped by feature so you can explain it page by page.
"""

from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.database import get_db
from app.models import Announcement, Attendance, Course, Enrollment, Grade, Student, User
from app.schemas import (
    AnnouncementCreate,
    AnnouncementResponse,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceUpdate,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    DashboardStats,
    EnrollmentCreate,
    GradeCreate,
    GradeResponse,
    GradeUpdate,
    StudentCreate,
    StudentDashboard,
    StudentResponse,
    StudentUpdate,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.utils import calculate_gpa, marks_to_letter_grade


# --- Shared helpers (format database rows for JSON responses) ---

def student_json(student: Student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        user_id=student.user_id,
        roll_number=student.roll_number,
        department=student.department,
        semester=student.semester,
        enrollment_year=student.enrollment_year,
        contact=student.contact,
        full_name=student.user.full_name,
        email=student.user.email,
    )


def course_json(course: Course) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        title=course.title,
        code=course.code,
        credit_hours=course.credit_hours,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.full_name if course.teacher else None,
    )


def grade_json(grade: Grade) -> GradeResponse:
    return GradeResponse(
        id=grade.id,
        student_id=grade.student_id,
        course_id=grade.course_id,
        marks=grade.marks,
        letter_grade=grade.letter_grade,
        remarks=grade.remarks,
        course_title=grade.course.title,
        course_code=grade.course.code,
    )


def attendance_json(record: Attendance) -> AttendanceResponse:
    return AttendanceResponse(
        id=record.id,
        student_id=record.student_id,
        course_id=record.course_id,
        date=record.date,
        status=record.status,
        student_name=record.student.user.full_name,
        course_title=record.course.title,
    )


def announcement_json(item: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=item.id,
        title=item.title,
        body=item.body,
        posted_by=item.posted_by,
        posted_at=item.posted_at,
        author_name=item.author.full_name if item.author else None,
    )


def teacher_owns_course(db: Session, teacher_id: int, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Not assigned to this course")
    return course


def attendance_summary_for(student_id: int, db: Session) -> list[dict]:
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    by_course: dict[int, dict] = {}
    for record in records:
        if record.course_id not in by_course:
            by_course[record.course_id] = {
                "course_id": record.course_id,
                "course_title": record.course.title,
                "present": 0,
                "absent": 0,
                "late": 0,
                "total": 0,
            }
        by_course[record.course_id]["total"] += 1
        if record.status == "Present":
            by_course[record.course_id]["present"] += 1
        elif record.status == "Absent":
            by_course[record.course_id]["absent"] += 1
        elif record.status == "Late":
            by_course[record.course_id]["late"] += 1

    summary = []
    for data in by_course.values():
        total = data["total"]
        attended = data["present"] + data["late"]
        percentage = round((attended / total) * 100, 2) if total else 0
        summary.append({**data, "percentage": percentage})
    return summary


# --- Route groups ---

auth = APIRouter(prefix="/api/auth", tags=["Authentication"])
students = APIRouter(prefix="/api/students", tags=["Students"])
courses = APIRouter(prefix="/api/courses", tags=["Courses"])
attendance = APIRouter(prefix="/api/attendance", tags=["Attendance"])
grades = APIRouter(prefix="/api/grades", tags=["Grades"])
dashboard = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
announcements = APIRouter(prefix="/api/announcements", tags=["Announcements"])


# ========== AUTH: login, register, profile ==========

@auth.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role == "student":
        if not all([payload.roll_number, payload.department, payload.semester, payload.enrollment_year]):
            raise HTTPException(
                status_code=400,
                detail="Student registration requires roll_number, department, semester, and enrollment_year",
            )
        if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
            raise HTTPException(status_code=400, detail="Roll number already exists")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()

    if payload.role == "student":
        db.add(
            Student(
                user_id=user.id,
                roll_number=payload.roll_number,
                department=payload.department,
                semester=payload.semester,
                enrollment_year=payload.enrollment_year,
                contact=payload.contact,
            )
        )

    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@auth.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@auth.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ========== STUDENTS ==========

@students.get("", response_model=list[StudentResponse])
def list_students(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    enrollment_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Student).join(User)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(like))
            | (Student.roll_number.ilike(like))
            | (User.email.ilike(like))
        )
    if department:
        query = query.filter(Student.department.ilike(f"%{department}%"))
    if enrollment_year:
        query = query.filter(Student.enrollment_year == enrollment_year)
    return [student_json(s) for s in query.order_by(Student.id).all()]


@students.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return student_json(student)


@students.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
        raise HTTPException(status_code=400, detail="Roll number already exists")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="student",
    )
    db.add(user)
    db.flush()
    student = Student(
        user_id=user.id,
        roll_number=payload.roll_number,
        department=payload.department,
        semester=payload.semester,
        enrollment_year=payload.enrollment_year,
        contact=payload.contact,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student_json(student)


@students.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if payload.email and payload.email != student.user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        student.user.email = payload.email
    if payload.full_name:
        student.user.full_name = payload.full_name
    if payload.roll_number and payload.roll_number != student.roll_number:
        if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
            raise HTTPException(status_code=400, detail="Roll number already exists")
        student.roll_number = payload.roll_number
    if payload.department:
        student.department = payload.department
    if payload.semester is not None:
        student.semester = payload.semester
    if payload.enrollment_year is not None:
        student.enrollment_year = payload.enrollment_year
    if payload.contact is not None:
        student.contact = payload.contact
    db.commit()
    db.refresh(student)
    return student_json(student)


@students.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    user = student.user
    db.delete(student)
    db.delete(user)
    db.commit()


# ========== COURSES ==========

@courses.get("", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Course)
    if current_user.role == "teacher":
        query = query.filter(Course.teacher_id == current_user.id)
    elif current_user.role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            enrolled_ids = [e.course_id for e in db.query(Enrollment).filter(Enrollment.student_id == student.id).all()]
            query = query.filter(Course.id.in_(enrolled_ids)) if enrolled_ids else query.filter(False)
        else:
            query = query.filter(False)
    return [course_json(c) for c in query.order_by(Course.id).all()]


@courses.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course_json(course)


@courses.get("/{course_id}/students", response_model=list[StudentResponse])
def get_course_students(course_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.query(Course).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    return [student_json(e.student) for e in enrollments]


@courses.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Course code already exists")
    if payload.teacher_id:
        if not db.query(User).filter(User.id == payload.teacher_id, User.role == "teacher").first():
            raise HTTPException(status_code=400, detail="Invalid teacher")
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course_json(course)


@courses.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if payload.code and payload.code != course.code:
        if db.query(Course).filter(Course.code == payload.code).first():
            raise HTTPException(status_code=400, detail="Course code already exists")
        course.code = payload.code
    if payload.title:
        course.title = payload.title
    if payload.credit_hours is not None:
        course.credit_hours = payload.credit_hours
    if payload.teacher_id is not None:
        if payload.teacher_id and not db.query(User).filter(User.id == payload.teacher_id, User.role == "teacher").first():
            raise HTTPException(status_code=400, detail="Invalid teacher")
        course.teacher_id = payload.teacher_id
    db.commit()
    db.refresh(course)
    return course_json(course)


@courses.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()


@courses.post("/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
def enroll_student(
    course_id: int,
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if not db.query(Course).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    if not db.query(Student).filter(Student.id == payload.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.student_id == payload.student_id).first():
        raise HTTPException(status_code=400, detail="Student already enrolled")
    db.add(Enrollment(student_id=payload.student_id, course_id=course_id))
    db.commit()
    return {"message": "Student enrolled successfully"}


@courses.delete("/{course_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_enrollment(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    enrollment = db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.student_id == student_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    db.commit()


# ========== ATTENDANCE ==========

@attendance.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    if not db.query(Student).filter(Student.id == payload.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher":
        teacher_owns_course(db, current_user.id, payload.course_id)

    existing = db.query(Attendance).filter(
        Attendance.student_id == payload.student_id,
        Attendance.course_id == payload.course_id,
        Attendance.date == payload.date,
    ).first()
    if existing:
        existing.status = payload.status
        db.commit()
        db.refresh(existing)
        return attendance_json(existing)

    record = Attendance(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return attendance_json(record)


@attendance.get("/{student_id}", response_model=list[AttendanceResponse])
def get_student_attendance(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    records = db.query(Attendance).filter(Attendance.student_id == student_id).order_by(Attendance.date.desc()).all()
    return [attendance_json(r) for r in records]


@attendance.get("/summary/{student_id}")
def attendance_summary(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return attendance_summary_for(student_id, db)


@attendance.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if current_user.role == "teacher":
        teacher_owns_course(db, current_user.id, record.course_id)
    record.status = payload.status
    db.commit()
    db.refresh(record)
    return attendance_json(record)


# ========== GRADES ==========

@grades.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def add_grade(
    payload: GradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    if not db.query(Student).filter(Student.id == payload.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "teacher":
        teacher_owns_course(db, current_user.id, payload.course_id)

    letter = payload.letter_grade or marks_to_letter_grade(payload.marks)
    existing = db.query(Grade).filter(Grade.student_id == payload.student_id, Grade.course_id == payload.course_id).first()
    if existing:
        existing.marks = payload.marks
        existing.letter_grade = letter
        existing.remarks = payload.remarks
        db.commit()
        db.refresh(existing)
        return grade_json(existing)

    grade = Grade(
        student_id=payload.student_id,
        course_id=payload.course_id,
        marks=payload.marks,
        letter_grade=letter,
        remarks=payload.remarks,
    )
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade_json(grade)


@grades.get("/{student_id}", response_model=list[GradeResponse])
def get_student_grades(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return [grade_json(g) for g in db.query(Grade).filter(Grade.student_id == student_id).all()]


@grades.get("/summary/{student_id}")
def grade_summary(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == "student" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    grades_list = db.query(Grade).filter(Grade.student_id == student_id).all()
    return {"grades": [grade_json(g) for g in grades_list], "gpa": calculate_gpa(grades_list)}


@grades.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: int,
    payload: GradeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    if current_user.role == "teacher":
        teacher_owns_course(db, current_user.id, grade.course_id)
    if payload.marks is not None:
        grade.marks = payload.marks
        grade.letter_grade = payload.letter_grade or marks_to_letter_grade(payload.marks)
    elif payload.letter_grade:
        grade.letter_grade = payload.letter_grade
    if payload.remarks is not None:
        grade.remarks = payload.remarks
    db.commit()
    db.refresh(grade)
    return grade_json(grade)


@grades.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(grade_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "teacher"))):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    db.delete(grade)
    db.commit()


# ========== DASHBOARD ==========

@dashboard.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return DashboardStats(
        total_students=db.query(Student).count(),
        total_courses=db.query(Course).count(),
        total_teachers=db.query(User).filter(User.role == "teacher").count(),
        total_announcements=db.query(Announcement).count(),
    )


@dashboard.get("/student", response_model=StudentDashboard)
def get_student_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_roles("student"))):
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    grades_list = db.query(Grade).filter(Grade.student_id == student.id).order_by(Grade.id.desc()).limit(5).all()

    return StudentDashboard(
        profile=student_json(student),
        enrolled_courses=[course_json(e.course) for e in enrollments],
        recent_grades=[grade_json(g) for g in grades_list],
        attendance_summary=attendance_summary_for(student.id, db),
    )


# ========== ANNOUNCEMENTS ==========

@announcements.get("", response_model=list[AnnouncementResponse])
def list_announcements(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = db.query(Announcement).order_by(Announcement.posted_at.desc()).all()
    return [announcement_json(a) for a in items]


@announcements.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    announcement = Announcement(title=payload.title, body=payload.body, posted_by=current_user.id)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement_json(announcement)


@announcements.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "teacher")),
):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if current_user.role == "teacher" and announcement.posted_by != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own announcements")
    db.delete(announcement)
    db.commit()


def register_routes(app: FastAPI) -> None:
    """Connect all API routes to the main app."""
    app.include_router(auth)
    app.include_router(students)
    app.include_router(courses)
    app.include_router(attendance)
    app.include_router(grades)
    app.include_router(dashboard)
    app.include_router(announcements)
