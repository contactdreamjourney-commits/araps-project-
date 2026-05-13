from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('report/', views.html_report, name='html_report'),   # <-- ADD THIS LINE
]