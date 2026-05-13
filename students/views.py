from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Student
from results.models import Result, Subject
from predictions.utils import predict_next_marks
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from io import BytesIO

@login_required
def dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
        results = Result.objects.filter(student=student)
        results_with_pred = []
        for result in results:
            pred = predict_next_marks(student.id, result.subject.id)
            results_with_pred.append({
                'subject': result.subject.name,
                'marks': result.marks,
                'term': result.term,
                'year': result.year,
                'predicted': pred if pred else None
            })
    except Student.DoesNotExist:
        student = None
        results_with_pred = []
    return render(request, 'students/dashboard.html', {
        'student': student,
        'results_with_pred': results_with_pred
    })

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