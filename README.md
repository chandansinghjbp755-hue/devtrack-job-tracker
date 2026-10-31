# DevTrack 2.0 — Job Application Tracker

DevTrack is a full-stack web application for organizing a job search. Each registered user gets a private application dashboard.

## Features
- User registration, login and logout
- Password hashing (Werkzeug)
- User-specific application records
- Add job applications with company, role, location, job type and notes
- Track statuses: Applied, Interview, Offer and Rejected
- Search by company or role and filter by status
- Store interview dates and show upcoming interviews
- Set follow-up dates and see reminders, including overdue follow-ups
- Save a job posting URL with each application
- Edit application details and keep an interview-preparation checklist and notes
- Export your own applications and preparation notes as CSV
- Dashboard metrics and pipeline progress bars
- Responsive layout for desktop and mobile
- Software engineer job-search guide with application steps and job-board links
- Show/hide password control on sign-in and registration
- CSRF tokens on all form submissions
- SQLite database with parameterized SQL queries

## Tech stack
Python, Flask, SQLite, HTML5, CSS3, Jinja2.

## Run in VS Code on Windows

### 1. Install prerequisites
Install Python 3.10+ and Visual Studio Code. During Python installation, enable **Add Python to PATH**.

### 2. Open the project
In VS Code choose **File → Open Folder** and select the extracted `DevTrack_2_0_Full_Project` folder (or the folder where you saved this project).

### 3. Open the terminal
Choose **Terminal → New Terminal**.

### 4. Create a virtual environment
```powershell
python -m venv venv
```

### 5. Activate it
PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```
If PowerShell blocks activation, use Command Prompt terminal instead:
```bat
venv\Scripts\activate.bat
```

### 6. Install Flask
```bash
python -m pip install -r requirements.txt
```

### 7. Set a local session secret
In PowerShell, generate a random secret for this terminal session:
```powershell
$env:DEVTRACK_SECRET = python -c "import secrets; print(secrets.token_hex(32))"
```
Keep this value private. Set `DEVTRACK_SECRET` in the hosting provider's environment settings before deployment. If it is missing, DevTrack uses a temporary random key and prints a warning; sessions will not survive an app restart.

### 8. Start the app
```bash
python app.py
```

### 9. Open in your browser
Visit:
`http://127.0.0.1:5000`

Create your own account from the Register page. Your data is stored locally in `devtrack.db`, which is created automatically.

## Using the application
- Add an application and optionally enter its job URL, interview date and follow-up date.
- Open **Edit / Prep** beside an application to update it and save interview preparation checklist items and notes.
- Check the dashboard's follow-up reminder list for scheduled or overdue follow-ups.
- Choose **Export CSV** to download your own application and preparation data for a spreadsheet.
- The CSV export prefixes spreadsheet formula-like text with an apostrophe to reduce formula-injection risk.

## Screenshots
To document your own demo, run the app with sample data, capture the dashboard and application edit/preparation page, and save the images under `docs/screenshots/`. Avoid including real email addresses, private job-search notes or other personal data in published screenshots.

## Security and deployment
- Every POST form is protected with a session-backed CSRF token.
- Passwords are stored as Werkzeug password hashes; the application never displays or exports passwords.
- The Flask development server runs with debug mode off. Use a production WSGI server for a public deployment.
- Configure a strong, private `DEVTRACK_SECRET` in the hosting environment. Do not commit it.
- If hosting behind HTTPS, set `DEVTRACK_COOKIE_SECURE=true` so session cookies are sent only over HTTPS.
- Do not upload `devtrack.db`, passwords or `.env` files.
- SQLite is suitable for a local portfolio demo; review hosting storage and backup requirements before using it for a public multi-user service.

## Troubleshooting
- If `python` is not recognized, reinstall Python and enable **Add Python to PATH**, then restart VS Code.
- If Flask is missing, activate the virtual environment and run `python -m pip install -r requirements.txt`.
- If the page does not load, check that the terminal still shows the Flask server running.
- Stop the server with `Ctrl + C`.

## Resume entry (only after you run, test and understand it)

**DevTrack 2.0 — Job Application Tracker**
- Developed a multi-user job application tracker using Python, Flask, SQLite, HTML and CSS.
- Implemented secure account registration and login with hashed passwords.
- Built application management features with search, filtering and status updates.
- Added dashboard metrics and upcoming interview tracking.
- Added saved job-posting links and a focused software engineering job-application guide.
- Implemented follow-up reminders, editable application records, interview preparation tracking and CSV export.
- Added CSRF protection and disabled Flask debug mode by default.

**Technologies:** Python, Flask, SQLite, HTML5, CSS3, Jinja2.

## Before publishing to GitHub
- Confirm your database and secrets are excluded by `.gitignore`.
- Add only screenshots with dummy/demo information.
- Review the code and customize the design and features so you can explain your own implementation.
