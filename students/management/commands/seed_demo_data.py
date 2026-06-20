import sys
import random
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.utils.timezone import localdate
from students.models import Student
from results.models import Subject, Result, Notification
from attendance.models import Attendance

class Command(BaseCommand):
    help = 'Reset old test data and seed clean, professional demo data for ARAPS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm execution of the destructive reset and seed process',
        )
        parser.add_argument(
            '--i-understand-this-is-production',
            action='store_true',
            help='Acknowledge and proceed if running on a production-like database or environment',
        )

    def handle(self, *args, **options):
        # 1. Detect production-like environment
        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        is_testing = 'test' in sys.argv
        is_production = (not settings.DEBUG and not is_testing) or ('sqlite3' not in db_engine)

        if is_production and not options.get('i_understand_this_is_production'):
            self.stdout.write(self.style.ERROR(
                "CRITICAL WARNING: You are trying to run this command in a production-like environment\n"
                "(DEBUG=False or database is not SQLite).\n"
                "This command is DESTRUCTIVE and will wipe all teacher/student accounts and related data.\n"
                "To proceed, you must specify both --confirm and --i-understand-this-is-production."
            ))
            return

        # 2. Refuse to run without --confirm
        if not options.get('confirm'):
            self.stdout.write(self.style.WARNING("=== DRY RUN (No changes will be made) ==="))
            self.stdout.write("Running this command WITH --confirm will:")
            self.stdout.write("1. Delete all existing Result and Attendance records.")
            self.stdout.write("2. Delete non-superuser Notifications.")
            self.stdout.write("3. Delete non-superuser Student profiles and User accounts in Student/Teacher groups.")
            self.stdout.write("4. Ensure 'Teacher' and 'Student' Groups exist.")
            self.stdout.write("5. Seed 1 teacher account (username: teacher1).")
            self.stdout.write("6. Seed 5 BSCS subjects (skipping existing ones).")
            self.stdout.write("7. Seed 10 student accounts and Student profiles.")
            self.stdout.write("8. Seed 200 Results (Mid/Final 2023/2024 for 5 subjects) with distinct trends:")
            self.stdout.write("   - student1 - student3: Improving")
            self.stdout.write("   - student4 - student7: Stable")
            self.stdout.write("   - student8 - student10: Declining")
            self.stdout.write("9. Seed 15 days of attendance per student (mostly Present, 1-2 Absent).")
            self.stdout.write("\nRun with --confirm to proceed.")
            return

        self.stdout.write(self.style.SUCCESS("Proceeding with database reset and seeding..."))

        # 3. Perform everything inside a transaction
        with transaction.atomic():
            # Identify users to delete: members of Teacher/Student groups, or anyone with a Student profile,
            # or with usernames we are about to seed (teacher1, student1-10)
            seeded_usernames = ['teacher1'] + [f'student{i}' for i in range(1, 11)]
            users_to_delete = User.objects.filter(
                Q(groups__name__in=['Teacher', 'Student']) | 
                Q(student__isnull=False) |
                Q(username__in=seeded_usernames)
            ).exclude(is_superuser=True).exclude(username='adil123').distinct()

            user_count = users_to_delete.count()

            # Dependency-safe wiping
            self.stdout.write("Wiping Results...")
            Result.objects.all().delete()
            
            self.stdout.write("Wiping Attendance...")
            Attendance.objects.all().delete()
            
            self.stdout.write("Wiping non-superuser Notifications...")
            Notification.objects.filter(recipient__in=users_to_delete).delete()
            
            self.stdout.write("Wiping Student profiles...")
            Student.objects.filter(user__in=users_to_delete).delete()
            
            self.stdout.write(f"Deleting {user_count} non-superuser User accounts...")
            users_to_delete.delete()

            # Seeding Groups
            self.stdout.write("Ensuring groups exist...")
            teacher_group, _ = Group.objects.get_or_create(name='Teacher')
            student_group, _ = Group.objects.get_or_create(name='Student')

            # Seeding Teacher
            self.stdout.write("Seeding teacher account...")
            teacher_user = User.objects.create(
                username='teacher1',
                first_name='Imran',
                last_name='Sheikh',
                email='teacher1@example.com'
            )
            teacher_user.set_password('teacher123')
            teacher_user.save()
            teacher_user.groups.add(teacher_group)

            # Seeding Subjects
            self.stdout.write("Seeding subjects...")
            subject_names = [
                "Programming Fundamentals",
                "Data Structures & Algorithms",
                "Database Systems",
                "Operating Systems",
                "Software Engineering"
            ]
            subjects = []
            for name in subject_names:
                sub, _ = Subject.objects.get_or_create(name=name)
                subjects.append(sub)

            # Seeding Students
            self.stdout.write("Seeding 10 student accounts and profiles...")
            student_data = [
                ("student1", "Ali Hassan", "21801401"),
                ("student2", "Sara Fatima", "21801402"),
                ("student3", "Bilal Ahmed", "21801403"),
                ("student4", "Ayesha Siddiqui", "21801404"),
                ("student5", "Usman Tariq", "21801405"),
                ("student6", "Hina Malik", "21801406"),
                ("student7", "Hamza Raza", "21801407"),
                ("student8", "Mahnoor Khan", "21801408"),
                ("student9", "Faisal Iqbal", "21801409"),
                ("student10", "Zainab Yousuf", "21801410"),
            ]

            students = []
            for username, full_name, roll in student_data:
                user = User.objects.create(
                    username=username,
                    first_name=full_name.split()[0],
                    last_name=" ".join(full_name.split()[1:]),
                    email=f"{username}@example.com"
                )
                user.set_password('student123')
                user.save()
                user.groups.add(student_group)
                
                profile = Student.objects.create(
                    user=user,
                    name=full_name,
                    roll_no=roll,
                    class_name="BSCS-7A"
                )
                students.append(profile)

            # Seeding Results with deliberate trend directions
            self.stdout.write("Seeding 200 result records...")
            terms_years = [
                ('Mid', 2023),
                ('Final', 2023),
                ('Mid', 2024),
                ('Final', 2024)
            ]

            # Let's specify varied offsets for each index to prevent flat lines or excessive predictability,
            # while guaranteeing the mathematically correct trend categories.
            improving_variations = [
                [0, 5, 10, 15],
                [2, 6, 9, 14],
                [1, 4, 8, 13]
            ]
            declining_variations = [
                [15, 10, 5, 0],
                [14, 9, 6, 2],
                [13, 8, 4, 1]
            ]
            stable_variations = [
                [0, 1, 0, 1],
                [1, 0, 1, 0],
                [0, 0, 0, 0],
                [1, 2, 1, 1],
                [-1, 0, -1, 0],
            ]

            for idx, student in enumerate(students):
                for s_idx, subject in enumerate(subjects):
                    # Base marks range from 50 to 80 depending on subject and student
                    if idx in [0, 1, 2]: # Improving
                        base = 58 + (s_idx * 3) + (idx * 2)
                        offsets = improving_variations[(s_idx + idx) % len(improving_variations)]
                    elif idx in [3, 4, 5, 6]: # Stable
                        base = 72 + (s_idx * 2) - ((idx - 3) * 2)
                        offsets = stable_variations[(s_idx + idx) % len(stable_variations)]
                    else: # Declining (indices 7, 8, 9)
                        base = 52 + (s_idx * 3) + ((idx - 7) * 2)
                        offsets = declining_variations[(s_idx + idx) % len(declining_variations)]

                    for t_idx, (term, year) in enumerate(terms_years):
                        offset = offsets[t_idx]
                        mark = base + offset
                        
                        # Clip to realistic limits
                        mark = max(0.0, min(100.0, float(mark)))

                        Result.objects.create(
                            student=student,
                            subject=subject,
                            marks=mark,
                            term=term,
                            year=year
                        )

            # Seeding Attendance
            self.stdout.write("Seeding attendance records (15 days)...")
            current_date = localdate()
            attendance_dates = []
            d = current_date
            while len(attendance_dates) < 15:
                # weekday(): 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun
                if d.weekday() < 5:
                    attendance_dates.append(d)
                d -= datetime.timedelta(days=1)

            for student in students:
                # Select 1 or 2 random dates to be absent
                absent_dates = random.sample(attendance_dates, k=random.choice([1, 2]))
                for date in attendance_dates:
                    status = 'Absent' if date in absent_dates else 'Present'
                    Attendance.objects.create(
                        student=student,
                        date=date,
                        status=status
                    )

        self.stdout.write(self.style.SUCCESS("Demo database successfully reset and seeded!"))
        self.stdout.write("\n" + "="*60)
        self.stdout.write("                    DEMO CREDENTIALS SUMMARY                    ")
        self.stdout.write("="*60)
        self.stdout.write(f"{'Role':<12} | {'Username':<12} | {'Password':<12} | {'Name/Roll No':<25}")
        self.stdout.write("-"*60)
        self.stdout.write(f"{'Teacher':<12} | {'teacher1':<12} | {'teacher123':<12} | Imran Sheikh")
        for idx, (username, full_name, roll) in enumerate(student_data):
            role_desc = f"Student {idx+1}"
            self.stdout.write(f"{role_desc:<12} | {username:<12} | {'student123':<12} | {full_name} ({roll})")
        self.stdout.write("="*60 + "\n")
