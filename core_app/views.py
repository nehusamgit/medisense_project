import re
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import Patient, DoctorProfile
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
            messages.error(request, "please enter the fields....")
            return render(request, 'register.html')

        # 2. Full Name Validation (First & Last name required)
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

        # 7. Create User & Profile
        try:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])

            # Account starts inactive until email activation link is clicked
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )

            if role == 'doctor':
                DoctorProfile.objects.create(user=user, age=age)
            else:
                Patient.objects.create(user=user, name=full_name, age=age)
                # Only save report if registered as Patient
                if report_file:
                    MedicalReport.objects.create(
                        user=user,
                        title=report_file.name,
                        report_file=report_file
                    )

            # Generate Activation URL
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            verify_url = request.build_absolute_uri(
                reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            )

            # Send Email (Printed in terminal)
            send_mail(
                subject="MediSense - Verify Your Email",
                message=f"Hi {first_name},\n\nPlease click the link below to activate your account:\n{verify_url}",
                from_email="noreply@medisense.com",
                recipient_list=[email],
                fail_silently=False,
            )

            # Show Success Message & Redirect to Login Page (NOT Dashboard)
            messages.success(request, "Registration successful! Please check your terminal/email to activate your account.")
            return redirect('login')

        except Exception as e:
            messages.error(request, f"Database Error: {str(e)}")
            return render(request, 'register.html')

    return render(request, 'register.html')

def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your email has been verified! You can now log in.")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid or has expired.")
        return redirect('login')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'login.html')

        # Check if account exists but isn't active (unverified email)
        try:
            user_obj = User.objects.get(username=username)
            if not user_obj.is_active:
                messages.error(request, "Your account is not verified yet. Please check your terminal/email for the activation link.")
                return render(request, 'login.html')
        except User.DoesNotExist:
            pass  # Fall through to standard authentication failure below

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, 'doctor_profile'):
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')
    

@login_required
def patient_dashboard(request):
    ai_insight = request.session.get('latest_ai_insight', None)
    
    context = {
        'ai_insight': ai_insight
    }
    return render(request, 'patient_dashboard.html', context)

@login_required
def doctor_dashboard(request):
    return render(request, 'doctor_dashboard.html')

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
            # Simulated AI extraction payload based on report analysis
            # (Replace this mock dict with your actual AI parser output when ready)
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

            # Store in session so patient_dashboard template can render it
            request.session['latest_ai_insight'] = ai_insights

            messages.success(request, f"Report '{report_file.name}' analyzed successfully!")

        except Exception as e:
            messages.error(request, f"Failed to process report: {str(e)}")

        return redirect('patient_dashboard')

    return redirect('patient_dashboard')