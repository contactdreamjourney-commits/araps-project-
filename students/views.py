from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from .models import Student
from results.models import Result, Subject, Notification
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.models import User, Group
from django.db import transaction
from attendance.models import Attendance
from predictions.utils import predict_next_marks, get_subject_trend, get_term_offset
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from io import BytesIO
import json
import pandas as pd
import csv

@login_required
def dashboard(request):
    overall_gpa = None
    term_gpa = None
    latest_term_name = "N/A"
    try:
        student = Student.objects.get(user=request.user)
        # Group by subject and sort chronologically within subject
        results = Result.objects.filter(student=student).order_by('subject__name', 'year')
        results_with_pred = []
        for result in results:
            pred = predict_next_marks(student.id, result.subject.id)
            sub_results = Result.objects.filter(student=student, subject=result.subject)
            trend = get_subject_trend(sub_results)
            results_with_pred.append({
                'subject': result.subject.name,
                'marks': result.marks,
                'grade': result.letter_grade,
                'term': result.term,
                'year': result.year,
                'predicted': pred if pred else None,
                'trend': trend
            })
        
        # GPA Calculation
        if results.exists():
            total_gp = sum(r.grade_point for r in results)
            overall_gpa = round(total_gp / results.count(), 2)
            
            max_val = -1
            latest_res = None
            for r in results:
                val = float(r.year) + get_term_offset(r.term)
                if val > max_val:
                    max_val = val
                    latest_res = r
            
            if latest_res:
                latest_term_name = f"{latest_res.term} {latest_res.year}"
                term_results = results.filter(year=latest_res.year, term=latest_res.term)
                term_gps = [r.grade_point for r in term_results]
                if term_gps:
                    term_gpa = round(sum(term_gps) / len(term_gps), 2)
        
        # Group chart data by unique subject name showing the latest result
        subject_latest = {}
        for r in results_with_pred:
            sub_name = r['subject']
            offset = get_term_offset(r['term'])
            x_val = float(r['year']) + offset
            if sub_name not in subject_latest or x_val > subject_latest[sub_name]['x_val']:
                subject_latest[sub_name] = {
                    'marks': r['marks'],
                    'predicted': r['predicted'],
                    'x_val': x_val
                }
        
        sorted_subjects = sorted(subject_latest.keys())
        chart_data = {
            'labels': sorted_subjects,
            'marks': [subject_latest[s]['marks'] for s in sorted_subjects],
            'predicted': [subject_latest[s]['predicted'] for s in sorted_subjects]
        }
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        # Fetch student attendance
        attendance_records = Attendance.objects.filter(student=student).order_by('-date')
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='Present').count()
        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 1)
        else:
            attendance_percentage = None
            
    except Student.DoesNotExist:
        student = None
        results_with_pred = []
        chart_data = {'labels': [], 'marks': [], 'predicted': []}
        unread_notifications_count = 0
        attendance_records = []
        total_days = 0
        present_days = 0
        attendance_percentage = None
        
    return render(request, 'students/dashboard.html', {
        'student': student,
        'results_with_pred': results_with_pred,
        'chart_data': chart_data,
        'unread_notifications_count': unread_notifications_count,
        'attendance_records': attendance_records,
        'total_days': total_days,
        'present_days': present_days,
        'attendance_percentage': attendance_percentage,
        'overall_gpa': overall_gpa,
        'term_gpa': term_gpa,
        'latest_term_name': latest_term_name,
    })

@login_required
def notification_list(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'students/notifications.html', {
        'student': student,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count
    })

@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')

def export_pdf(request):
    try:
        student = Student.objects.get(user=request.user)
        results = Result.objects.filter(student=student)
    except Student.DoesNotExist:
        return HttpResponse("No student profile", status=404)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{student.name}_results.pdf"'
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height-50, f"Student Result: {student.name} (Roll: {student.roll_no})")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height-100, "Subject")
    p.drawString(200, height-100, "Marks")
    p.drawString(300, height-100, "Term")
    p.drawString(400, height-100, "Year")
    p.setFont("Helvetica", 11)
    y = height-130
    for r in results:
        p.drawString(50, y, str(r.subject.name))
        p.drawString(200, y, f"{r.marks}")
        p.drawString(300, y, str(r.term))
        p.drawString(400, y, str(r.year))
        y -= 25
        if y < 80:
            p.showPage()
            y = height-50
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def html_report(request):
    try:
        student = Student.objects.get(user=request.user)
        results = Result.objects.filter(student=student)
    except Student.DoesNotExist:
        return HttpResponse("No student profile", status=404)
    return render(request, 'students/report.html', {'student': student, 'results': results})

def home_redirect(request):
    if not request.user.is_authenticated:
        return render(request, 'landing.html')
    elif request.user.is_superuser:
        return redirect('/admin/')
    elif request.user.groups.filter(name='Teacher').exists():
        return redirect('teacher_dashboard')
    else:
        return redirect('dashboard')

class ARAPSLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return '/admin/'
        elif user.groups.filter(name='Teacher').exists():
            return '/teacher/marks/'
        else:
            return '/dashboard/'

def custom_logout(request):
    logout(request)
    return redirect('login')

@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def admin_import_students(request):
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
                return render(request, 'students/bulk_import.html', {'errors': errors})
        except Exception as e:
            errors.append(f"Failed to read file: {e}")
            return render(request, 'students/bulk_import.html', {'errors': errors})

        # Check required columns
        required_cols = {'username', 'name', 'roll_no', 'class_name'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {', '.join(missing_cols)}")
            return render(request, 'students/bulk_import.html', {'errors': errors})

        # Verify Student group exists
        student_group, _ = Group.objects.get_or_create(name='Student')

        # Row by row validation
        records_to_create = []
        seen_usernames = set()
        seen_roll_nos = set()

        for idx, row in df.iterrows():
            row_num = idx + 2  # 1-indexed header is row 1
            username = str(row.get('username', '')).strip() if pd.notna(row.get('username')) else ''
            name = str(row.get('name', '')).strip() if pd.notna(row.get('name')) else ''
            roll_no = str(row.get('roll_no', '')).strip() if pd.notna(row.get('roll_no')) else ''
            class_name = str(row.get('class_name', '')).strip() if pd.notna(row.get('class_name')) else ''

            if not username or username.lower() == 'nan':
                errors.append(f"Row {row_num}: Username cannot be blank.")
            if not name or name.lower() == 'nan':
                errors.append(f"Row {row_num}: Name cannot be blank.")
            if not roll_no or roll_no.lower() == 'nan':
                errors.append(f"Row {row_num}: Roll number cannot be blank.")
            if not class_name or class_name.lower() == 'nan':
                errors.append(f"Row {row_num}: Class name cannot be blank.")

            if username:
                if username in seen_usernames:
                    errors.append(f"Row {row_num}: Duplicate username '{username}' within upload file.")
                seen_usernames.add(username)
                if User.objects.filter(username=username).exists():
                    errors.append(f"Row {row_num}: Username '{username}' already exists in database.")

            if roll_no:
                if roll_no in seen_roll_nos:
                    errors.append(f"Row {row_num}: Duplicate roll number '{roll_no}' within upload file.")
                seen_roll_nos.add(roll_no)
                if Student.objects.filter(roll_no=roll_no).exists():
                    errors.append(f"Row {row_num}: Roll number '{roll_no}' already exists in database.")

            records_to_create.append({
                'username': username,
                'name': name,
                'roll_no': roll_no,
                'class_name': class_name
            })

        if not errors:
            try:
                with transaction.atomic():
                    for rec in records_to_create:
                        user = User.objects.create_user(
                            username=rec['username'],
                            password='student123',
                            first_name=rec['name'].split()[0] if rec['name'].split() else '',
                            last_name=' '.join(rec['name'].split()[1:]) if len(rec['name'].split()) > 1 else ''
                        )
                        student_group.user_set.add(user)
                        Student.objects.create(
                            user=user,
                            name=rec['name'],
                            roll_no=rec['roll_no'],
                            class_name=rec['class_name']
                        )
                success_message = f"Successfully imported {len(records_to_create)} students."
            except Exception as e:
                errors.append(f"Database error during import: {e}")

    return render(request, 'students/bulk_import.html', {'errors': errors, 'success_message': success_message})

def download_students_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_template.csv"'
    writer = csv.writer(response)
    writer.writerow(['username', 'name', 'roll_no', 'class_name'])
    writer.writerow(['student_test', 'Test Student', '21801450', 'BSCS-7A'])
    return response