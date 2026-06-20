from results.models import Result

def get_term_offset(term):
    if not term:
        return 0.0
    term_clean = str(term).strip().lower()
    if 'mid' in term_clean or '1st' in term_clean:
        return 0.0
    elif 'final' in term_clean or '2nd' in term_clean:
        return 0.5
    return 0.0


def predict_next_marks(student_id, subject_id):
    results = Result.objects.filter(student_id=student_id, subject_id=subject_id)
    if results.count() < 2:
        return None
    
    data = []
    for r in results:
        offset = get_term_offset(r.term)
        x_val = float(r.year) + offset
        data.append((x_val, r.marks))
        
    # Sort data by chronological X value
    data.sort(key=lambda item: item[0])
    
    # Extract x and y lists
    x_values = [item[0] for item in data]
    marks = [item[1] for item in data]
    
    # Check if all x values are identical
    if len(set(x_values)) < 2:
        return None
        
    n = len(data)
    mean_x = sum(x_values) / n
    mean_y = sum(marks) / n
    
    numerator = sum((x_values[i] - mean_x) * (marks[i] - mean_y) for i in range(n))
    denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
    
    if denominator == 0:
        return None
        
    try:
        slope = numerator / denominator
        intercept = mean_y - slope * mean_x
        next_x = max(x_values) + 0.5
        predicted = slope * next_x + intercept
        
        # Clip prediction between 0 and 100 as marks are percentages
        predicted = max(0.0, min(100.0, predicted))
        return round(predicted, 2)
    except ZeroDivisionError:
        return None

def get_subject_trend(results):
    if results.count() < 2:
        return "Not enough data yet"
    
    data = []
    for r in results:
        offset = get_term_offset(r.term)
        x_val = float(r.year) + offset
        data.append((x_val, r.marks))
        
    data.sort(key=lambda item: item[0])
    
    x_values = [item[0] for item in data]
    marks = [item[1] for item in data]
    
    n = len(data)
    mean_x = sum(x_values) / n
    mean_y = sum(marks) / n
    
    numerator = sum((x_values[i] - mean_x) * (marks[i] - mean_y) for i in range(n))
    denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
    
    if denominator == 0:
        diff = marks[-1] - marks[0]
        if diff > 1:
            return "Improving"
        elif diff < -1:
            return "Declining"
        else:
            return "Stable"
            
    slope = numerator / denominator
    if slope > 0.5:
        return "Improving"
    elif slope < -0.5:
        return "Declining"
    else:
        return "Stable"