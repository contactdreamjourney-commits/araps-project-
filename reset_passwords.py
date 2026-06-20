import os
import django

# Bootstrap Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'result_system.settings')
django.setup()

from django.contrib.auth.models import User, Group
from students.models import Student

def setup_accounts():
    # Define credentials (easily customizable)
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'
    
    TEACHER_USERNAME = 'teacher1'
    TEACHER_PASSWORD = 'teacher123'
    
    STUDENT_USERNAME = 'student1'
    STUDENT_PASSWORD = 'student123'
    
    # Ensure Teacher group exists
    teacher_group, created = Group.objects.get_or_create(name='Teacher')
    
    # 1. Setup Admin Account
    try:
        user, created = User.objects.get_or_create(username=ADMIN_USERNAME)
        user.is_superuser = True
        user.is_staff = True
        user.set_password(ADMIN_PASSWORD)
        user.save()
        print(f"Password reset/account setup for admin [OK]")
    except Exception as e:
        print(f"Failed to setup admin account: {e}")
        
    # 2. Setup Teacher Account
    try:
        user, created = User.objects.get_or_create(username=TEACHER_USERNAME)
        user.is_staff = True
        user.set_password(TEACHER_PASSWORD)
        user.save()
        user.groups.add(teacher_group)
        print(f"Password reset/account setup for teacher1 [OK]")
    except Exception as e:
        print(f"Failed to setup teacher1 account: {e}")
        
    # 3. Setup Student Account
    try:
        user, created = User.objects.get_or_create(username=STUDENT_USERNAME)
        # Note: Students need is_staff = True to log in via Django admin's /admin/login/ screen
        user.is_staff = True
        user.set_password(STUDENT_PASSWORD)
        user.save()
        
        # Link to Student profile if not exists
        student, s_created = Student.objects.get_or_create(
            user=user,
            defaults={
                'name': 'Student 1',
                'roll_no': '2025001',
                'class_name': '10th'
            }
        )
        print(f"Password reset/account setup for student1 [OK]")
    except Exception as e:
        print(f"Failed to setup student1 account: {e}")

if __name__ == '__main__':
    setup_accounts()
