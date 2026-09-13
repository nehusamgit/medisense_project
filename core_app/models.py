from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# 1. Doctor Profile Table
class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100, default="General Practitioner")
    age = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"

# 2. Patient Table (Doctors can add patients)
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='patient_profile')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_patients')
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField() # Mandatory field
    phone = models.CharField(max_length=15, default="919876543210", help_text="Enter phone number with country code without + (e.g. 919876543210)")
    condition = models.CharField(max_length=50, default='general')

    def __str__(self):
        return self.name

# 3. Medication Log Table (To track daily dose)
class MedicationLog(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(auto_now_add=True)
    morning_dose = models.BooleanField(default=False)
    afternoon_dose = models.BooleanField(default=False)
    evening_dose = models.BooleanField(default=False)
    missed_any = models.BooleanField(default=False) # For AI prediction later

    def __str__(self):
        return f"{self.patient.name} - {self.date}"

class PatientVital(models.Model):
    """Logs daily health metrics (Phase 1)."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    systolic_bp = models.IntegerField(help_text="mmHg")
    diastolic_bp = models.IntegerField(help_text="mmHg")
    heart_rate = models.IntegerField(help_text="BPM")
    blood_sugar = models.FloatField(help_text="mg/dL")
    spo2_level = models.FloatField(help_text="%")
    logged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - Vitals ({self.logged_at.strftime('%Y-%m-%d %H:%M')})"


class PatientThreshold(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='thresholds')
    min_systolic_bp = models.IntegerField(default=90, help_text="Minimum safe systolic BP")
    max_systolic_bp = models.IntegerField(default=140, help_text="Maximum safe systolic BP")
    min_diastolic_bp = models.IntegerField(default=60, help_text="Minimum safe diastolic BP")
    max_diastolic_bp = models.IntegerField(default=90, help_text="Maximum safe diastolic BP")
    min_blood_sugar = models.FloatField(default=70, help_text="Minimum safe blood sugar")
    max_blood_sugar = models.FloatField(default=180, help_text="Maximum safe blood sugar")
    min_spo2 = models.FloatField(default=90, help_text="Minimum safe oxygen saturation")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.name} threshold settings"


class PatientCaseSheetNote(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='case_sheet_notes')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    clinical_impression = models.TextField()
    recommended_action = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']


class AIRiskAssessment(models.Model):
    """Stores AI/ML risk evaluations linked to vital logs (Phase 1)."""
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MODERATE', 'Moderate Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]

    vital = models.OneToOneField(PatientVital, on_delete=models.CASCADE, related_name='ai_assessment')
    risk_score = models.FloatField(help_text="Probability score 0.00 - 1.00")
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    predicted_condition = models.CharField(max_length=150, null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vital.patient.name} - {self.risk_level} ({self.risk_score})"

class Medication(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='medications')
    prescribed_by = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    medicine_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    timing = models.CharField(max_length=50)
    is_taken_today = models.BooleanField(default=False)
    last_taken_date = models.DateField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medicine_name} - {self.patient.user.username}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    TYPE_CHOICES = [
        ('ROUTINE', 'Routine Checkup'),
        ('CRITICAL', 'Critical Follow-up'),
    ]

    # Note: Foreign key names match your project setup (Doctor Profile & Patient Profile)
    doctor = models.ForeignKey('DoctorProfile', on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='appointments')
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ROUTINE')
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']

    def __str__(self):
        return f"{self.get_appointment_type_display()} - {self.patient.user.username} on {self.scheduled_date}"

class EmergencyAlert(models.Model):
    ALERT_TYPES = (
        ('SOS', 'Manual SOS Button'),
        ('CRITICAL_VITALS', 'Critical Vitals Threshold'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='alerts')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='SOS')
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} - {self.patient.name}"

class DiagnosticReport(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diagnostic_reports')
    report_file = models.FileField(upload_to='diagnostic_reports/')
    summary = models.TextField()
    status_flag = models.CharField(max_length=50, default='Document Insights Normal')
    flagged_data = models.JSONField(default=list, blank=True) # Metrics like Glucose, Cholesterol
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - Report ({self.created_at.strftime('%Y-%m-%d')})"