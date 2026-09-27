from django import forms
from django.contrib.auth.models import User
from .models import Patient, MedicationLog, DoctorProfile, SecureMessage

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'phone', 'condition', 'doctor']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Patient Name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
        }

class MedicationLogForm(forms.ModelForm):
    class Meta:
        model = MedicationLog
        fields = ['patient', 'morning_dose', 'afternoon_dose']

class UserRegistrationForm(forms.ModelForm):
    ROLE_CHOICES = (
        ('doctor', 'Doctor/Medical Professional'),
        ('patient', 'Patient'),
    )
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm password'
    }))
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={
        'class': 'form-select'
    }))

    lab_report = forms.FileField(
        required=False,
        label="Upload Lab Report (PDF/Images)",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file text-sm text-slate-400',
            'accept': 'application/pdf,image/*'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data


class SecureMessageForm(forms.ModelForm):
    SUBJECT_CHOICES = [
        ('Appointment follow-up', 'Appointment follow-up'),
        ('Medication question', 'Medication question'),
        ('Prescription refill', 'Prescription refill'),
        ('Lab report discussion', 'Lab report discussion'),
        ('Symptoms update', 'Symptoms update'),
        ('Treatment progress', 'Treatment progress'),
        ('General health question', 'General health question'),
    ]

    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-400',
        }),
    )

    class Meta:
        model = SecureMessage
        fields = ['subject', 'body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none focus:border-cyan-400',
                'placeholder': 'Write your secure message...',
                'rows': 8,
            }),
        }