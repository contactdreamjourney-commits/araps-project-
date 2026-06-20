from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db import transaction
from students.models import Student
from results.models import Subject, Result, Notification
import pandas as pd
import csv

def is_teacher(user):
    return user.groups.filter(name='Teacher').exists()

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def teacher_dashboard(request):
    students = Student.objects.all()
    subjects = Subject.objects.all()
    results = Result.objects.all().select_related('student', 'subject')
    
    # 1. Selectors for analytics
    analytics_subjects = Subject.objects.all()
    analytics_terms = Result.objects.values_list('term', flat=True).distinct()
    analytics_years = Result.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    # 2. Defaults
    default_subject = Subject.objects.first()
    default_term = "Final"
    default_year = 2024
    
    latest_result = Result.objects.order_by('-year', '-id').first()
    if latest_result:
        default_subject = latest_result.subject
        default_term = latest_result.term
        default_year = latest_result.year
        
    # Get parameters
    sel_subject_id = request.GET.get('analytics_subject', str(default_subject.id) if default_subject else "")
    sel_term = request.GET.get('analytics_term', default_term)
    sel_year = request.GET.get('analytics_year', str(default_year))
    
    try:
        sel_year_int = int(sel_year)
    except (ValueError, TypeError):
        sel_year_int = default_year
        
    # Filter results for cohort
    cohort_results = Result.objects.filter(
        subject_id=sel_subject_id,
        term=sel_term,
        year=sel_year_int
    ).select_related('student')
    
    # Average mark
    from django.db.models import Avg
    class_average = cohort_results.aggregate(Avg('marks'))['marks__avg'] or 0.0
    class_average = round(class_average, 1)
    
    # Prepare data for Chart.js
    chart_labels = [r.student.name for r in cohort_results]
    chart_marks = [r.marks for r in cohort_results]
    
    # Top 3 / Bottom 3 performers
    student_averages = Student.objects.annotate(avg_marks=Avg('result__marks')).filter(avg_marks__isnull=False)
    top_performers = student_averages.order_by('-avg_marks')[:3]
    bottom_performers = student_averages.order_by('avg_marks')[:3]

    if request.method == 'POST':
        student_id = request.POST.get('student')
        subject_id = request.POST.get('subject')
        marks = request.POST.get('marks')
        term = request.POST.get('term')
        year = request.POST.get('year', 2025)
        Result.objects.create(
            student_id=student_id,
            subject_id=subject_id,
            marks=marks,
            term=term,
            year=year
        )
        return redirect('teacher_dashboard')
        
    return render(request, 'teachers/dashboard.html', {
        'students': students,
        'subjects': subjects,
        'results': results,
        'analytics_subjects': analytics_subjects,
        'analytics_terms': analytics_terms,
        'analytics_years': analytics_years,
        'sel_subject_id': sel_subject_id,
        'sel_term': sel_term,
        'sel_year': sel_year,
        'class_average': class_average,
        'chart_labels': chart_labels,
        'chart_marks': chart_marks,
        'top_performers': top_performers,
        'bottom_performers': bottom_performers,
    })

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def edit_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    if request.method == 'POST':
        result.marks = request.POST.get('marks')
        result.term = request.POST.get('term')
        result.year = request.POST.get('year')
        result.save()
        return redirect('teacher_dashboard')
    students = Student.objects.all()
    subjects = Subject.objects.all()
    return render(request, 'teachers/edit_result.html', {'result': result, 'students': students, 'subjects': subjects})

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def delete_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    if request.method == 'POST':
        result.delete()
        return redirect('teacher_dashboard')
    return render(request, 'teachers/delete_result.html', {'result': result})

from django.utils.timezone import localdate
import datetime
from attendance.models import Attendance
from results.models import AuditLog

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def mark_attendance(request):
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = localdate()
    else:
        selected_date = localdate()

    students = Student.objects.all().order_by('roll_no')
    
    # Load existing attendance for this date
    existing_attendance = Attendance.objects.filter(date=selected_date)
    attendance_map = {att.student_id: att.status for att in existing_attendance}

    if request.method == 'POST':
        present_count = 0
        absent_count = 0
        for student in students:
            # Check form input for this student
            status = request.POST.get(f'status_{student.id}', 'Absent')
            if status not in ['Present', 'Absent']:
                status = 'Absent'
            
            # Save or update attendance record
            Attendance.objects.update_or_create(
                student=student,
                date=selected_date,
                defaults={'status': status}
            )
            if status == 'Present':
                present_count += 1
            else:
                absent_count += 1

        # Log activity in AuditLog
        AuditLog.objects.create(
            user=request.user,
            action="Attendance Marked",
            details=f"Attendance marked for date {selected_date}. Present: {present_count}, Absent: {absent_count}."
        )
        return redirect(f'/teacher/attendance/?date={selected_date}')
        
    student_list = []
    for student in students:
        student_list.append({
            'id': student.id,
            'name': student.name,
            'roll_no': student.roll_no,
            'status': attendance_map.get(student.id, 'Present')
        })

    return render(request, 'teachers/attendance.html', {
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'students': student_list,
    })

@login_required
@user_passes_test(is_teacher, login_url='/login/')
def teacher_import_results(request):
    errors = []
    success_message = None
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        try:
            if file_name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif file_name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(uploaded_file)
            else:
                errors.append("Invalid file format. Please upload a CSV or Excel (.xlsx/.xls) file.")
                return render(request, 'teachers/bulk_import.html', {'errors': errors})
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            return render(request, 'teachers/bulk_import.html', {'errors': errors})

        # Required columns
        required_cols = {'subject', 'term', 'year', 'marks'}
        col_set = set(df.columns)
        has_roll = 'student_roll_no' in col_set
        has_user = 'username' in col_set

        if not (has_roll or has_user):
            errors.append("Missing identifier column: file must contain either 'student_roll_no' or 'username'.")
        missing_other = required_cols - col_set
        if missing_other:
            errors.append(f"Missing required columns: {', '.join(missing_other)}")

        if errors:
            return render(request, 'teachers/bulk_import.html', {'errors': errors})

        records_to_process = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            
            student_obj = None
            if has_roll:
                roll_val = str(row.get('student_roll_no', '')).strip() if pd.notna(row.get('student_roll_no')) else ''
                if roll_val and roll_val.lower() != 'nan':
                    try:
                        student_obj = Student.objects.get(roll_no=roll_val)
                    except Student.DoesNotExist:
                        errors.append(f"Row {row_num}: Student with roll number '{roll_val}' not found.")
                else:
                    errors.append(f"Row {row_num}: Student roll number cannot be blank.")
            else:
                user_val = str(row.get('username', '')).strip() if pd.notna(row.get('username')) else ''
                if user_val and user_val.lower() != 'nan':
                    try:
                        student_obj = Student.objects.get(user__username=user_val)
                    except Student.DoesNotExist:
                        errors.append(f"Row {row_num}: Student with username '{user_val}' not found.")
                else:
                    errors.append(f"Row {row_num}: Student username cannot be blank.")

            sub_val = str(row.get('subject', '')).strip() if pd.notna(row.get('subject')) else ''
            subject_obj = None
            if sub_val and sub_val.lower() != 'nan':
                try:
                    subject_obj = Subject.objects.get(name__iexact=sub_val)
                except Subject.DoesNotExist:
                    errors.append(f"Row {row_num}: Subject '{sub_val}' not found.")
            else:
                errors.append(f"Row {row_num}: Subject cannot be blank.")

            term_val = str(row.get('term', '')).strip() if pd.notna(row.get('term')) else ''
            if not term_val or term_val.lower() == 'nan':
                errors.append(f"Row {row_num}: Term cannot be blank.")
            elif term_val.lower() not in ['mid', 'final', 'mid-term', 'final-term']:
                errors.append(f"Row {row_num}: Term must be either 'Mid' or 'Final'.")
            else:
                if term_val.lower() == 'mid-term':
                    term_val = 'Mid'
                elif term_val.lower() == 'final-term':
                    term_val = 'Final'
                else:
                    term_val = term_val.capitalize()

            year_val = row.get('year')
            year_int = None
            if pd.isna(year_val):
                errors.append(f"Row {row_num}: Year cannot be blank.")
            else:
                try:
                    year_int = int(year_val)
                    if year_int < 1900 or year_int > 2100:
                        errors.append(f"Row {row_num}: Year '{year_int}' is out of range.")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num}: Invalid year '{year_val}'.")

            marks_val = row.get('marks')
            marks_float = None
            if pd.isna(marks_val):
                errors.append(f"Row {row_num}: Marks cannot be blank.")
            else:
                try:
                    marks_float = float(marks_val)
                    if marks_float < 0.0 or marks_float > 100.0:
                        errors.append(f"Row {row_num}: Marks '{marks_float}' must be between 0 and 100.")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num}: Invalid marks value '{marks_val}'.")

            if student_obj and subject_obj and term_val and year_int is not None and marks_float is not None:
                records_to_process.append({
                    'student': student_obj,
                    'subject': subject_obj,
                    'term': term_val,
                    'year': year_int,
                    'marks': marks_float
                })

        if not errors:
            try:
                with transaction.atomic():
                    for rec in records_to_process:
                        result_obj, created = Result.objects.update_or_create(
                            student=rec['student'],
                            subject=rec['subject'],
                            term=rec['term'],
                            year=rec['year'],
                            defaults={'marks': rec['marks']}
                        )
                        Notification.objects.create(
                            recipient=rec['student'].user,
                            message=f"Your {rec['term']} term result for {rec['subject'].name} ({rec['year']}) has been uploaded/updated: {rec['marks']}% ({result_obj.letter_grade})."
                        )
                success_message = f"Successfully imported {len(records_to_process)} results."
            except Exception as e:
                errors.append(f"Database error during import: {e}")

    return render(request, 'teachers/bulk_import.html', {'errors': errors, 'success_message': success_message})

def download_results_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="results_template.csv"'
    writer = csv.writer(response)
    writer.writerow(['student_roll_no', 'subject', 'term', 'year', 'marks'])
    writer.writerow(['21801401', 'Programming Fundamentals', 'Mid', '2024', '85.5'])
    writer.writerow(['21801402', 'Programming Fundamentals', 'Final', '2024', '92.0'])
    return response