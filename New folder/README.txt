RESUMind AI - Login Version

LOGIN DETAILS
User:
  Username: user
  Password: user123

Admin:
  Username: admin
  Password: admin123

ROUTING
1. Open http://127.0.0.1:5000/
2. You will be sent to User Login.
3. User login opens the RESUMind home page.
4. All main pages and API processing routes require a login session.
5. Admin Dashboard requires the separate Admin Login.
6. /logout clears the session.

FILES
- app.py = modified Flask application with authentication
- templates/user_login.html = user login
- templates/admin_login.html = admin login
- templates/index.html = current project home page (if source template was available)
- templates/admin.html = current admin dashboard (if source template was available)

IMPORTANT
These credentials are intended for a college/demo project. For a real deployment,
use a database, password hashing, and a strong secret key stored outside the source code.
