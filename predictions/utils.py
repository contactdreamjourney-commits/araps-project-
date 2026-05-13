from results.models import Result

def predict_next_marks(student_id, subject_id):
    results = Result.objects.filter(student_id=student_id, subject_id=subject_id).order_by('year')
    if results.count() < 2:
        return None
    n = results.count()
    years = [r.year for r in results]
    marks = [r.marks for r in results]
    mean_x = sum(years) / n
    mean_y = sum(marks) / n
    numerator = sum((years[i] - mean_x) * (marks[i] - mean_y) for i in range(n))
    denominator = sum((years[i] - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return None
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    next_year = max(years) + 1
    predicted = slope * next_year + intercept
    return round(predicted, 2)