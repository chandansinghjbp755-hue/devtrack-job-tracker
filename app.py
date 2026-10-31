import csv
import io
import os
import secrets
import sqlite3
import warnings
from functools import wraps
from pathlib import Path
from datetime import date
from urllib.parse import urlsplit
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "devtrack.db"

app = Flask(__name__)
secret_key = os.environ.get("DEVTRACK_SECRET")
if not secret_key:
    secret_key = secrets.token_hex(32)
    warnings.warn(
        "DEVTRACK_SECRET is not set. A temporary key is being used; configure "
        "DEVTRACK_SECRET before deployment.",
        RuntimeWarning,
    )
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "DEVTRACK_COOKIE_SECURE", ""
).lower() == "true"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Applied',
                applied_on TEXT NOT NULL,
                interview_on TEXT DEFAULT '',
                job_type TEXT DEFAULT 'Full-time',
                notes TEXT DEFAULT '',
                job_url TEXT DEFAULT '',
                follow_up_on TEXT DEFAULT '',
                prep_coding INTEGER NOT NULL DEFAULT 0,
                prep_projects INTEGER NOT NULL DEFAULT 0,
                prep_behavioral INTEGER NOT NULL DEFAULT 0,
                prep_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        columns = {
            row[1] for row in db.execute("PRAGMA table_info(applications)")
        }
        migrations = {
            "job_url": "TEXT DEFAULT ''",
            "follow_up_on": "TEXT DEFAULT ''",
            "prep_coding": "INTEGER NOT NULL DEFAULT 0",
            "prep_projects": "INTEGER NOT NULL DEFAULT 0",
            "prep_behavioral": "INTEGER NOT NULL DEFAULT 0",
            "prep_notes": "TEXT DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in columns:
                db.execute(
                    f"ALTER TABLE applications ADD COLUMN {column} {definition}"
                )


def valid_date(value, optional=False):
    if not value:
        return optional
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def valid_http_url(value):
    if not value:
        return True
    try:
        parsed_url = urlsplit(value)
    except ValueError:
        return False
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


@app.context_processor
def inject_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        session_token = session.get("csrf_token", "")
        if not session_token or not secrets.compare_digest(
            submitted_token, session_token
        ):
            return "The form expired or was invalid. Please go back, refresh, and try again.", 400


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None

        if not name or not email or not password:
            error = "Please fill in every field."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            try:
                db = get_db()
                cursor = db.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password))
                )
                db.commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Your account is ready. Welcome to DevTrack!", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                error = "An account with this email already exists."

        if error:
            flash(error, "error")

    return render_template("auth.html", mode="register")


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="login")


@app.route("/logout", methods=("POST",))
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = session["user_id"]
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    allowed_statuses = {"Applied", "Interview", "Offer", "Rejected"}

    sql = "SELECT * FROM applications WHERE user_id = ?"
    params = [user_id]
    if q:
        sql += " AND (company LIKE ? OR role LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if status_filter in allowed_statuses:
        sql += " AND status = ?"
        params.append(status_filter)
    sql += " ORDER BY applied_on DESC, id DESC"
    applications = db.execute(sql, params).fetchall()

    counts = db.execute("""
        SELECT COUNT(*) AS total,
               SUM(status = 'Applied') AS applied,
               SUM(status = 'Interview') AS interview,
               SUM(status = 'Offer') AS offers,
               SUM(status = 'Rejected') AS rejected
        FROM applications WHERE user_id = ?
    """, (user_id,)).fetchone()

    stats = {key: (counts[key] or 0) for key in
             ("total", "applied", "interview", "offers", "rejected")}

    upcoming = db.execute("""
        SELECT company, role, interview_on FROM applications
        WHERE user_id = ? AND status = 'Interview'
          AND interview_on >= ? AND interview_on != ''
        ORDER BY interview_on ASC LIMIT 4
    """, (user_id, date.today().isoformat())).fetchall()
    followups = db.execute("""
        SELECT id, company, role, follow_up_on FROM applications
        WHERE user_id = ? AND follow_up_on != ''
        ORDER BY follow_up_on ASC LIMIT 5
    """, (user_id,)).fetchall()

    return render_template(
        "dashboard.html", applications=applications, stats=stats,
        upcoming=upcoming, search=q, status_filter=status_filter,
        followups=followups, today=date.today().isoformat()
    )


@app.route("/applications/add", methods=("POST",))
@login_required
def add_application():
    company = request.form.get("company", "").strip()
    role = request.form.get("role", "").strip()
    applied_on = request.form.get("applied_on", "").strip()
    interview_on = request.form.get("interview_on", "").strip()
    follow_up_on = request.form.get("follow_up_on", "").strip()
    job_url = request.form.get("job_url", "").strip()
    status = request.form.get("status", "Applied")
    valid_statuses = {"Applied", "Interview", "Offer", "Rejected"}

    if not company or not role or not applied_on:
        flash("Company, role and applied date are required.", "error")
    elif status not in valid_statuses:
        flash("Please choose a valid application status.", "error")
    elif not valid_http_url(job_url):
        flash("Job link must be a valid http or https URL.", "error")
    elif not all((
        valid_date(applied_on),
        valid_date(interview_on, optional=True),
        valid_date(follow_up_on, optional=True),
    )):
        flash("Please enter valid application, interview and follow-up dates.", "error")
    else:
        get_db().execute("""
            INSERT INTO applications
            (user_id, company, role, location, status, applied_on, interview_on, job_type, notes, job_url, follow_up_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], company, role,
            request.form.get("location", "").strip(), status, applied_on,
            interview_on,
            request.form.get("job_type", "Full-time"),
            request.form.get("notes", "").strip(), job_url, follow_up_on
        ))
        get_db().commit()
        flash("Application added to your pipeline.", "success")

    return redirect(url_for("dashboard"))


@app.route("/applications/<int:application_id>/edit", methods=("GET", "POST"))
@login_required
def edit_application(application_id):
    db = get_db()
    item = db.execute(
        "SELECT * FROM applications WHERE id = ? AND user_id = ?",
        (application_id, session["user_id"])
    ).fetchone()
    if item is None:
        return "Application not found.", 404

    if request.method == "POST":
        company = request.form.get("company", "").strip()
        role = request.form.get("role", "").strip()
        applied_on = request.form.get("applied_on", "").strip()
        interview_on = request.form.get("interview_on", "").strip()
        follow_up_on = request.form.get("follow_up_on", "").strip()
        job_url = request.form.get("job_url", "").strip()
        status = request.form.get("status", "")
        allowed_statuses = {"Applied", "Interview", "Offer", "Rejected"}
        if not company or not role:
            flash("Company and role are required.", "error")
        elif status not in allowed_statuses:
            flash("Please choose a valid application status.", "error")
        elif not all((
            valid_date(applied_on),
            valid_date(interview_on, optional=True),
            valid_date(follow_up_on, optional=True),
        )):
            flash("Please enter valid application, interview and follow-up dates.", "error")
        elif not valid_http_url(job_url):
            flash("Job link must be a valid http or https URL.", "error")
        else:
            db.execute("""
                UPDATE applications
                SET company = ?, role = ?, location = ?, status = ?, applied_on = ?,
                    interview_on = ?, job_type = ?, notes = ?, job_url = ?,
                    follow_up_on = ?, prep_coding = ?, prep_projects = ?,
                    prep_behavioral = ?, prep_notes = ?
                WHERE id = ? AND user_id = ?
            """, (
                company, role, request.form.get("location", "").strip(), status,
                applied_on, interview_on, request.form.get("job_type", "Full-time"),
                request.form.get("notes", "").strip(), job_url, follow_up_on,
                int(request.form.get("prep_coding") == "on"),
                int(request.form.get("prep_projects") == "on"),
                int(request.form.get("prep_behavioral") == "on"),
                request.form.get("prep_notes", "").strip(),
                application_id, session["user_id"]
            ))
            db.commit()
            flash("Application and interview preparation updated.", "success")
            return redirect(url_for("dashboard"))

        item = db.execute(
            "SELECT * FROM applications WHERE id = ? AND user_id = ?",
            (application_id, session["user_id"])
        ).fetchone()

    return render_template("edit_application.html", item=item)


@app.route("/applications/export.csv")
@login_required
def export_applications():
    rows = get_db().execute("""
        SELECT company, role, location, job_type, status, applied_on,
               interview_on, follow_up_on, job_url, notes, prep_coding,
               prep_projects, prep_behavioral, prep_notes
        FROM applications WHERE user_id = ?
        ORDER BY applied_on DESC, id DESC
    """, (session["user_id"],)).fetchall()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Company", "Role", "Location", "Job type", "Status", "Applied on",
        "Interview date", "Follow-up date", "Job link", "Application notes",
        "Coding practice complete", "Project review complete",
        "Behavioural practice complete", "Interview prep notes",
    ])
    for row in rows:
        values = list(row)
        values[10:13] = ["Yes" if value else "No" for value in values[10:13]]
        writer.writerow([
            "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value
            for value in values
        ])
    response = app.response_class(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=devtrack-applications.csv"}
    )
    return response


@app.route("/applications/<int:application_id>/status", methods=("POST",))
@login_required
def update_status(application_id):
    status = request.form.get("status", "")
    if status not in {"Applied", "Interview", "Offer", "Rejected"}:
        flash("Invalid status selected.", "error")
    else:
        get_db().execute(
            "UPDATE applications SET status = ? WHERE id = ? AND user_id = ?",
            (status, application_id, session["user_id"])
        )
        get_db().commit()
        flash("Application status updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/applications/<int:application_id>/delete", methods=("POST",))
@login_required
def delete_application(application_id):
    get_db().execute(
        "DELETE FROM applications WHERE id = ? AND user_id = ?",
        (application_id, session["user_id"])
    )
    get_db().commit()
    flash("Application removed.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=False)
