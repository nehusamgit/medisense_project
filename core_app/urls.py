from django.urls import path
from . import views
from .views import simple_password_reset_view

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout')
    path('reset-password/', simple_password_reset_view, name='simple_password_reset'),
    path('patient/', views.patient_dashboard_view, name='patient_dashboard'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'), 
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'), 
    path('upload-report/', views.upload_report_view, name='upload_report'),
    path('log-vitals/', views.log_vitals_view, name='log_vitals'),
    path('api/vitals-history/', views.vitals_history_api, name='vitals_history_api'),
    path('patient/<int:patient_id>/modal/', views.patient_modal, name='patient_modal'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('doctor/patient/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('doctor/patient/<int:patient_id>/add-medication/', views.add_medication_view, name='add_medication'),
    path('patient/toggle-medication/<int:med_id>/', views.toggle_medication_view, name='toggle_medication'),
    path('doctor/patient/<int:patient_id>/create-appointment/', views.create_appointment_view, name='create_appointment'),
]