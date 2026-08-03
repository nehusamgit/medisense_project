from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'), 
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'), 
    path('upload-report/', views.upload_report_view, name='upload_report'),
    path('log-vitals/', views.log_vitals_view, name='log_vitals'),
]