from django.urls import path
from . import views

urlpatterns = [
    path('marks/', views.teacher_dashboard, name='teacher_dashboard'),
    path('edit/<int:result_id>/', views.edit_result, name='edit_result'),
    path('delete/<int:result_id>/', views.delete_result, name='delete_result'),
    path('attendance/', views.mark_attendance, name='mark_attendance'),
    path('import-results/', views.teacher_import_results, name='teacher_import_results'),
    path('download-results-template/', views.download_results_template, name='download_results_template'),
]