import io
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from reportlab.pdfgen import canvas
from core_app.models import Patient, DiagnosticReport
from core_app.ai_services import extract_report_offline_rules

def _create_sample_pdf_bytes():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "CLINICAL LABORATORY DIAGNOSTIC REPORT")
    c.drawString(100, 720, "Fasting Blood Sugar: 145.0 mg/dL")
    c.drawString(100, 690, "HbA1c: 7.1 %")
    c.drawString(100, 660, "Total Cholesterol: 235.0 mg/dL")
    c.drawString(100, 630, "Serum Creatinine: 0.8 mg/dL")
    c.save()
    buf.seek(0)
    return buf.getvalue()

class DiagnosticReportAnalysisTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testpatient',
            password='password123',
            email='patient@test.com'
        )
        self.patient = Patient.objects.create(
            user=self.user,
            name='Test Patient',
            age=45,
            phone='919876543210'
        )
        self.client = Client()
        self.client.login(username='testpatient', password='password123')

    def test_offline_extractor_extracts_and_flags_values(self):
        pdf_bytes = _create_sample_pdf_bytes()
        result = extract_report_offline_rules(pdf_bytes, 'lab_sample.pdf')
        
        self.assertIn('summary', result)
        self.assertIn('status_flag', result)
        self.assertIn('flagged_data', result)
        
        metrics = {item['metric'].lower(): item for item in result['flagged_data']}
        
        self.assertIn('fasting blood sugar', metrics)
        self.assertEqual(metrics['fasting blood sugar']['status'], 'HIGH')
        self.assertIn('hba1c', metrics)
        self.assertEqual(metrics['hba1c']['status'], 'HIGH')

    def test_upload_report_view_saves_diagnostic_report_with_ai(self):
        pdf_bytes = _create_sample_pdf_bytes()
        sample_file = SimpleUploadedFile(
            "blood_work.pdf",
            pdf_bytes,
            content_type="application/pdf"
        )

        response = self.client.post(reverse('upload_report'), {'report_file': sample_file}, follow=True)
        self.assertEqual(response.status_code, 200)

        report = DiagnosticReport.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(report)
        self.assertTrue(len(report.flagged_data) > 0)
        self.assertIn('blood_work', report.report_file.name)
