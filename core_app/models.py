from django.db import models
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
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField() # Mandatory field
    phone = models.CharField(max_length=15, blank=True)
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

