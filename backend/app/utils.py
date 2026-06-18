from decimal import Decimal
def marks_to_letter_grade(marks: Decimal) -> str:
    score = float(marks)
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 55:
        return "C-"
    if score >= 50:
        return "D"
    return "F"


def get_grade_points(letter_grade: str) -> float:
    grade_points_map = {
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
    return grade_points_map.get(letter_grade or "F", 0.0)


def calculate_gpa(all_grades: list) -> float:
    if not all_grades:
        return 0.0
    total_points = sum(get_grade_points(g.letter_grade) for g in all_grades)
    return round(total_points / len(all_grades), 2)
