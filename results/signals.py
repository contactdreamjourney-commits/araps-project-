from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.auth.models import User
from students.models import Student
from results.models import Result, AuditLog, Notification
from results.middleware import get_current_user

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    try:
        AuditLog.objects.create(
            user=user,
            action="Login",
            details=f"User {user.username} logged in successfully."
        )
    except Exception:
        pass

@receiver(post_save, sender=Result)
def log_and_notify_result_save(sender, instance, created, **kwargs):
    # Log Result creation/update
    try:
        user = get_current_user()
        action = "Result Created" if created else "Result Updated"
        details = f"Result ID {instance.id} for Student {instance.student.name} (Subject: {instance.subject.name}, Marks: {instance.marks}) was {'created' if created else 'updated'}."
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            details=details
        )
    except Exception:
        pass

    # Trigger Notification to student
    try:
        student_user = instance.student.user
        action_str = "added" if created else "updated"
        msg = f"Your result for {instance.subject.name} ({instance.term} term, {instance.year}) has been {action_str}. Marks: {instance.marks}."
        Notification.objects.create(
            recipient=student_user,
            message=msg
        )
    except Exception:
        pass

@receiver(post_delete, sender=Result)
def log_result_delete(sender, instance, **kwargs):
    try:
        user = get_current_user()
        details = f"Result ID {instance.id} for Student {instance.student.name} (Subject: {instance.subject.name}, Marks: {instance.marks}) was deleted."
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action="Result Deleted",
            details=details
        )
    except Exception:
        pass

@receiver(post_save, sender=Student)
def log_student_save(sender, instance, created, **kwargs):
    try:
        user = get_current_user()
        action = "Student Created" if created else "Student Updated"
        details = f"Student {instance.name} (Roll: {instance.roll_no}, Class: {instance.class_name}) was {'created' if created else 'updated'}."
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            details=details
        )
    except Exception:
        pass

@receiver(post_delete, sender=Student)
def log_student_delete(sender, instance, **kwargs):
    try:
        user = get_current_user()
        details = f"Student {instance.name} (Roll: {instance.roll_no}, Class: {instance.class_name}) was deleted."
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action="Student Deleted",
            details=details
        )
    except Exception:
        pass
