from django.test import TestCase
from django.contrib.auth.models import User
from students.models import Student
from results.models import Subject, Result, AuditLog, Notification
from predictions.utils import predict_next_marks, get_subject_trend

class ResultSystemTests(TestCase):
    def setUp(self):
        # Create user and student
        self.user = User.objects.create_user(username='teststudent', password='password123')
        self.student = Student.objects.create(user=self.user, name='Test Student', roll_no='T001', class_name='10th')
        # Create subjects
        self.math = Subject.objects.create(name='Math')
        self.science = Subject.objects.create(name='Science')

    def test_subject_trend_improving(self):
        Result.objects.create(student=self.student, subject=self.math, marks=60.0, term='mid', year=2025)
        Result.objects.create(student=self.student, subject=self.math, marks=80.0, term='final', year=2025)
        
        sub_results = Result.objects.filter(student=self.student, subject=self.math)
        trend = get_subject_trend(sub_results)
        self.assertEqual(trend, "Improving")

    def test_subject_trend_declining(self):
        Result.objects.create(student=self.student, subject=self.math, marks=90.0, term='mid', year=2025)
        Result.objects.create(student=self.student, subject=self.math, marks=70.0, term='final', year=2025)
        
        sub_results = Result.objects.filter(student=self.student, subject=self.math)
        trend = get_subject_trend(sub_results)
        self.assertEqual(trend, "Declining")

    def test_subject_trend_stable(self):
        Result.objects.create(student=self.student, subject=self.math, marks=75.0, term='mid', year=2025)
        Result.objects.create(student=self.student, subject=self.math, marks=75.0, term='final', year=2025)
        
        sub_results = Result.objects.filter(student=self.student, subject=self.math)
        trend = get_subject_trend(sub_results)
        self.assertEqual(trend, "Stable")

    def test_predict_next_marks(self):
        Result.objects.create(student=self.student, subject=self.math, marks=70.0, term='mid', year=2025)
        Result.objects.create(student=self.student, subject=self.math, marks=80.0, term='final', year=2025)
        
        pred = predict_next_marks(self.student.id, self.math.id)
        # Expected linear equation: X=2025.0 -> Y=70, X=2025.5 -> Y=80 (slope=20 per term/year offset, i.e. 20 per 0.5 step = 20 / 0.5 = 40 slope)
        # intercept = 70 - 40 * 2025 = -80930
        # Next X is max(X) + 0.5 = 2025.5 + 0.5 = 2026.0
        # Prediction = 40 * 2026.0 - 80930 = 90.0
        self.assertIsNotNone(pred)
        self.assertEqual(pred, 90.0)

    def test_audit_log_signals(self):
        # Result creation should trigger AuditLog
        res = Result.objects.create(student=self.student, subject=self.science, marks=85.0, term='mid', year=2025)
        self.assertTrue(AuditLog.objects.filter(action="Result Created").exists())
        
        # Result update should trigger AuditLog
        res.marks = 92.0
        res.save()
        self.assertTrue(AuditLog.objects.filter(action="Result Updated").exists())
        
        # Result delete should trigger AuditLog
        res.delete()
        self.assertTrue(AuditLog.objects.filter(action="Result Deleted").exists())

    def test_notification_signals(self):
        # Creating a result should notify student
        Result.objects.create(student=self.student, subject=self.science, marks=85.0, term='mid', year=2025)
        notifications = Notification.objects.filter(recipient=self.user)
        self.assertEqual(notifications.count(), 1)
        self.assertIn("Math" not in notifications.first().message, [True])

    def test_attendance_model(self):
        from attendance.models import Attendance
        import datetime
        att = Attendance.objects.create(student=self.student, date=datetime.date(2026, 6, 17), status='Present')
        self.assertEqual(att.status, 'Present')
        
        # Test unique constraint
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(student=self.student, date=datetime.date(2026, 6, 17), status='Absent')

    def test_role_security_middleware_student(self):
        self.client.force_login(self.user)
        response = self.client.get('/admin/results/result/')
        # Should redirect to student dashboard (which is /dashboard/)
        self.assertRedirects(response, '/dashboard/')

    def test_role_security_middleware_teacher(self):
        from django.contrib.auth.models import Group
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        teacher_user = User.objects.create_user(username='testteacher', password='password123')
        teacher_user.groups.add(teacher_group)
        
        self.client.force_login(teacher_user)
        response = self.client.get('/admin/results/result/')
        # Should redirect to teacher dashboard (which is /teacher/marks/)
        self.assertRedirects(response, '/teacher/marks/')

    def test_role_security_middleware_superuser(self):
        superuser = User.objects.create_superuser(username='testadmin', password='password123')
        self.client.force_login(superuser)
        response = self.client.get('/admin/')
        # Should be 200 OK or 302 redirect but not to a student/teacher dashboard
        self.assertIn(response.status_code, [200, 302])

    def test_mark_attendance_view_get(self):
        from django.contrib.auth.models import Group
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        teacher_user = User.objects.create_user(username='testteacher', password='password123')
        teacher_user.groups.add(teacher_group)
        self.client.force_login(teacher_user)
        
        response = self.client.get('/teacher/attendance/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Attendance')
        
    def test_mark_attendance_view_post(self):
        from django.contrib.auth.models import Group
        from attendance.models import Attendance
        import datetime
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        teacher_user = User.objects.create_user(username='testteacher', password='password123')
        teacher_user.groups.add(teacher_group)
        self.client.force_login(teacher_user)
        
        post_data = {
            f'status_{self.student.id}': 'Present'
        }
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        response = self.client.post(f'/teacher/attendance/?date={today_str}', post_data)
        self.assertEqual(response.status_code, 302)
        
        att = Attendance.objects.get(student=self.student, date=datetime.date.today())
        self.assertEqual(att.status, 'Present')

    def test_unauthenticated_user_redirects_to_login(self):
        # Access student dashboard unauthenticated
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/?next=/dashboard/')
        
        # Access teacher dashboard unauthenticated
        response = self.client.get('/teacher/marks/')
        self.assertRedirects(response, '/login/?next=/teacher/marks/')

    def test_login_page_renders_custom_template(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'ARAPS')

    def test_login_redirection_and_welcome_messages(self):
        # 1. Student Login & Redirection & Welcome Message
        response = self.client.post('/login/', {'username': 'teststudent', 'password': 'password123'})
        self.assertRedirects(response, '/dashboard/')
        
        # Follow the redirect and verify welcome message
        dashboard_response = self.client.get('/dashboard/')
        self.assertContains(dashboard_response, 'Welcome, Student teststudent!')
        
        # Log out
        logout_response = self.client.get('/logout/')
        self.assertRedirects(logout_response, '/login/')
        
        # 2. Teacher Login & Redirection & Welcome Message
        from django.contrib.auth.models import Group
        teacher_group, _ = Group.objects.get_or_create(name='Teacher')
        teacher_user = User.objects.create_user(username='testteacher2', password='password123')
        teacher_user.groups.add(teacher_group)
        
        response = self.client.post('/login/', {'username': 'testteacher2', 'password': 'password123'})
        self.assertRedirects(response, '/teacher/marks/')
        
        dashboard_response = self.client.get('/teacher/marks/')
        self.assertContains(dashboard_response, 'Welcome, Teacher testteacher2!')

        # Log out
        logout_response = self.client.get('/logout/')
        self.assertRedirects(logout_response, '/login/')

