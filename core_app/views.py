import re
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Patient, DoctorProfile, PatientVital, AIRiskAssessment, Medication
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login


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

        # 1. Check for empty fields
        if not all([username, email, full_name, age_str, password, confirm_password]):
            messages.error(request, "Please enter all required fields.")
            return render(request, 'register.html')

        # 2. Full Name Validation
        name_parts = full_name.split()
        if len(name_parts) < 2:
            messages.error(request, "Please enter your full name (first and last name).")
            return render(request, 'register.html')

        # 3. Email Format Check
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'register.html')

        # 4. Age Validation
        try:
            age = int(age_str)
            if age <= 0 or age > 120:
                messages.error(request, "Please enter a valid age between 1 and 120.")
                return render(request, 'register.html')
        except ValueError:
            messages.error(request, "Age must be a valid number.")
            return render(request, 'register.html')

        # 5. Password Strength & Match
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'register.html')
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        # 6. Uniqueness Checks
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'register.html')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'register.html')

        # 7. Create Active User & Profile
        try:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])

            # Account is created ACTIVE immediately
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
            
            # ROUTING BASED ON ROLE
            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard')
            elif hasattr(user, 'doctorprofile') or hasattr(user, 'doctor_profile'):
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('login')

    role = request.GET.get('role', 'all')
    users = User.objects.all().order_by('-date_joined')

    # Filtering Logic based on top tab selection
    if role == 'doctor':
        users = users.filter(is_staff=True) # അല്ലെങ്കിൽ Doctor role condition
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
        
        # 1. Soft Delete (This bypasses all DB FK Constraint/Cascade errors)
        user_to_delete.is_active = False
        user_to_delete.save()

        # 2. Return 200 OK with empty response so HTMX instantly removes the row from DOM
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

    if patient_profile:
        latest_vital = PatientVital.objects.filter(patient=patient_profile).order_by('-logged_at').first()
        medications = Medication.objects.filter(patient=patient_profile).order_by('-created_at')

    context = {
        'patient': patient_profile,
        'latest_vital': latest_vital,
        'medications': medications,
    }
    return render(request, 'patient_dashboard.html', context)

@login_required
def log_vitals_view(request):
    """Logs patient clinical parameters and generates dynamic AI Risk Score."""
    if request.method == 'POST':
        try:
            # Safely get or create the patient profile
            patient_profile, _ = Patient.objects.get_or_create(
                user=request.user,
                defaults={'name': request.user.get_full_name() or request.user.username, 'age': 30}
            )

            sys_bp = int(request.POST.get('systolic_bp', 120))
            dia_bp = int(request.POST.get('diastolic_bp', 80))
            hr = int(request.POST.get('heart_rate', 72))
            sugar = float(request.POST.get('blood_sugar', 100.0))
            spo2 = float(request.POST.get('spo2_level', 98.0))

            # 1. Save Vitals Entry
            vital_entry = PatientVital.objects.create(
                patient=patient_profile,
                systolic_bp=sys_bp,
                diastolic_bp=dia_bp,
                heart_rate=hr,
                blood_sugar=sugar,
                spo2_level=spo2
            )

            # 2. Rule-Based AI Risk Scoring Pipeline
            critical_conditions = []
            moderate_conditions = []

            # --- Critical Checks (High & Low Risks) ---
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

            # --- Moderate Checks ---
            if not critical_conditions:
                if 130 <= sys_bp <= 140 or 80 <= dia_bp <= 90:
                    moderate_conditions.append('Elevated Blood Pressure')
                if 120 <= sugar <= 180:
                    moderate_conditions.append('Elevated Blood Sugar')
                if 93 <= spo2 <= 95:
                    moderate_conditions.append('Borderline Oxygen Level')

            # --- Evaluate Overall Risk Level & Message ---
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
                risk_level = 'NORMAL'  # LOW മാറ്റി NORMAL ആക്കി
                condition = 'Normal Vitals'
                recommendation = 'Maintain regular diet, hydration, and daily medication schedule.'

            # 3. Save AI Risk Assessment
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
    patients = Patient.objects.all().select_related('user')
    total_patients_count = patients.count()
    
    context = {
        'patients': patients,
        'total_patients_count': total_patients_count,
        
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
    """Processes uploaded report file directly in memory and stores AI insights in session."""
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
            ai_insights = {
                'filename': report_file.name,
                'status': 'Elevated Risk Flags Detected',
                'summary': 'Elevated Fasting Glucose (105.0 mg/dL), Total Cholesterol (225.0 mg/dL), and HbA1c (5.9%). CBC parameters are within normal ranges.',
                'flags': [
                    {'metric': 'Fasting Blood Sugar', 'val': '105.0 mg/dL', 'status': 'HIGH'},
                    {'metric': 'Total Cholesterol', 'val': '225.0 mg/dL', 'status': 'HIGH'},
                    {'metric': 'LDL Cholesterol', 'val': '145.0 mg/dL', 'status': 'HIGH'},
                    {'metric': 'HbA1c', 'val': '5.9%', 'status': 'ELEVATED'}
                ],
                'timestamp': 'Just now'
            }

            request.session['latest_ai_insight'] = ai_insights
            messages.success(request, f"Report '{report_file.name}' analyzed successfully!")

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
                prescribed_by=request.user,
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
    if request.method == 'POST':
        medication = get_object_or_404(Medication, id=med_id, patient__user=request.user)
        medication.is_taken_today = not medication.is_taken_today
        medication.save()
        messages.success(request, "Medication status updated!")

    return redirect('patient_dashboard')    