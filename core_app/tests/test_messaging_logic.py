from django.test import TestCase, Client
from django.contrib.auth.models import User
from core_app.models import Patient, DoctorProfile, SecureMessage

class SecureMessagingChatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient_user = User.objects.create_user(
            username='chat_patient',
            email='patient_chat@test.com',
            password='Password123!',
            first_name='Rahul',
            last_name='Kumar'
        )
        self.doctor_user = User.objects.create_user(
            username='chat_doctor',
            email='doctor_chat@test.com',
            password='Password123!',
            first_name='Ananya',
            last_name='Iyer',
            is_staff=True
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='Cardiology'
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            name='Rahul Kumar',
            age=35,
            phone='919876543210',
            doctor=self.doctor
        )

    def test_patient_can_view_inbox_and_see_doctor_thread(self):
        self.client.login(username='chat_patient', password='Password123!')
        response = self.client.get('/inbox/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dr. Ananya Iyer')
        self.assertContains(response, 'Cardiology')

    def test_patient_can_send_message_to_doctor(self):
        self.client.login(username='chat_patient', password='Password123!')
        response = self.client.post('/inbox/', {
            'patient_id': self.patient.id,
            'subject': 'Medication Question',
            'body': 'Hello Dr. Ananya, should I take Metformin before or after dinner?'
        })
        self.assertRedirects(response, f'/inbox/{self.patient.id}/')

        msg = SecureMessage.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.sender, self.patient_user)
        self.assertEqual(msg.receiver, self.doctor_user)
        self.assertEqual(msg.subject, 'Medication Question')
        self.assertEqual(msg.body, 'Hello Dr. Ananya, should I take Metformin before or after dinner?')
        self.assertFalse(msg.is_read)

    def test_doctor_sees_message_and_marks_read_on_view(self):
        # Create unread message from patient
        SecureMessage.objects.create(
            patient=self.patient,
            sender=self.patient_user,
            receiver=self.doctor_user,
            subject='Symptoms Update',
            body='Feeling mild dizziness in the morning.',
            is_read=False
        )

        self.client.login(username='chat_doctor', password='Password123!')
        response = self.client.get(f'/inbox/{self.patient.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feeling mild dizziness in the morning.')

        # Verify it was automatically marked as read
        msg = SecureMessage.objects.filter(patient=self.patient).first()
        self.assertTrue(msg.is_read)

    def test_doctor_can_reply_to_patient(self):
        self.client.login(username='chat_doctor', password='Password123!')
        response = self.client.post('/inbox/', {
            'patient_id': self.patient.id,
            'subject': 'Treatment Progress',
            'body': 'Please check your blood pressure twice daily and drink enough fluids.'
        })
        self.assertRedirects(response, f'/inbox/{self.patient.id}/')

        reply = SecureMessage.objects.filter(sender=self.doctor_user).first()
        self.assertIsNotNone(reply)
        self.assertEqual(reply.receiver, self.patient_user)
        self.assertEqual(reply.body, 'Please check your blood pressure twice daily and drink enough fluids.')
