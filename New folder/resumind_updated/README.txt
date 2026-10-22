RESUMind AI — COMPANY APPROACH RESUME APPLICATION FEATURE
========================================================

WHAT THE NEW FEATURE DOES
1. The user opens Company Approach and enters full name, email, target company, and job role.
2. The user uploads a PDF resume and clicks "Submit Resume & Find Suitable Companies".
3. The resume is saved as an application in the local SQLite database and appears in the ADMINISTRATOR DASHBOARD only.
4. The Company Approach page continues to show matching-company recommendations.
5. The administrator signs in, opens the Resume Applications section, views/downloads the resume, selects a status, and clicks "Save Status & Send Email".
6. Status choices include Selected, Prepare for Interview, Not Selected, and Submitted. The administrator may type a custom email message.
7. Status changes are saved even if SMTP is not configured. Real emails require SMTP settings below.

FILES
- app.py
- requirements.txt
- templates/ (all HTML pages)
- static/style.css
- uploads/ is created automatically when the app runs
- users.db is created automatically when the app runs; applications are stored there

RUN ON WINDOWS
1. Extract this ZIP file.
2. Open the extracted project folder containing app.py.
3. Click File Explorer's address bar, type cmd, and press Enter.
4. Run: python -m pip install -r requirements.txt
5. Run: python app.py
6. Keep Command Prompt open and visit http://127.0.0.1:5000/
If python is not recognized, use `py` instead of `python`.

TEST LOGINS
- User: username user, password user123
- Admin: visit http://127.0.0.1:5000/admin-login
  username admin, password admin123

TEST THE FEATURE
1. Sign in as user.
2. Open Company Approach from the home page.
3. Fill in name, email, company, role, and upload a PDF resume.
4. Click "Submit Resume & Find Suitable Companies".
5. Open http://127.0.0.1:5000/admin-login and sign in as admin.
6. The application should appear in "Resume Applications & Email Status Updates" on the administrator dashboard.
7. Choose Selected or Prepare for Interview, optionally enter a message, and click "Save Status & Send Email".

REAL EMAIL SETUP (GMAIL EXAMPLE)
Use a Google App Password, not your normal Gmail password. In Windows PowerShell, set:
$env:RESUMIND_SMTP_HOST="smtp.gmail.com"
$env:RESUMIND_SMTP_PORT="587"
$env:RESUMIND_SMTP_USER="your-email@gmail.com"
$env:RESUMIND_SMTP_PASSWORD="your-16-character-app-password"
$env:RESUMIND_FROM_EMAIL="your-email@gmail.com"
python app.py

If SMTP is not configured, the dashboard will display a message saying the status was saved but the email could not be sent. This project uses demo login credentials; secure them before any public deployment.
