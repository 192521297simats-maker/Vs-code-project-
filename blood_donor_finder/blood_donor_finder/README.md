# LifeLine Finder — Emergency Blood Donor Finder

A beginner-friendly Flask + SQLite college project for connecting people with potential blood donors.

## Features
- Donor registration and login with hashed passwords
- Donor search by blood group and city
- Submit and track blood requests
- Donor availability controls
- Admin dashboard for donor and request management
- Responsive red-and-white interface
- SQLite database created automatically on first run

## Requirements
- Python 3.9 or newer
- VS Code (recommended)

## Run on Windows
1. Extract the ZIP file.
2. Open the `blood_donor_finder` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. (Recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
5. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open `http://127.0.0.1:5000/` in your browser.

The `blood_donor.db` SQLite database is generated automatically.

## Demo admin login
- Email: `admin@bloodfinder.local`
- Password: `Admin123!`

Change this demo password and configure a strong `SECRET_KEY` before any real or public deployment. This starter project is intended for local educational demonstration; it has not been security-audited for production use.

## Main routes
- `/` — Home
- `/register` — Donor registration
- `/login` — Login
- `/find-donor` — Search donors
- `/request-blood` — Submit a request
- `/requests` — Community requests
- `/dashboard` — Signed-in user's dashboard
- `/admin` — Admin dashboard

## Important safety note
This app is a connection tool, not a medical service. It does not validate donor eligibility, blood compatibility, or the legitimacy of requests. For emergencies, contact a hospital, emergency services, or a licensed blood bank immediately. Verify all information through qualified medical professionals.
