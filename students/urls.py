from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('report/', views.html_report, name='html_report'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('import-students/', views.admin_import_students, name='admin_import_students'),
    path('download-students-template/', views.download_students_template, name='download_students_template'),
]