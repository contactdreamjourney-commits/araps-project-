GRADING_SCALE = [
    # (min_percentage, max_percentage, letter_grade, grade_point)
    (90.0, 100.0, 'A', 4.0),
    (80.0, 89.99, 'B+', 3.5),
    (70.0, 79.99, 'B', 3.0),
    (60.0, 69.99, 'C+', 2.5),
    (50.0, 59.99, 'C', 2.0),
    (40.0, 49.99, 'D', 1.0),
    (0.0, 39.99, 'F', 0.0),
]

def get_grade_info(marks):
    """
    Takes a mark percentage and returns a tuple (letter_grade, grade_point).
    """
    if marks is None:
        return ('-', 0.0)
    
    # Clean and convert marks to float
    try:
        val = float(marks)
    except (ValueError, TypeError):
        return ('-', 0.0)
        
    for min_p, max_p, letter, gp in GRADING_SCALE:
        if min_p <= val <= max_p:
            return (letter, gp)
            
    # Fallbacks for out-of-bounds percentages
    if val > 100.0:
        return ('A', 4.0)
    return ('F', 0.0)
