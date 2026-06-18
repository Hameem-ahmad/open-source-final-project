from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import (
    check_password,
    get_logged_in_user,
    make_login_token,
    must_be_role,
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
def make_student_response(student: Student) -> StudentResponse:
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


def make_course_response(course: Course) -> CourseResponse:
    teacher_name = course.teacher.full_name if course.teacher else None
    return CourseResponse(
        id=course.id,
        title=course.title,
        code=course.code,
        credit_hours=course.credit_hours,
        teacher_id=course.teacher_id,
        teacher_name=teacher_name,
    )


def make_grade_response(grade: Grade) -> GradeResponse:
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


def make_attendance_response(record: Attendance) -> AttendanceResponse:
    return AttendanceResponse(
        id=record.id,
        student_id=record.student_id,
        course_id=record.course_id,
        date=record.date,
        status=record.status,
        student_name=record.student.user.full_name,
        course_title=record.course.title,
    )


def make_announcement_response(item: Announcement) -> AnnouncementResponse:
    author_name = item.author.full_name if item.author else None
    return AnnouncementResponse(
        id=item.id,
        title=item.title,
        body=item.body,
        posted_by=item.posted_by,
        posted_at=item.posted_at,
        author_name=author_name,
    )


def check_teacher_has_course(db: Session, teacher_id: int, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Not assigned to this course")
    return course


def get_attendance_summary(student_id: int, db: Session) -> list[dict]:
    all_records = db.query(Attendance).filter(Attendance.student_id == student_id).all()

    summary_by_course = {}
    for record in all_records:
        course_id = record.course_id
        if course_id not in summary_by_course:
            summary_by_course[course_id] = {
                "course_id": course_id,
                "course_title": record.course.title,
                "present": 0,
                "absent": 0,
                "late": 0,
                "total": 0,
            }

        summary_by_course[course_id]["total"] += 1
        if record.status == "Present":
            summary_by_course[course_id]["present"] += 1
        elif record.status == "Absent":
            summary_by_course[course_id]["absent"] += 1
        elif record.status == "Late":
            summary_by_course[course_id]["late"] += 1

    result = []
    for course_data in summary_by_course.values():
        total_days = course_data["total"]
        days_attended = course_data["present"] + course_data["late"]
        if total_days > 0:
            percentage = round((days_attended / total_days) * 100, 2)
        else:
            percentage = 0
        result.append({**course_data, "percentage": percentage})
    return result

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
students_router = APIRouter(prefix="/api/students", tags=["Students"])
courses_router = APIRouter(prefix="/api/courses", tags=["Courses"])
attendance_router = APIRouter(prefix="/api/attendance", tags=["Attendance"])
grades_router = APIRouter(prefix="/api/grades", tags=["Grades"])
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
announcements_router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    email_taken = db.query(User).filter(User.email == data.email).first()
    if email_taken:
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.role == "student":
        missing_fields = not all([
            data.roll_number,
            data.department,
            data.semester,
            data.enrollment_year,
        ])
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail="Student registration requires roll_number, department, semester, and enrollment_year",
            )
        roll_taken = db.query(Student).filter(Student.roll_number == data.roll_number).first()
        if roll_taken:
            raise HTTPException(status_code=400, detail="Roll number already exists")

    new_user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=data.password,
        role=data.role,
    )
    db.add(new_user)
    db.flush()

    if data.role == "student":
        db.add(
            Student(
                user_id=new_user.id,
                roll_number=data.roll_number,
                department=data.department,
                semester=data.semester,
                enrollment_year=data.enrollment_year,
                contact=data.contact,
            )
        )

    db.commit()
    db.refresh(new_user)
    token = make_login_token(new_user.id, new_user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(new_user))


@auth_router.post("/login", response_model=TokenResponse)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    password_ok = user and check_password(data.password, user.password_hash)
    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = make_login_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@auth_router.get("/me", response_model=UserResponse)
def get_my_profile(logged_in_user: User = Depends(get_logged_in_user)):
    return logged_in_user


# ==================== STUDENTS ====================

@students_router.get("", response_model=list[StudentResponse])
def get_all_students(
    search: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    enrollment_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    db_query = db.query(Student).join(User)

    if search:
        search_text = f"%{search}%"
        db_query = db_query.filter(
            (User.full_name.ilike(search_text))
            | (Student.roll_number.ilike(search_text))
            | (User.email.ilike(search_text))
        )
    if department:
        db_query = db_query.filter(Student.department.ilike(f"%{department}%"))
    if enrollment_year:
        db_query = db_query.filter(Student.enrollment_year == enrollment_year)

    all_students = db_query.order_by(Student.id).all()
    return [make_student_response(s) for s in all_students]


@students_router.get("/{student_id}", response_model=StudentResponse)
def get_one_student(
    student_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if logged_in_user.role == "student" and student.user_id != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return make_student_response(student)


@students_router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def add_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.query(Student).filter(Student.roll_number == data.roll_number).first():
        raise HTTPException(status_code=400, detail="Roll number already exists")

    new_user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=data.password,
        role="student",
    )
    db.add(new_user)
    db.flush()

    new_student = Student(
        user_id=new_user.id,
        roll_number=data.roll_number,
        department=data.department,
        semester=data.semester,
        enrollment_year=data.enrollment_year,
        contact=data.contact,
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return make_student_response(new_student)


@students_router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if data.email and data.email != student.user.email:
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        student.user.email = data.email
    if data.full_name:
        student.user.full_name = data.full_name
    if data.roll_number and data.roll_number != student.roll_number:
        if db.query(Student).filter(Student.roll_number == data.roll_number).first():
            raise HTTPException(status_code=400, detail="Roll number already exists")
        student.roll_number = data.roll_number
    if data.department:
        student.department = data.department
    if data.semester is not None:
        student.semester = data.semester
    if data.enrollment_year is not None:
        student.enrollment_year = data.enrollment_year
    if data.contact is not None:
        student.contact = data.contact

    db.commit()
    db.refresh(student)
    return make_student_response(student)


@students_router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    user_account = student.user
    db.delete(student)
    db.delete(user_account)
    db.commit()

@courses_router.get("", response_model=list[CourseResponse])
def get_all_courses(
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    db_query = db.query(Course)

    if logged_in_user.role == "teacher":
        db_query = db_query.filter(Course.teacher_id == logged_in_user.id)
    elif logged_in_user.role == "student":
        student = db.query(Student).filter(Student.user_id == logged_in_user.id).first()
        if student:
            enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
            course_ids = [e.course_id for e in enrollments]
            if course_ids:
                db_query = db_query.filter(Course.id.in_(course_ids))
            else:
                db_query = db_query.filter(False)
        else:
            db_query = db_query.filter(False)

    all_courses = db_query.order_by(Course.id).all()
    return [make_course_response(c) for c in all_courses]


@courses_router.get("/{course_id}", response_model=CourseResponse)
def get_one_course(
    course_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return make_course_response(course)


@courses_router.get("/{course_id}/students", response_model=list[StudentResponse])
def get_students_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    return [make_student_response(e.student) for e in enrollments]


@courses_router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def add_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    if db.query(Course).filter(Course.code == data.code).first():
        raise HTTPException(status_code=400, detail="Course code already exists")
    if data.teacher_id:
        teacher = db.query(User).filter(User.id == data.teacher_id, User.role == "teacher").first()
        if not teacher:
            raise HTTPException(status_code=400, detail="Invalid teacher")

    new_course = Course(
        title=data.title,
        code=data.code,
        credit_hours=data.credit_hours,
        teacher_id=data.teacher_id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return make_course_response(new_course)


@courses_router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if data.code and data.code != course.code:
        if db.query(Course).filter(Course.code == data.code).first():
            raise HTTPException(status_code=400, detail="Course code already exists")
        course.code = data.code
    if data.title:
        course.title = data.title
    if data.credit_hours is not None:
        course.credit_hours = data.credit_hours
    if data.teacher_id is not None:
        if data.teacher_id:
            teacher = db.query(User).filter(User.id == data.teacher_id, User.role == "teacher").first()
            if not teacher:
                raise HTTPException(status_code=400, detail="Invalid teacher")
        course.teacher_id = data.teacher_id

    db.commit()
    db.refresh(course)
    return make_course_response(course)


@courses_router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()


@courses_router.post("/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
def enroll_student_in_course(
    course_id: int,
    data: EnrollmentCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    already_enrolled = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.student_id == data.student_id,
    ).first()
    if already_enrolled:
        raise HTTPException(status_code=400, detail="Student already enrolled")

    db.add(Enrollment(student_id=data.student_id, course_id=course_id))
    db.commit()
    return {"message": "Student enrolled successfully"}


@courses_router.delete("/{course_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_from_course(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.student_id == student_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    db.commit()

@attendance_router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if logged_in_user.role == "teacher":
        check_teacher_has_course(db, logged_in_user.id, data.course_id)

    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.course_id == data.course_id,
        Attendance.date == data.date,
    ).first()

    if existing:
        existing.status = data.status
        db.commit()
        db.refresh(existing)
        return make_attendance_response(existing)

    new_record = Attendance(
        student_id=data.student_id,
        course_id=data.course_id,
        date=data.date,
        status=data.status,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return make_attendance_response(new_record)


@attendance_router.get("/{student_id}", response_model=list[AttendanceResponse])
def get_student_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if logged_in_user.role == "student" and student.user_id != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    records = db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).order_by(Attendance.date.desc()).all()
    return [make_attendance_response(r) for r in records]


@attendance_router.get("/summary/{student_id}")
def attendance_summary(
    student_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if logged_in_user.role == "student" and student.user_id != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return get_attendance_summary(student_id, db)


@attendance_router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: int,
    data: AttendanceUpdate,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    if logged_in_user.role == "teacher":
        check_teacher_has_course(db, logged_in_user.id, record.course_id)

    record.status = data.status
    db.commit()
    db.refresh(record)
    return make_attendance_response(record)

@grades_router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def add_grade(
    data: GradeCreate,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    """Add or update marks for a student in a course."""
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if logged_in_user.role == "teacher":
        check_teacher_has_course(db, logged_in_user.id, data.course_id)

    letter_grade = data.letter_grade or marks_to_letter_grade(data.marks)

    existing = db.query(Grade).filter(
        Grade.student_id == data.student_id,
        Grade.course_id == data.course_id,
    ).first()

    if existing:
        existing.marks = data.marks
        existing.letter_grade = letter_grade
        existing.remarks = data.remarks
        db.commit()
        db.refresh(existing)
        return make_grade_response(existing)

    new_grade = Grade(
        student_id=data.student_id,
        course_id=data.course_id,
        marks=data.marks,
        letter_grade=letter_grade,
        remarks=data.remarks,
    )
    db.add(new_grade)
    db.commit()
    db.refresh(new_grade)
    return make_grade_response(new_grade)


@grades_router.get("/{student_id}", response_model=list[GradeResponse])
def get_student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if logged_in_user.role == "student" and student.user_id != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    all_grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    return [make_grade_response(g) for g in all_grades]


@grades_router.get("/summary/{student_id}")
def grade_summary(
    student_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if logged_in_user.role == "student" and student.user_id != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    all_grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    return {
        "grades": [make_grade_response(g) for g in all_grades],
        "gpa": calculate_gpa(all_grades),
    }


@grades_router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: int,
    data: GradeUpdate,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")

    if logged_in_user.role == "teacher":
        check_teacher_has_course(db, logged_in_user.id, grade.course_id)

    if data.marks is not None:
        grade.marks = data.marks
        grade.letter_grade = data.letter_grade or marks_to_letter_grade(data.marks)
    elif data.letter_grade:
        grade.letter_grade = data.letter_grade
    if data.remarks is not None:
        grade.remarks = data.remarks

    db.commit()
    db.refresh(grade)
    return make_grade_response(grade)


@grades_router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    db.delete(grade)
    db.commit()

@dashboard_router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(must_be_role("admin")),
):
    """Admin dashboard: total counts."""
    return DashboardStats(
        total_students=db.query(Student).count(),
        total_courses=db.query(Course).count(),
        total_teachers=db.query(User).filter(User.role == "teacher").count(),
        total_announcements=db.query(Announcement).count(),
    )


@dashboard_router.get("/student", response_model=StudentDashboard)
def get_student_dashboard(
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("student")),
):
    """Student dashboard: profile, courses, grades, attendance."""
    student = db.query(Student).filter(Student.user_id == logged_in_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    recent_grades = db.query(Grade).filter(
        Grade.student_id == student.id
    ).order_by(Grade.id.desc()).limit(5).all()

    return StudentDashboard(
        profile=make_student_response(student),
        enrolled_courses=[make_course_response(e.course) for e in enrollments],
        recent_grades=[make_grade_response(g) for g in recent_grades],
        attendance_summary=get_attendance_summary(student.id, db),
    )

@announcements_router.get("", response_model=list[AnnouncementResponse])
def get_all_announcements(
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(get_logged_in_user),
):
    items = db.query(Announcement).order_by(Announcement.posted_at.desc()).all()
    return [make_announcement_response(a) for a in items]


@announcements_router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def post_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    new_announcement = Announcement(
        title=data.title,
        body=data.body,
        posted_by=logged_in_user.id,
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return make_announcement_response(new_announcement)


@announcements_router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    logged_in_user: User = Depends(must_be_role("admin", "teacher")),
):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if logged_in_user.role == "teacher" and announcement.posted_by != logged_in_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own announcements")

    db.delete(announcement)
    db.commit()


def setup_all_routes(app: FastAPI) -> None:
    """Connect all routers to the main FastAPI app."""
    app.include_router(auth_router)
    app.include_router(students_router)
    app.include_router(courses_router)
    app.include_router(attendance_router)
    app.include_router(grades_router)
    app.include_router(dashboard_router)
    app.include_router(announcements_router)
