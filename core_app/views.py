import re
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import JsonResponse
from twilio.rest import Client
from .models import Patient, DoctorProfile, PatientVital, AIRiskAssessment, Medication, Appointment, EmergencyAlert, DiagnosticReport

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        full_name = request.POST.get('first_name', '').strip()
        age_str = request.POST.get('age', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', 'patient')
        report_file = request.FILES.get('report_file')

        if not all([username, email, full_name, age_str, password, confirm_password]):
            messages.error(request, "Please enter all required fields.")
            return render(request, 'register.html')

        name_parts = full_name.split()
        if len(name_parts) < 2:
            messages.error(request, "Please enter your full name (first and last name).")
            return render(request, 'register.html')

        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'register.html')

        try:
            age = int(age_str)
            if age <= 0 or age > 120:
                messages.error(request, "Please enter a valid age between 1 and 120.")
                return render(request, 'register.html')
        except ValueError:
            messages.error(request, "Age must be a valid number.")
            return render(request, 'register.html')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'register.html')
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'register.html')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'register.html')

        try:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )

            if role == 'doctor':
                DoctorProfile.objects.create(user=user, age=age)
            else:
                Patient.objects.create(user=user, name=full_name, age=age)
                if report_file:
                    MedicalReport.objects.create(
                        user=user,
                        title=report_file.name,
                        report_file=report_file
                    )

            messages.success(request, "Registration successful! You can now log in immediately.")
            return redirect('login')

        except Exception as e:
            messages.error(request, f"Database Error: {str(e)}")
            return render(request, 'register.html')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
            elif hasattr(user, 'doctorprofile') or hasattr(user, 'doctor_profile'):
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

def simple_password_reset_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('username_or_email', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not identifier or not new_password:
            messages.error(request, "All fields are required!")
            return render(request, 'simple_password_reset.html')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'simple_password_reset.html')

        user = User.objects.filter(username__iexact=identifier).first()
        if not user:
            user = User.objects.filter(email__iexact=identifier).first()

        if user:
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password updated for user '{user.username}'! Please log in.")
            return redirect('login')
        else:
            messages.error(request, "No account found with this Username or Email.")

    return render(request, 'simple_password_reset.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    role = request.GET.get('role', 'all')
    users = User.objects.all().order_by('-date_joined')

    if role == 'doctor':
        users = users.filter(is_staff=True)
    elif role == 'patient':
        users = users.filter(is_staff=False)

    context = {
        'users': users,
        'total_users': User.objects.count(),
        'active_doctors': User.objects.filter(is_staff=True).count(),
        'active_patients': User.objects.filter(is_staff=False).count(),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'partials/admin_user_list.html', context)

    return render(request, 'admin_dashboard.html', context)

@login_required
@csrf_exempt
def delete_user(request, user_id):
    if request.method == 'POST':
        if request.user.id == user_id:
            return HttpResponse(status=400)

        user_to_delete = get_object_or_404(User, id=user_id)
        user_to_delete.is_active = False
        user_to_delete.save()

        return HttpResponse("", status=200)

    return HttpResponse(status=400)

@login_required
def patient_dashboard_view(request):
    try:
        patient_profile = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient_profile = None

    latest_vital = None
    medications = []
    upcoming_appointments = []
    adherence_rate = 0
    vitals_history = []
    latest_report = None

    if patient_profile:
        latest_vital = PatientVital.objects.filter(patient=patient_profile).order_by('-logged_at').first()
        medications = Medication.objects.filter(patient=patient_profile).order_by('-created_at')
        
        latest_report = DiagnosticReport.objects.filter(patient=patient_profile).order_by('-created_at').first()

        today = timezone.now().date()
        upcoming_appointments = Appointment.objects.filter(
            patient=patient_profile,
            status='SCHEDULED',
            scheduled_date__gte=today
        ).order_by('scheduled_date', 'scheduled_time')

        total_meds = medications.count()
        if total_meds > 0:
            taken_count = medications.filter(is_taken_today=True).count()
            adherence_rate = round((taken_count / total_meds) * 100)

        vitals_qs = list(PatientVital.objects.filter(patient=patient_profile).order_by('-logged_at')[:10])
        vitals_qs.reverse() 

        for v in vitals_qs:
            vitals_history.append({
                'timestamp': v.logged_at.strftime('%b %d, %H:%M') if getattr(v, 'logged_at', None) else '',
                'systolic': v.systolic_bp if getattr(v, 'systolic_bp', None) else 0,
                'diastolic': v.diastolic_bp if getattr(v, 'diastolic_bp', None) else 0,
                'glucose': float(v.blood_sugar) if getattr(v, 'blood_sugar', None) else 0,
                'heart_rate': v.heart_rate if getattr(v, 'heart_rate', None) else 0,
                'spo2': float(v.spo2_level) if getattr(v, 'spo2_level', None) else 0,
            })

    context = {
        'patient': patient_profile,
        'latest_vital': latest_vital,
        'medications': medications,
        'upcoming_appointments': upcoming_appointments,
        'adherence_rate': adherence_rate,
        'vitals_history_json': json.dumps(vitals_history),
        'latest_report': latest_report,
    }

    return render(request, 'patient_dashboard.html', context)

@login_required
def add_patient(request):
    try:
        current_doctor = request.user.doctor_profile
    except DoctorProfile.DoesNotExist:
        return redirect('doctor_dashboard')

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        condition = request.POST.get('condition', 'general')

        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            patient.doctor = current_doctor
            if condition:
                patient.condition = condition
            patient.save()

        return redirect('doctor_dashboard')

    unassigned_patients = Patient.objects.filter(doctor__isnull=True)

    context = {
        'unassigned_patients': unassigned_patients
    }
    return render(request, 'add_patient.html', context)

@login_required
def log_vitals_view(request):
    if request.method == 'POST':
        try:
            patient_profile, _ = Patient.objects.get_or_create(
                user=request.user,
                defaults={'name': request.user.get_full_name() or request.user.username, 'age': 30}
            )

            sys_bp = int(request.POST.get('systolic_bp', 120))
            dia_bp = int(request.POST.get('diastolic_bp', 80))
            hr = int(request.POST.get('heart_rate', 72))
            sugar = float(request.POST.get('blood_sugar', 100.0))
            spo2 = float(request.POST.get('spo2_level', 98.0))

            vital_entry = PatientVital.objects.create(
                patient=patient_profile,
                systolic_bp=sys_bp,
                diastolic_bp=dia_bp,
                heart_rate=hr,
                blood_sugar=sugar,
                spo2_level=spo2
            )

            critical_conditions = []
            moderate_conditions = []

            if sys_bp > 140 or dia_bp > 90:
                critical_conditions.append('Hypertension')
            elif sys_bp < 90 or dia_bp < 60:
                critical_conditions.append('Hypotension (Low BP)')

            if sugar > 180:
                critical_conditions.append('Hyperglycemia')
            elif sugar < 70:
                critical_conditions.append('Hypoglycemia (Low Sugar)')

            if spo2 < 93:
                critical_conditions.append('Hypoxia (Low Oxygen)')

            if not critical_conditions:
                if 130 <= sys_bp <= 140 or 80 <= dia_bp <= 90:
                    moderate_conditions.append('Elevated Blood Pressure')
                if 120 <= sugar <= 180:
                    moderate_conditions.append('Elevated Blood Sugar')
                if 93 <= spo2 <= 95:
                    moderate_conditions.append('Borderline Oxygen Level')

            if critical_conditions:
                risk_score = 0.88
                risk_level = 'CRITICAL'
                condition = ' & '.join(critical_conditions) + ' Risk'
                recommendation = 'Critical vitals detected. Immediate clinical review required.'
            elif moderate_conditions:
                risk_score = 0.55
                risk_level = 'MODERATE'
                condition = ' & '.join(moderate_conditions)
                recommendation = 'Monitor vitals closely over the next 24 hours.'
            else:
                risk_score = 0.15
                risk_level = 'NORMAL'  
                condition = 'Normal Vitals'
                recommendation = 'Maintain regular diet, hydration, and daily medication schedule.'

            AIRiskAssessment.objects.create(
                vital=vital_entry,
                risk_score=risk_score,
                risk_level=risk_level,
                predicted_condition=condition,
                recommendation=recommendation
            )

            messages.success(request, f"Vitals logged successfully! AI Risk Assessment: {risk_level}")

        except Exception as e:
            messages.error(request, f"Error saving vitals: {str(e)}")

    return redirect('patient_dashboard')


@login_required
def doctor_dashboard(request):
    try:
        current_doctor = request.user.doctor_profile 
        patients = Patient.objects.filter(doctor=current_doctor)
        active_sos_alerts = EmergencyAlert.objects.filter(doctor=current_doctor, is_resolved=False).order_by('-created_at')
        

        today = timezone.now().date()
        weekly_schedules = Appointment.objects.filter(
            doctor=current_doctor,
            scheduled_date__gte=today
        ).order_by('scheduled_date', 'scheduled_time')

    except DoctorProfile.DoesNotExist:
        current_doctor = None
        patients = Patient.objects.none()
        active_sos_alerts = EmergencyAlert.objects.none()
        weekly_schedules = Appointment.objects.none()

    context = {
        'doctor': current_doctor,
        'patients': patients,
        'total_patients': patients.count(),
        'active_sos_alerts': active_sos_alerts,
        'weekly_schedules': weekly_schedules,  # Template-ലേക്ക് weekly_schedules അയക്കുന്നു
    }
    return render(request, 'doctor_dashboard.html', context)

@login_required
def patient_modal(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    return render(request, 'partials/patient_modal_partial.html', {'patient': patient})


def home_view(request):
    return render(request, 'home.html')


@login_required
def upload_report_view(request):
    if request.method == 'POST':
        report_file = request.FILES.get('report_file')

        if not report_file:
            messages.error(request, "Please select a file before clicking Analyze.")
            return redirect('patient_dashboard')

        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_ext = report_file.name.lower()[report_file.name.rfind('.'):]
        if file_ext not in allowed_extensions:
            messages.error(request, "Invalid file format. Please upload a PDF, PNG, or JPEG file.")
            return redirect('patient_dashboard')

        try:
            patient_profile = Patient.objects.get(user=request.user)

            # Mock AI Extraction Logic (മരുന്ന്/ലാബ് റിപ്പോർട്ടിലെ സാമ്പിൾ അനാളിസിസ്)
            summary_text = f"Report '{report_file.name}' analyzed: Key clinical parameters extracted. Elevated Fasting Glucose and Cholesterol flags detected."
            status_text = "Elevated Risk Flags Detected"
            flags = [
                {'metric': 'Fasting Blood Sugar', 'val': '105.0 mg/dL', 'status': 'HIGH'},
                {'metric': 'Total Cholesterol', 'val': '225.0 mg/dL', 'status': 'HIGH'},
                {'metric': 'LDL Cholesterol', 'val': '145.0 mg/dL', 'status': 'HIGH'},
                {'metric': 'HbA1c', 'val': '5.9%', 'status': 'ELEVATED'}
            ]

            # Database-ലേക്ക് റിപ്പോർട്ട് സേവ് ചെയ്യുന്നു
            DiagnosticReport.objects.create(
                patient=patient_profile,
                report_file=report_file,
                summary=summary_text,
                status_flag=status_text,
                flagged_data=flags
            )

            messages.success(request, f"Report '{report_file.name}' analyzed and saved successfully!")

        except Patient.DoesNotExist:
            messages.error(request, "Patient profile not found.")
        except Exception as e:
            messages.error(request, f"Failed to process report: {str(e)}")

        return redirect('patient_dashboard')

    return redirect('patient_dashboard')

@login_required
def vitals_history_api(request):
    try:
        patient = Patient.objects.get(user=request.user)
        vitals_qs = PatientVital.objects.filter(patient=patient).order_by('-logged_at')[:10]
        vitals = reversed(list(vitals_qs)) 

        data = {
            'labels': [v.logged_at.strftime('%b %d, %H:%M') for v in vitals],
            'systolic': [v.systolic_bp for v in vitals],
            'diastolic': [v.diastolic_bp for v in vitals],
            'glucose': [v.blood_sugar for v in vitals],
            'hr': [v.heart_rate for v in vitals],
            'spo2': [v.spo2_level for v in vitals],
        }
    except Patient.DoesNotExist:
        data = {'labels': [], 'systolic': [], 'diastolic': [], 'glucose': [], 'hr': [], 'spo2': []}

    script_response = f"""
    <script>
        if (window.updateVitalsChart) {{
            window.updateVitalsChart({json.dumps(data)});
        }}
    </script>
    """
    return HttpResponse(script_response)

@login_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    latest_vital = PatientVital.objects.filter(patient=patient).order_by('-logged_at').first()
    
    context = {
        'patient': patient,
        'latest_vital': latest_vital,
    }
    return render(request, 'patient_detail.html', context)
    
@login_required
def add_medication_view(request, patient_id):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, id=patient_id)
        med_name = request.POST.get('medicine_name', '').strip()
        dosage = request.POST.get('dosage', '').strip()
        timing = request.POST.get('timing', 'Morning')

        if med_name and dosage:
            Medication.objects.create(
                patient=patient,
                medicine_name=med_name,
                dosage=dosage,
                timing=timing
            )
            messages.success(request, f"Prescription added for {patient.name}!")
        else:
            messages.error(request, "Please fill in all medication details.")

    return redirect('patient_detail', patient_id=patient_id)


@login_required
def toggle_medication_view(request, med_id):
    medication = get_object_or_404(Medication, id=med_id)
    today = timezone.now().date()

    if not medication.is_taken_today or medication.last_taken_date != today:
        medication.is_taken_today = True
        medication.last_taken_date = today
    else:
        medication.is_taken_today = False

    medication.save()
    return redirect('patient_dashboard')    

@login_required
def create_appointment_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    doctor = get_object_or_404(DoctorProfile, user=request.user)

    if request.method == 'POST':
        scheduled_date = request.POST.get('scheduled_date')
        scheduled_time = request.POST.get('scheduled_time')
        appointment_type = request.POST.get('appointment_type')
        reason = request.POST.get('reason')

        Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            appointment_type=appointment_type,
            reason=reason
        )
        messages.success(request, f"Appointment scheduled for {patient.user.username} successfully!")
        return redirect('patient_detail', patient_id=patient.id)

    return redirect('patient_detail', patient_id=patient.id)

@login_required
def schedule_appointment_view(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        scheduled_date = request.POST.get('scheduled_date')
        scheduled_time = request.POST.get('scheduled_time')
        appointment_type = request.POST.get('appointment_type', 'Follow-up')
        reason = request.POST.get('reason', '')

        try:
            current_doctor = request.user.doctor_profile
            patient = Patient.objects.get(id=patient_id)

            # Save to Database
            Appointment.objects.create(
                doctor=current_doctor,
                patient=patient,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                appointment_type=appointment_type,
                reason=reason,
                status='Confirmed'
            )
            messages.success(request, "Schedule created successfully!")
        except (DoctorProfile.DoesNotExist, Patient.DoesNotExist) as e:
            messages.error(request, f"Error creating schedule: {str(e)}")
            
    return redirect('doctor_dashboard')

@csrf_exempt
@login_required
def trigger_sos_alert(request):
    if request.method == "POST":
        try:
            patient = Patient.objects.get(user=request.user)
            doctor = patient.doctor 
            
            # If patient is not linked to a doctor, assign first available doctor or default
            if not doctor:
                doctor = DoctorProfile.objects.first()

            if doctor:
                EmergencyAlert.objects.create(
                    patient=patient,
                    doctor=doctor,
                    alert_type='SOS',
                    message=f"EMERGENCY: {patient.name} pressed the SOS button!"
                )
                messages.error(request, "SOS Alert sent to Doctor!")
        except Exception as e:
            messages.error(request, f"Failed to send SOS: {str(e)}")
            
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def check_emergencies(request):
    try:
        doctor = request.user.doctor_profile
        active_alerts = EmergencyAlert.objects.filter(doctor=doctor, is_resolved=False).order_by('-created_at')
        
        if active_alerts.exists():
            alerts_html = ""
            for alert in active_alerts:
                local_time = timezone.localtime(alert.created_at)
                formatted_time = local_time.strftime('%b %d, %Y - %I:%M %p')
                alerts_html += f"""
                <div id="alert-card-{alert.id}" class="mb-4 p-4 bg-red-600/20 border-2 border-red-500 rounded-2xl flex items-center justify-between shadow-lg shadow-red-500/20">
                    <div class="flex items-center space-x-3">
                        <span class="text-3xl animate-bounce">🚨</span>
                        <div>
                            <h4 class="font-extrabold text-red-400 text-sm uppercase tracking-wide">EMERGENCY SOS ALERT!</h4>
                            <p class="text-xs text-white font-medium">{alert.message}</p>
                            <p class="text-[10px] text-slate-400 mt-0.5">{formatted_time}</p>
                        </div>
                    </div>
                    <button onclick="resolveSosAlert({alert.id})" 
                            class="px-3.5 py-1.5 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl text-xs transition shadow-md cursor-pointer">
                        Acknowledge & Resolve
                    </button>
                </div>
                """
            return HttpResponse(alerts_html)
    except DoctorProfile.DoesNotExist:
        pass
    return HttpResponse("")

@login_required
def resolve_alert(request, alert_id):
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    alert.is_resolved = True
    alert.save()
    return JsonResponse({'status': 'success', 'alert_id': alert_id})

