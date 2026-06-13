from decimal import Decimal


def marks_to_letter_grade(marks: Decimal) -> str:
    value = float(marks)
    if value >= 90:
        return "A"
    if value >= 85:
        return "A-"
    if value >= 80:
        return "B+"
    if value >= 75:
        return "B"
    if value >= 70:
        return "B-"
    if value >= 65:
        return "C+"
    if value >= 60:
        return "C"
    if value >= 55:
        return "C-"
    if value >= 50:
        return "D"
    return "F"


def grade_point(letter: str) -> float:
    mapping = {
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D": 1.0,
        "F": 0.0,
    }
    return mapping.get(letter or "F", 0.0)


def calculate_gpa(grades: list) -> float:
    if not grades:
        return 0.0
    total = sum(grade_point(g.letter_grade) for g in grades)
    return round(total / len(grades), 2)
