from django.db import models
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
    year = models.IntegerField(default=2025)   # ← yeh line add karo

    def __str__(self):
        return f"{self.student.name} - {self.subject.name}"