from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: Literal["admin", "teacher", "student"]


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["student", "teacher"] = "student"
    roll_number: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    enrollment_year: Optional[int] = None
    contact: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class StudentBase(BaseModel):
    roll_number: str
    department: str
    semester: int
    enrollment_year: int
    contact: Optional[str] = None


class StudentCreate(StudentBase):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=6)


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    enrollment_year: Optional[int] = None
    contact: Optional[str] = None


class StudentResponse(StudentBase):
    id: int
    user_id: int
    full_name: str
    email: EmailStr

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    title: str
    code: str
    credit_hours: int
    teacher_id: Optional[int] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    credit_hours: Optional[int] = None
    teacher_id: Optional[int] = None


class CourseResponse(CourseBase):
    id: int
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    student_id: int


class AttendanceCreate(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: Literal["Present", "Absent", "Late"]


class AttendanceUpdate(BaseModel):
    status: Literal["Present", "Absent", "Late"]


class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    date: date
    status: str
    student_name: Optional[str] = None
    course_title: Optional[str] = None

    class Config:
        from_attributes = True

class GradeCreate(BaseModel):
    student_id: int
    course_id: int
    marks: Decimal
    letter_grade: Optional[str] = None
    remarks: Optional[str] = None


class GradeUpdate(BaseModel):
    marks: Optional[Decimal] = None
    letter_grade: Optional[str] = None
    remarks: Optional[str] = None


class GradeResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    marks: Decimal
    letter_grade: Optional[str] = None
    remarks: Optional[str] = None
    course_title: Optional[str] = None
    course_code: Optional[str] = None

    class Config:
        from_attributes = True

class AnnouncementCreate(BaseModel):
    title: str
    body: str


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    body: str
    posted_by: int
    posted_at: datetime
    author_name: Optional[str] = None

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_students: int
    total_courses: int
    total_teachers: int
    total_announcements: int


class StudentDashboard(BaseModel):
    profile: StudentResponse
    enrolled_courses: list[CourseResponse]
    recent_grades: list[GradeResponse]
    attendance_summary: list[dict]
