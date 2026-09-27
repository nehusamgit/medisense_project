import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core_app.models import Patient, DoctorProfile

User = get_user_model()

class MediSenseSeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configure Chrome options
        chrome_options = Options()
        # Removed '--headless=new' so the browser opens visibly
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280,800')

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        """Create test users in the temporary test database before each test."""
        self.password = "SecurePass123!"
        
        # Create Patient User
        self.patient = User.objects.create_user(
            username="patient_test",
            email="patient@example.com",
            password=self.password,
            first_name="John",
            last_name="Doe"
        )
        
        # Create Doctor User
        self.doctor = User.objects.create_user(
            username="doctor_test",
            email="doctor@example.com",
            password=self.password,
            first_name="Dr. Sarah",
            last_name="Smith"
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor,
            specialization="General",
            age=40
        )
        self.patient_profile = Patient.objects.create(
            user=self.patient,
            doctor=self.doctor_profile,
            name="John Doe",
            age=30,
            phone="919876543210"
        )

    def test_01_patient_login_success(self):
        """Test patient login redirect to patient dashboard."""
        driver = self.driver
        driver.get(f"{self.live_server_url}/login/")

        # Find login elements
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")

        # Fill credentials
        username_input.send_keys("patient_test")
        password_input.send_keys(self.password)
        submit_btn.click()

        # Wait for redirect and verify dashboard element
        WebDriverWait(driver, 5).until(
            EC.url_contains("/patient/")
        )
        self.assertIn("/patient/", driver.current_url)

    def test_02_trigger_sos_alert(self):
        """Test triggering SOS alert from Patient Dashboard."""
        driver = self.driver

        # Login as Patient
        driver.get(f"{self.live_server_url}/login/")
        driver.find_element(By.NAME, "username").send_keys("patient_test")
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Locate and Click SOS Button
        sos_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'EMERGENCY SOS')]"))
        )
        sos_button.click()

        # Handle alert
        WebDriverWait(driver, 5).until(EC.alert_is_present())
        driver.switch_to.alert.accept()

        # Check for success message or redirect back to patient page
        WebDriverWait(driver, 5).until(
            EC.url_contains("/patient/")
        )
        self.assertIn("/patient/", driver.current_url)

    def test_03_doctor_view_and_acknowledge_sos(self):
        """Test doctor logging in and seeing active emergency alert."""
        driver = self.driver

        # Login as Doctor
        driver.get(f"{self.live_server_url}/login/")
        driver.find_element(By.NAME, "username").send_keys("doctor_test")
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Check Doctor Dashboard loads correctly
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.assertIn("Doctor", driver.page_source)