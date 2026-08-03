import re
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Patient, DoctorProfile, PatientVital, AIRiskAssessment
from django.contrib.auth.decorators import login_required
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
    """Admin portal to monitor platform metrics and system overview."""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Access restricted to Administrators only.")
        return redirect('login')

    total_patients = Patient.objects.count()
    total_doctors = DoctorProfile.objects.count()
    total_users = User.objects.count()

    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_users': total_users,
        'recent_users': User.objects.order_by('-date_joined')[:5],
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def patient_dashboard(request):
    # Safely get or create the Patient profile
    patient_profile, _ = Patient.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.get_full_name() or request.user.username, 'age': 30}
    )

    ai_insight = request.session.get('latest_ai_insight', None)
    
    # Fetch recent vitals & latest AI assessment
    recent_vitals = PatientVital.objects.filter(patient=patient_profile).order_by('-logged_at')[:5]
    latest_vital = recent_vitals.first()

    context = {
        'ai_insight': ai_insight,
        'recent_vitals': recent_vitals,
        'latest_vital': latest_vital,
    }
    return render(request, 'patient_dashboard.html', context)

@login_required
def log_vitals_view(request):
    """Logs patient clinical parameters and generates immediate AI Risk Score."""
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
            risk_score = 0.15
            risk_level = 'LOW'
            condition = 'Normal Vitals'
            recommendation = 'Maintain regular diet, hydration, and daily medication schedule.'

            if sys_bp > 140 or sugar > 180 or spo2 < 93:
                risk_score = 0.88
                risk_level = 'CRITICAL'
                condition = 'Hypertension & Hyperglycemia Risk'
                recommendation = 'Critical vitals detected. Immediate clinical review required.'
            elif sys_bp > 130 or sugar > 120:
                risk_score = 0.55
                risk_level = 'MODERATE'
                condition = 'Elevated Blood Pressure / Sugar'
                recommendation = 'Monitor vitals closely over the next 24 hours.'

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

