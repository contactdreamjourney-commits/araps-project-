from django.db import models

# Create your models here.
from django.db import models
from students.models import Student

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.student.name} - {self.date}"