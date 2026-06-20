import datetime
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User, Group
from students.models import Student
from results.models import Subject, Result, Notification
from attendance.models import Attendance
from predictions.utils import get_subject_trend

class SeedDemoDataTests(TestCase):
    def setUp(self):
        # Create a superuser we expect to NOT be deleted
        self.superuser = User.objects.create_superuser(username='adil123', password='password123', email='adil123@example.com')
        
        # Create some dummy test data to be deleted
        self.other_user = User.objects.create_user(username='oldstudent', password='password123')
        self.student_group, _ = Group.objects.get_or_create(name='Student')
        self.other_user.groups.add(self.student_group)
        self.student_profile = Student.objects.create(user=self.other_user, name='Old Student', roll_no='9999', class_name='OldClass')
        self.subj = Subject.objects.create(name='Old Subject')
        
        Result.objects.create(student=self.student_profile, subject=self.subj, marks=50.0, term='Mid', year=2023)
        Attendance.objects.create(student=self.student_profile, date=datetime.date(2023, 1, 1), status='Present')

    def test_dry_run_does_not_modify_db(self):
        # Run without confirm flag
        call_command('seed_demo_data')
        
        # Verify old data is still there
        self.assertTrue(User.objects.filter(username='oldstudent').exists())
        self.assertTrue(Student.objects.filter(roll_no='9999').exists())
        self.assertTrue(Result.objects.filter(marks=50.0).exists())
        self.assertTrue(Attendance.objects.filter(status='Present').exists())
        
    def test_confirm_seeds_successfully(self):
        # Run with confirm flag
        call_command('seed_demo_data', confirm=True)
        
        # Verify old data is wiped
        self.assertFalse(User.objects.filter(username='oldstudent').exists())
        self.assertFalse(Student.objects.filter(roll_no='9999').exists())
        
        # Verify superuser adil123 is NOT deleted
        self.assertTrue(User.objects.filter(username='adil123').exists())
        
        # Verify teacher1 is created and is in Teacher group
        self.assertTrue(User.objects.filter(username='teacher1').exists())
        teacher = User.objects.get(username='teacher1')
        self.assertTrue(teacher.groups.filter(name='Teacher').exists())
        
        # Verify 10 students created
        self.assertEqual(Student.objects.count(), 10)
        
        # Verify 200 result records created (10 students * 5 subjects * 4 combinations)
        self.assertEqual(Result.objects.count(), 200)
        
        # Verify attendance records created (10 students * 15 days = 150 records)
        self.assertEqual(Attendance.objects.count(), 150)
        
        # Verify trend of student1 is Improving
        student1 = Student.objects.get(user__username='student1')
        subjects = Subject.objects.exclude(name='Old Subject') # Since 'Old Subject' might exist if not wiped
        for sub in subjects:
            sub_results = Result.objects.filter(student=student1, subject=sub)
            self.assertEqual(get_subject_trend(sub_results), "Improving")
            
        # Verify trend of student8 is Declining
        student8 = Student.objects.get(user__username='student8')
        for sub in subjects:
            sub_results = Result.objects.filter(student=student8, subject=sub)
            self.assertEqual(get_subject_trend(sub_results), "Declining")

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

class ImportViewsTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username='admin_test', password='password123', email='admin@example.com')
        self.teacher_user = User.objects.create_user(username='teacher_test', password='password123')
        self.teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        self.teacher_user.groups.add(self.teacher_group)

        self.student_group, _ = Group.objects.get_or_create(name='Student')
        self.student_user = User.objects.create_user(username='student_test', password='password123')
        self.student_user.groups.add(self.student_group)
        self.student_profile = Student.objects.create(user=self.student_user, name='Ali Student', roll_no='21801999', class_name='BSCS-7A')

        self.subject = Subject.objects.create(name='Database Systems')

    def test_download_students_template(self):
        self.client.login(username='admin_test', password='password123')
        url = reverse('download_students_template')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(b'username,name,roll_no,class_name', response.content)

    def test_download_results_template(self):
        self.client.login(username='teacher_test', password='password123')
        url = reverse('download_results_template')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(b'student_roll_no,subject,term,year,marks', response.content)

    def test_admin_import_students_success(self):
        self.client.login(username='admin_test', password='password123')
        url = reverse('admin_import_students')
        
        csv_file = SimpleUploadedFile("test_students.csv", b"username,name,roll_no,class_name\nnewstudent1,New Student One,21802001,BSCS-7A\nnewstudent2,New Student Two,21802002,BSCS-7A")

        response = self.client.post(url, {'file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Successfully imported 2 students")

        # Verify database
        self.assertTrue(User.objects.filter(username='newstudent1').exists())
        self.assertTrue(Student.objects.filter(roll_no='21802001').exists())
        self.assertTrue(User.objects.filter(username='newstudent2').exists())
        self.assertTrue(Student.objects.filter(roll_no='21802002').exists())

    def test_admin_import_students_validation_error(self):
        self.client.login(username='admin_test', password='password123')
        url = reverse('admin_import_students')
        
        # Duplicate roll number in the file
        csv_file = SimpleUploadedFile("test_students.csv", b"username,name,roll_no,class_name\nnewstudent1,New Student One,21802001,BSCS-7A\nnewstudent2,New Student Two,21802001,BSCS-7A")

        response = self.client.post(url, {'file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Duplicate roll number")
        
        # Verify rollback - no student should be created
        self.assertFalse(User.objects.filter(username='newstudent1').exists())
        self.assertFalse(Student.objects.filter(roll_no='21802001').exists())

    def test_teacher_import_results_success(self):
        self.client.login(username='teacher_test', password='password123')
        url = reverse('teacher_import_results')

        csv_file = SimpleUploadedFile("test_results.csv", b"student_roll_no,subject,term,year,marks\n21801999,Database Systems,Mid,2024,85.5")

        response = self.client.post(url, {'file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Successfully imported 1 results")

        # Verify Result
        res = Result.objects.get(student=self.student_profile, subject=self.subject)
        self.assertEqual(res.marks, 85.5)
        self.assertEqual(res.term, 'Mid')
        self.assertEqual(res.year, 2024)

    def test_teacher_import_results_validation_error(self):
        self.client.login(username='teacher_test', password='password123')
        url = reverse('teacher_import_results')

        # Invalid marks (150)
        csv_file = SimpleUploadedFile("test_results.csv", b"student_roll_no,subject,term,year,marks\n21801999,Database Systems,Mid,2024,150.0")

        response = self.client.post(url, {'file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must be between 0 and 100")

        # Verify rollback
        self.assertFalse(Result.objects.filter(student=self.student_profile, subject=self.subject).exists())

