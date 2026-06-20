from django.db import models
from django.contrib.auth.models import User
from students.models import Student

class Subject(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.FloatField()
    term = models.CharField(max_length=10)
    year = models.IntegerField(default=2025)

    @property
    def letter_grade(self):
        from results.grading import get_grade_info
        letter, _ = get_grade_info(self.marks)
        return letter

    @property
    def grade_point(self):
        from results.grading import get_grade_info
        _, gp = get_grade_info(self.marks)
        return gp

    def __str__(self):
        return f"{self.student.name} - {self.subject.name}"

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.user.username if self.user else 'System'} on {self.created_at}"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:30]}"