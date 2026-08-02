from django.contrib import admin

from django.contrib import admin
from .models import DoctorProfile, Patient, MedicationLog

admin.site.register(DoctorProfile)
admin.site.register(Patient)
admin.site.register(MedicationLog)
