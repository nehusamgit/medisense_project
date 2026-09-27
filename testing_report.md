# MediSense Automated Testing Report

**Date:** September 27, 2026
**Framework:** Django Test Runner + Selenium WebDriver
**Scope:** Core Web Application Functional Testing

## Overview
This report details the automated Selenium UI testing performed on the **MediSense** platform. The testing suite focuses on simulating end-to-end user workflows for both Patients and Doctors to ensure the critical paths of the application function as expected.

---

## Test Suites Executed

### Suite 1: Core System & SOS Alerts (`test_medi_sense_all.py`)
This suite focuses on the critical emergency alert functionality and basic user access.

1. **Patient Login Flow (`test_01_patient_login_success`)**
   - **Action:** Navigates to the login page, enters patient credentials, and submits the form.
   - **Expected Result:** Successful authentication and redirection to the `/patient/` dashboard.
   - **Status:** ✅ **PASSED**

2. **Trigger Emergency SOS (`test_02_trigger_sos_alert`)**
   - **Action:** Logs in as a patient, locates the "EMERGENCY SOS" button on the dashboard, clicks it, and accepts the browser confirmation alert.
   - **Expected Result:** The system processes the alert and redirects back to the dashboard without errors.
   - **Status:** ✅ **PASSED**

3. **Doctor Alert Acknowledgement (`test_03_doctor_view_and_acknowledge_sos`)**
   - **Action:** Logs in as a doctor and accesses the doctor dashboard.
   - **Expected Result:** Dashboard loads successfully, and active SOS alerts from patients are visible.
   - **Status:** ✅ **PASSED**

---

### Suite 2: Extended Functionality (`test_extended_functionality.py`)
This suite tests patient onboarding and the daily medical logging processes.

4. **Patient Registration & Vitals Input (`test_01_patient_registration_and_vitals`)**
   - **Action:** Fills out the registration form with valid data, registers a new account, logs in, and submits a complete set of daily vitals (BP, Heart Rate, SpO2, Glucose).
   - **Expected Result:** Registration redirects to login; vitals form submission is successful and redirects back to the dashboard.
   - **Status:** ✅ **PASSED**

5. **Doctor Login & View (`test_02_doctor_login_and_view`)**
   - **Action:** Authenticates a doctor profile.
   - **Expected Result:** Validates that the doctor's specific routing and dashboard access are correctly enforced.
   - **Status:** ✅ **PASSED**

---

## Execution Summary
- **Total Tests Run:** 5
- **Tests Passed:** 5
- **Tests Failed:** 0
- **Execution Time:** ~76.8 seconds (Headless Mode)

## Notes for Project Guide Review
- **Visibility Update:** The tests were initially run in "headless" mode (running in the background without opening a physical browser window), which is why no browser popped up on the screen during the first run.
- The testing scripts have now been updated to remove headless mode. Future runs of `python manage.py test` will physically open Google Chrome and perform the automated clicks on-screen, which is ideal for a live demonstration.
