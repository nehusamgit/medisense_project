import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core_app.models import Patient, DoctorProfile, EmergencyAlert

User = get_user_model()

class ExtendedSeleniumTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280,800')

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.password = "SecurePass123!"
        
        # Create Doctor User
        self.doctor = User.objects.create_user(
            username="doctor_ext",
            email="doctor_ext@example.com",
            password=self.password,
            first_name="Dr. Ext",
            last_name="Test"
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor,
            specialization="General",
            age=45
        )

    def test_01_patient_registration_and_vitals(self):
        """Test patient registration, login, and logging vitals."""
        driver = self.driver
        driver.get(f"{self.live_server_url}/register/")

        # Fill registration form
        driver.find_element(By.NAME, "first_name").send_keys("Test Patient")
        driver.find_element(By.NAME, "email").send_keys("testpatient@example.com")
        driver.find_element(By.NAME, "age").send_keys("35")
        driver.find_element(By.NAME, "phone").send_keys("919876543210")
        driver.find_element(By.NAME, "username").send_keys("testpatient")
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.NAME, "confirm_password").send_keys(self.password)
        
        # Submit registration
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Should redirect to login
        WebDriverWait(driver, 5).until(EC.url_contains("/login/"))
        
        # Login
        driver.find_element(By.NAME, "username").send_keys("testpatient")
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Redirect to patient dashboard
        WebDriverWait(driver, 5).until(EC.url_contains("/patient/"))

        # Log Vitals
        driver.find_element(By.NAME, "systolic_bp").send_keys("120")
        driver.find_element(By.NAME, "diastolic_bp").send_keys("80")
        driver.find_element(By.NAME, "blood_sugar").send_keys("105")
        driver.find_element(By.NAME, "heart_rate").send_keys("72")
        driver.find_element(By.NAME, "spo2_level").send_keys("98")
        
        # Click submit vitals
        vitals_submit = driver.find_element(By.XPATH, "//button[contains(., 'Submit Daily Vitals')]")
        vitals_submit.click()

        # Check for successful vitals log (page redirects back to dashboard, maybe shows a flash message)
        WebDriverWait(driver, 5).until(EC.url_contains("/patient/"))
        self.assertIn("/patient/", driver.current_url)

    def test_02_doctor_login_and_view(self):
        """Test doctor login and view dashboard."""
        driver = self.driver
        driver.get(f"{self.live_server_url}/login/")
        
        driver.find_element(By.NAME, "username").send_keys("doctor_ext")
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Check Doctor Dashboard loads correctly
        WebDriverWait(driver, 5).until(
            EC.url_contains("/doctor/")
        )
        self.assertIn("/doctor/", driver.current_url)
