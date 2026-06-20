from django.test import TestCase
from django.contrib.auth.models import User
from students.models import Student
from results.models import Subject, Result
from predictions.utils import predict_next_marks

class PredictionRegressionTests(TestCase):
    def setUp(self):
        # Create standard test data
        self.user = User.objects.create_user(username='teststudent', password='student123')
        self.student = Student.objects.create(
            user=self.user,
            name='Test Student',
            roll_no='T21801401',
            class_name='BSCS-7A'
        )
        self.subject = Subject.objects.create(name='Programming Fundamentals')

    def test_mid_and_final_same_year_produces_valid_prediction(self):
        # Test 1: Student with both Mid-term and Final-term marks for the same subject and year
        # generates a valid float prediction without raising exceptions.
        Result.objects.create(student=self.student, subject=self.subject, marks=75.0, term='Mid', year=2024)
        Result.objects.create(student=self.student, subject=self.subject, marks=85.0, term='Final', year=2024)

        pred = predict_next_marks(self.student.id, self.subject.id)
        self.assertIsNotNone(pred)
        self.assertIsInstance(pred, float)
        # Linear regression prediction check:
        # x1 = 2024.0 (Mid), y1 = 75
        # x2 = 2024.5 (Final), y2 = 85
        # Slope = (85-75)/(2024.5-2024.0) = 10 / 0.5 = 20
        # Next x = 2024.5 + 0.5 = 2025.0
        # Pred = 85 + 20 * 0.5 = 95.0
        self.assertEqual(pred, 95.0)

    def test_single_result_returns_none_cleanly(self):
        # Test 2: Student with only one mark returns None safely.
        Result.objects.create(student=self.student, subject=self.subject, marks=80.0, term='Mid', year=2024)

        pred = predict_next_marks(self.student.id, self.subject.id)
        self.assertIsNone(pred)

    def test_results_across_different_years_returns_sane_prediction(self):
        # Test 3: Student with multiple marks across 2 different years returns a plausible number (clipped between 0 and 100).
        Result.objects.create(student=self.student, subject=self.subject, marks=60.0, term='Mid', year=2023)
        Result.objects.create(student=self.student, subject=self.subject, marks=65.0, term='Final', year=2023)
        Result.objects.create(student=self.student, subject=self.subject, marks=70.0, term='Mid', year=2024)
        Result.objects.create(student=self.student, subject=self.subject, marks=75.0, term='Final', year=2024)

        pred = predict_next_marks(self.student.id, self.subject.id)
        self.assertIsNotNone(pred)
        self.assertTrue(0.0 <= pred <= 100.0)
        # Predicted value should follow improving trend (e.g., above 75)
        self.assertTrue(pred > 75.0)
