from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from students.models import Student
from results.models import Subject, Result

def is_teacher(user):
    return user.groups.filter(name='Teacher').exists()

@login_required
@user_passes_test(is_teacher, login_url='/admin/login/')
def teacher_dashboard(request):
    students = Student.objects.all()
    subjects = Subject.objects.all()
    results = Result.objects.all().select_related('student', 'subject')
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
    })

@login_required
@user_passes_test(is_teacher, login_url='/admin/login/')
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
@user_passes_test(is_teacher, login_url='/admin/login/')
def delete_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    if request.method == 'POST':
        result.delete()
        return redirect('teacher_dashboard')
    return render(request, 'teachers/delete_result.html', {'result': result})