from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-for-real-use")
DB_PATH = os.path.join(os.path.dirname(__file__), "blood_donor.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            blood_group TEXT NOT NULL,
            city TEXT NOT NULL,
            phone TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER,
            requester_name TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units INTEGER NOT NULL DEFAULT 1,
            city TEXT NOT NULL,
            hospital TEXT NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'Urgent',
            details TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(requester_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)
        # A local demo admin account is created if it does not exist.
        admin = con.execute("SELECT id FROM users WHERE email = ?", ("admin@bloodfinder.local",)).fetchone()
        if not admin:
            con.execute(
                "INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
                ("Demo Admin", "admin@bloodfinder.local",
                 generate_password_hash("Admin123!"), "admin")
            )

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access is required.", "warning")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    with db() as con:
        donor_count = con.execute("SELECT COUNT(*) FROM donors WHERE available=1").fetchone()[0]
        request_count = con.execute("SELECT COUNT(*) FROM blood_requests WHERE status='Pending'").fetchone()[0]
        fulfilled_count = con.execute("SELECT COUNT(*) FROM blood_requests WHERE status='Fulfilled'").fetchone()[0]
        urgent = con.execute("""SELECT * FROM blood_requests WHERE status='Pending'
                              ORDER BY CASE urgency WHEN 'Critical' THEN 0 WHEN 'Urgent' THEN 1 ELSE 2 END,
                              created_at DESC LIMIT 3""").fetchall()
    return render_template("index.html", donor_count=donor_count, request_count=request_count,
                           fulfilled_count=fulfilled_count, urgent=urgent)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        blood_group = request.form.get("blood_group", "")
        city = request.form.get("city", "").strip()
        phone = request.form.get("phone", "").strip()
        if not all([name, email, password, blood_group, city, phone]):
            flash("Please complete all required fields.", "error")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")
        try:
            with db() as con:
                cur = con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                  (name, email, generate_password_hash(password)))
                con.execute("INSERT INTO donors(user_id,blood_group,city,phone) VALUES(?,?,?,?)",
                            (cur.lastrowid, blood_group, city, phone))
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("admin") if user["role"] == "admin" else url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/find-donor", methods=["GET"])
def find_donor():
    blood_group = request.args.get("blood_group", "").strip()
    city = request.args.get("city", "").strip()
    query = """SELECT d.*, u.name FROM donors d JOIN users u ON u.id=d.user_id WHERE d.available=1"""
    params = []
    if blood_group:
        query += " AND d.blood_group=?"
        params.append(blood_group)
    if city:
        query += " AND LOWER(d.city) LIKE LOWER(?)"
        params.append("%" + city + "%")
    query += " ORDER BY d.city, u.name"
    with db() as con:
        donors = con.execute(query, params).fetchall()
    return render_template("find_donor.html", donors=donors, blood_group=blood_group, city=city)

@app.route("/request-blood", methods=["GET", "POST"])
def request_blood():
    if request.method == "POST":
        data = {
            "requester_name": request.form.get("requester_name", "").strip(),
            "contact_phone": request.form.get("contact_phone", "").strip(),
            "blood_group": request.form.get("blood_group", ""),
            "units": request.form.get("units", "1"),
            "city": request.form.get("city", "").strip(),
            "hospital": request.form.get("hospital", "").strip(),
            "urgency": request.form.get("urgency", "Urgent"),
            "details": request.form.get("details", "").strip()
        }
        if not all([data["requester_name"], data["contact_phone"], data["blood_group"],
                    data["city"], data["hospital"]]):
            flash("Please complete all required fields.", "error")
            return render_template("request_blood.html")
        try:
            units = max(1, min(20, int(data["units"])))
        except ValueError:
            units = 1
        with db() as con:
            con.execute("""INSERT INTO blood_requests
                (requester_id,requester_name,contact_phone,blood_group,units,city,hospital,urgency,details)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (session.get("user_id"), data["requester_name"], data["contact_phone"],
                 data["blood_group"], units, data["city"], data["hospital"], data["urgency"], data["details"]))
        flash("Blood request submitted. Please also contact the hospital or local blood bank directly.", "success")
        return redirect(url_for("requests"))
    return render_template("request_blood.html")

@app.route("/requests")
def requests():
    status = request.args.get("status", "").strip()
    query = "SELECT * FROM blood_requests"
    params = []
    if status in ("Pending", "Accepted", "Fulfilled", "Cancelled"):
        query += " WHERE status=?"
        params.append(status)
    query += """ ORDER BY CASE urgency WHEN 'Critical' THEN 0 WHEN 'Urgent' THEN 1 ELSE 2 END,
                 created_at DESC"""
    with db() as con:
        rows = con.execute(query, params).fetchall()
    return render_template("requests.html", requests=rows, selected_status=status)

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        donor = con.execute("SELECT * FROM donors WHERE user_id=?", (session["user_id"],)).fetchone()
        own_requests = con.execute("SELECT * FROM blood_requests WHERE requester_id=? ORDER BY created_at DESC",
                                   (session["user_id"],)).fetchall()
    return render_template("dashboard.html", donor=donor, own_requests=own_requests)

@app.route("/availability", methods=["POST"])
@login_required
def availability():
    available = 1 if request.form.get("available") == "1" else 0
    with db() as con:
        con.execute("UPDATE donors SET available=? WHERE user_id=?", (available, session["user_id"]))
    flash("Your donor availability has been updated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin")
@login_required
@admin_required
def admin():
    with db() as con:
        donors = con.execute("""SELECT d.*,u.name,u.email FROM donors d JOIN users u ON u.id=d.user_id
                                ORDER BY u.name""").fetchall()
        rows = con.execute("SELECT * FROM blood_requests ORDER BY created_at DESC").fetchall()
        stats = {
            "donors": con.execute("SELECT COUNT(*) FROM donors").fetchone()[0],
            "available": con.execute("SELECT COUNT(*) FROM donors WHERE available=1").fetchone()[0],
            "pending": con.execute("SELECT COUNT(*) FROM blood_requests WHERE status='Pending'").fetchone()[0],
            "fulfilled": con.execute("SELECT COUNT(*) FROM blood_requests WHERE status='Fulfilled'").fetchone()[0]
        }
    return render_template("admin.html", donors=donors, requests=rows, stats=stats)

@app.route("/admin/request/<int:request_id>", methods=["POST"])
@login_required
@admin_required
def update_request(request_id):
    status = request.form.get("status", "Pending")
    if status not in ("Pending", "Accepted", "Fulfilled", "Cancelled"):
        flash("Invalid request status.", "error")
        return redirect(url_for("admin"))
    with db() as con:
        con.execute("UPDATE blood_requests SET status=? WHERE id=?", (status, request_id))
    flash("Request status updated.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/donor/<int:donor_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_donor(donor_id):
    with db() as con:
        con.execute("DELETE FROM users WHERE id=(SELECT user_id FROM donors WHERE id=?)", (donor_id,))
    flash("Donor record removed.", "success")
    return redirect(url_for("admin"))

@app.route("/health")
def health():
    return {"status": "ok"}

init_db()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
