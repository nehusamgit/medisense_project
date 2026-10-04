import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from core_app.models import Patient, DoctorProfile, Medication

class MedicationDailyIntakeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testpatient',
            email='patient@test.com',
            password='Password123!',
            first_name='John',
            last_name='Doe'
        )
        self.doctor_user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='Password123!',
            first_name='Dr',
            last_name='Smith',
            is_staff=True
        )
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)
        self.patient = Patient.objects.create(
            user=self.user,
            name='John Doe',
            age=32,
            phone='919876543210',
            doctor=self.doctor
        )
        self.medication = Medication.objects.create(
            patient=self.patient,
            prescribed_by=self.doctor,
            medicine_name='Metformin',
            dosage='500mg',
            timing='Morning'
        )

    def test_single_click_intake_today(self):
        self.client.login(username='testpatient', password='Password123!')
        today = timezone.now().date()

        # Initial state: not taken
        self.assertFalse(self.medication.is_taken_today)
        self.assertIsNone(self.medication.last_taken_date)
        self.assertFalse(self.medication.is_taken_for_today)

        # 1. Click to take medication
        response = self.client.post(f'/patient/toggle-medication/{self.medication.id}/')
        self.assertRedirects(response, '/patient/')

        self.medication.refresh_from_db()
        self.assertTrue(self.medication.is_taken_today)
        self.assertEqual(self.medication.last_taken_date, today)
        self.assertTrue(self.medication.is_taken_for_today)

        # 2. Click again on the same day - should remain taken and not toggle back to False
        response2 = self.client.post(f'/patient/toggle-medication/{self.medication.id}/')
        self.assertRedirects(response2, '/patient/')

        self.medication.refresh_from_db()
        self.assertTrue(self.medication.is_taken_today)
        self.assertEqual(self.medication.last_taken_date, today)

    def test_dynamic_reset_on_next_day(self):
        self.client.login(username='testpatient', password='Password123!')
        yesterday = timezone.now().date() - datetime.timedelta(days=1)

        # Simulate medication was taken yesterday
        self.medication.is_taken_today = True
        self.medication.last_taken_date = yesterday
        self.medication.save()

        self.assertFalse(self.medication.is_taken_for_today)

        # When patient visits the dashboard on the new day, it auto-resets
        response = self.client.get('/patient/')
        self.assertEqual(response.status_code, 200)

        self.medication.refresh_from_db()
        self.assertFalse(self.medication.is_taken_today)
        self.assertEqual(self.medication.last_taken_date, yesterday)

        # The button is re-enabled for today, so patient can take it for today
        response_take = self.client.post(f'/patient/toggle-medication/{self.medication.id}/')
        self.assertRedirects(response_take, '/patient/')

        self.medication.refresh_from_db()
        self.assertTrue(self.medication.is_taken_today)
        self.assertEqual(self.medication.last_taken_date, timezone.now().date())
