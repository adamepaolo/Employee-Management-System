import os
import sqlite3
import sys
import csv
import io
import uuid
from contextlib import contextmanager
import requests

from dateutil.relativedelta import relativedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, session, \
    Response, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any
from datetime import date, timedelta
from calendar import monthrange
from flask import make_response
from flask import send_file
from flask_wtf.csrf import CSRFProtect, validate_csrf

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.secret_key = "your_very_secure_secret_key_here_change_me"
csrf = CSRFProtect(app)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
VISA_DOCS_FOLDER = 'static/visa_docs'
PASSPORT_DOCS_FOLDER = 'static/passport_docs'
TICKET_DOCS_FOLDER = 'static/ticket_docs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['VISA_DOCS_FOLDER'] = VISA_DOCS_FOLDER
app.config['PASSPORT_DOCS_FOLDER'] = PASSPORT_DOCS_FOLDER
app.config['TICKET_DOCS_FOLDER'] = TICKET_DOCS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure the upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['VISA_DOCS_FOLDER'], exist_ok=True)
os.makedirs(app.config['PASSPORT_DOCS_FOLDER'], exist_ok=True)
os.makedirs(app.config['TICKET_DOCS_FOLDER'], exist_ok=True)


class Pagination:
    def __init__(self, page, per_page, total, items):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items

    @property
    def pages(self):
        if self.per_page == 0:
            return 0
        return max(0, (self.total - 1) // self.per_page) + 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def first(self):
        return (self.page - 1) * self.per_page + 1

    @property
    def last(self):
        if self.page * self.per_page > self.total:
            return self.total
        return self.page * self.per_page

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
                    (num > self.page - left_current - 1 and num < self.page + right_current) or \
                    num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)




@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect('employees.db')
        conn.row_factory = sqlite3.Row
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise  # Re-raise the exception
    finally:
        if conn:
            conn.close()


def init_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()



            # Check if Employees table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Employees'")
            employees_table_exists = cursor.fetchone() is not None

            if employees_table_exists:
                # Check if columns exist before adding them
                cursor.execute("PRAGMA table_info(Employees)")
                columns = [column[1] for column in cursor.fetchall()]

                # Add missing columns if they don't exist
                for column in ['CreatedBy', 'CreatedAt', 'UpdatedBy', 'UpdatedAt']:
                    if column not in columns:
                        cursor.execute(f"ALTER TABLE Employees ADD COLUMN {column} TEXT")
            else:

                # Create Users table with all columns
                cursor.execute("""
                                CREATE TABLE IF NOT EXISTS Users (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    username TEXT UNIQUE NOT NULL,
                                    password TEXT NOT NULL,
                                    email TEXT,
                                    full_name TEXT,
                                    is_admin BOOLEAN DEFAULT 0,
                                    is_developer BOOLEAN DEFAULT 0,
                                    is_approved BOOLEAN DEFAULT 0,
                                    last_activity TIMESTAMP,
                                    last_action TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            """)

                # Create new Employees table with current schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Employees (
                        EmployeeId TEXT PRIMARY KEY,
                        FirstName TEXT NOT NULL,
                        MiddleName TEXT,
                        LastName TEXT NOT NULL,
                        DisplayName TEXT NOT NULL,
                        FullNameArabic TEXT,
                        EmploymentType TEXT NOT NULL,
                        Nationality TEXT,
                        NationalityArabic TEXT,
                        PassportNumber TEXT NOT NULL,
                        Designation TEXT,
                        DesignationArabic TEXT,
                        Company TEXT,
                        CompanyArabic TEXT,
                        PhotoPath TEXT,
                        FieldOfAssignment TEXT,
                        FieldSite TEXT,
                        Rotation TEXT,
                        Birthday DATE,
                        Age INTEGER,
                        EmailAddress TEXT,
                        ContactNumber TEXT,
                        Rate REAL,
                        RateDescription TEXT,
                        ArrivalDate DATE,
                        StartedDate DATE,
                        Retired TEXT,
                        RetirementDate DATE,
                        Status TEXT,
                        DesertPassNumber TEXT,
                        DesertPassIssuedDate DATE,
                        DesertPassExpiryDate DATE,
                        BusinessVisaNumber TEXT,
                        BusinessVisaIssuedDate DATE,
                        BusinessVisaExpiryDate DATE,
                        ResidenceVisaNumber TEXT,
                        ResidenceVisaIssuedDate DATE,
                        ResidenceVisaExpiryDate DATE,
                        PassportIssuedDate DATE,
                        PassportExpiryDate DATE,
                        AccountName TEXT,
                        AccountNumber TEXT,
                        IBAN TEXT,
                        SwiftCode TEXT,
                        BankName TEXT,
                        BankAddress TEXT,
                        EmergencyContactName TEXT,
                        EmergencyContactRelationship TEXT,
                        EmergencyContactNumber TEXT,
                        EmergencyContactEmail TEXT,
                        BusinessVisaFilePath TEXT,
                        ResidenceVisaFilePath TEXT,
                        PassportFilePath TEXT,
                        CreatedBy TEXT,
                        CreatedAt TIMESTAMP,
                        UpdatedBy TEXT,
                        UpdatedAt TIMESTAMP
                    )
                """)

            # Create other tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS TrialLicenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    days_added INTEGER NOT NULL,
                    is_used BOOLEAN DEFAULT 0,
                    used_at TIMESTAMP,
                    used_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_to TEXT,
                    sent_at TIMESTAMP,
                    remote_ip TEXT,
                    remote_hostname TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AppSettings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_flight_ref TEXT,
                    pnr_ticket_number TEXT,
                    ticket_status TEXT,
                    flight_type TEXT,
                    passenger_id TEXT,
                    passenger_name TEXT,
                    designation TEXT,
                    company TEXT,
                    flight_route TEXT,
                    departure_country TEXT,
                    departure_airport TEXT,
                    departure_date DATE,
                    departure_time TEXT,
                    departure_airline TEXT,
                    has_transit BOOLEAN DEFAULT 0,
                    transit_country TEXT,
                    transit_airport TEXT,
                    transit_hours TEXT,
                    transit_airline TEXT,
                    arrival_country TEXT,
                    arrival_airport TEXT,
                    arrival_date DATE,
                    arrival_time TEXT,
                    arrival_airline TEXT,
                    ticket_document TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    updated_at TIMESTAMP,
                    updated_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES Users(id),
                    FOREIGN KEY (updated_by) REFERENCES Users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS UserActivity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES Users(id)
                )
            """)

            # Check if is_developer column exists (for older versions)
            cursor.execute("PRAGMA table_info(Users)")
            user_columns = [col[1] for col in cursor.fetchall()]
            if 'is_developer' not in user_columns:
                cursor.execute("ALTER TABLE Users ADD COLUMN is_developer BOOLEAN DEFAULT 0")

            # Insert initial trial settings if they don't exist
            cursor.execute("""
                INSERT OR IGNORE INTO AppSettings (setting_key, setting_value) 
                VALUES ('trial_start_date', ?), ('trial_days', '30')
            """, (datetime.now().strftime('%Y-%m-%d'),))

            # Check if admin user exists
            cursor.execute("SELECT * FROM Users WHERE is_admin = 1")
            admin_exists = cursor.fetchone()

            if not admin_exists:
                admin_password = generate_password_hash("admin123")
                cursor.execute(
                    "INSERT INTO Users (username, password, email, full_name, is_admin, is_developer, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("admin", admin_password, "info.mertini@gmail.com", "Admin User", True, False, True)
                )

            # Add developer user (only if it doesn't exist)
            cursor.execute("SELECT * FROM Users WHERE username = 'developer'")
            dev_exists = cursor.fetchone()
            if not dev_exists:
                cursor.execute(
                    "INSERT INTO Users (username, password, email, full_name, is_admin, is_developer, is_approved) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("developer", generate_password_hash("mertini25"), "info.merini@gmail.com", "Developer User", True,
                     True, True)
                )

            # Check if admin2 user exists
            cursor.execute("SELECT * FROM Users WHERE username = 'admin2'")
            admin2_exists = cursor.fetchone()



            conn.commit()
    except sqlite3.Error as e:
        error_message = f"Error initializing database: {e}"
        print(error_message)
        # Don't use flash here since we might be outside request context
        if 'user_id' in session:  # Only flash if we're in a request context
            flash(error_message, "danger")
        raise RuntimeError(error_message) from e


init_db()

def activate_trial(key, hostname="My Server"):
    response = requests.post(
        "http://127.0.0.1:5000/api/activate_trial",  # Added http:// and full endpoint path
        json={
            "license_key": key,
            "hostname": hostname
        }
    )
    return response.json()




def get_all_users():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users ORDER BY last_activity DESC")
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []


def log_user_activity(user_id, username, action):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO UserActivity (user_id, username, action, ip_address, user_agent)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, action, request.remote_addr, request.user_agent.string)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error logging activity: {e}")
        return False


def get_trial_status():
    """Get current trial status with error handling"""
    default_status = {
        'is_active': False,
        'start_date': None,
        'end_date': None,
        'days_remaining': 0,
        'total_days': 0
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_key = 'trial_start_date'")
            start_date = cursor.fetchone()[0]

            cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_key = 'trial_days'")
            trial_days = int(cursor.fetchone()[0])

            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = start_date + timedelta(days=trial_days)
            days_remaining = (end_date - date.today()).days

            return {
                'is_active': days_remaining > 0,
                'start_date': start_date,
                'end_date': end_date,
                'days_remaining': max(0, days_remaining),
                'total_days': trial_days
            }
    except Exception as e:
        print(f"Error getting trial status: {e}")
        return default_status


def generate_trial_extension(days):
    """Generate a trial extension code"""
    import secrets
    import hashlib

    # Generate a random license key
    key = f"TRL-{secrets.token_hex(8).upper()}"

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO TrialLicenses (license_key, days_added) VALUES (?, ?)",
                (key, days))
            conn.commit()
            return key
    except sqlite3.Error as e:
        print(f"Error generating trial extension: {e}")
        return None


def apply_trial_extension(key, username):
    """Apply a trial extension code"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if key exists and is unused
            cursor.execute(
                "SELECT days_added FROM TrialLicenses WHERE license_key = ? AND is_used = 0",
                (key,))
            result = cursor.fetchone()

            if not result:
                return False, "Invalid or already used license key"

            days = result[0]

            # Update trial days
            cursor.execute(
                "UPDATE AppSettings SET setting_value = CAST(setting_value AS INTEGER) + ? "
                "WHERE setting_key = 'trial_days'",
                (days,))

            # Mark key as used
            cursor.execute(
                "UPDATE TrialLicenses SET is_used = 1, used_at = CURRENT_TIMESTAMP, used_by = ? "
                "WHERE license_key = ?",
                (username, key))

            conn.commit()
            return True, f"System extended by {days} days successfully!"

    except sqlite3.Error as e:
        return False, f"Database error: {e}"

def update_user_activity(user_id, action):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Users SET last_activity = CURRENT_TIMESTAMP, last_action = ? WHERE id = ?",
                (action, user_id)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error updating user activity: {e}")
        return False


def get_user_by_username(username):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


def update_user_role(user_id, is_admin):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Users SET is_admin = ? WHERE id = ?",
                (is_admin, user_id)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False


def create_user(username, password, email, full_name):
    try:
        hashed_password = generate_password_hash(password)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Users (username, password, email, full_name) VALUES (?, ?, ?, ?)",
                (username, hashed_password, email, full_name)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False


def get_all_pending_users():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE is_approved = 0 ORDER BY created_at DESC")
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []


def approve_user(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET is_approved = 1 WHERE id = ?", (user_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False


def delete_user(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False


def migrate_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if is_developer column exists in Users table
            cursor.execute("PRAGMA table_info(Users)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'is_developer' not in columns:
                print("Adding is_developer column to Users table")
                cursor.execute("ALTER TABLE Users ADD COLUMN is_developer BOOLEAN DEFAULT 0")
                conn.commit()

            # Check for other migrations that might be needed
            # Add additional migration checks here as needed

    except sqlite3.Error as e:
        print(f"Migration error: {e}")
        raise

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))

        # Log the activity
        if request.path != url_for('logout'):
            action = f"Accessed {request.path}"
            log_user_activity(session['user_id'], session['username'], action)
            update_user_activity(session['user_id'], action)

        return f(*args, **kwargs)

    return decorated_function

trial_status = get_trial_status()


# Replace the check_trial_status() function with this version that uses AppSettings:
def check_trial_status():
    """Get current trial status with error handling"""
    default_status = {
        'is_active': False,
        'start_date': None,
        'end_date': None,
        'days_remaining': 0,
        'total_days': 0
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get trial start date
            cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_key = 'trial_start_date'")
            start_date_row = cursor.fetchone()
            if not start_date_row:
                return default_status

            start_date = datetime.strptime(start_date_row[0], '%Y-%m-%d').date()

            # Get trial days
            cursor.execute("SELECT setting_value FROM AppSettings WHERE setting_key = 'trial_days'")
            trial_days_row = cursor.fetchone()
            if not trial_days_row:
                return default_status

            trial_days = int(trial_days_row[0])
            end_date = start_date + timedelta(days=trial_days)
            days_remaining = (end_date - date.today()).days

            return {
                'is_active': days_remaining > 0,
                'start_date': start_date,
                'end_date': end_date,
                'days_remaining': max(0, days_remaining),
                'total_days': trial_days
            }
    except Exception as e:
        print(f"Error getting trial status: {e}")
        return default_status


# Remove the extend_trial() function since you're not using it (you have apply_trial_extension() instead)


def extend_trial(extension_code):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get current trial settings
            cursor.execute("SELECT end_date, extension_codes FROM TrialSettings ORDER BY id DESC LIMIT 1")
            trial = cursor.fetchone()

            if not trial:
                return False, "No trial settings found"

            # Check if code is valid
            valid_codes = trial['extension_codes'].split(',') if trial['extension_codes'] else []
            if extension_code not in valid_codes:
                return False, "Invalid extension code"

            # Extend trial by 30 days
            current_end = datetime.strptime(trial['end_date'], '%Y-%m-%d %H:%M:%S')
            new_end = current_end + timedelta(days=30)

            # Remove used code
            valid_codes.remove(extension_code)

            cursor.execute("""
                UPDATE TrialSettings 
                SET end_date = ?, extension_codes = ?, is_active = 1
                WHERE id = ?
            """, (new_end.strftime('%Y-%m-%d %H:%M:%S'), ','.join(valid_codes), trial['id']))
            conn.commit()

            return True, "System extended successfully"
    except sqlite3.Error as e:
        return False, f"Database error: {e}"


def trial_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_trial_status():
            flash("Your trial period has expired. Please contact support.", "danger")
            return redirect(url_for('trial_expired'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash("You don't have permission to access this page.", "danger")
            return redirect(url_for('main_menu'))

        # Update user activity
        action = f"Accessed admin page: {request.path}"
        update_user_activity(session['user_id'], action)

        return f(*args, **kwargs)

    return decorated_function

def developer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_developer'):
            flash("Developer access required", "danger")
            return redirect(url_for('main_menu'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/extend-trial', methods=['POST'])
def apply_trial_extension_route():
    if request.method == 'POST':
        license_key = request.form.get('license_key')
        success, message = apply_trial_extension(license_key, session.get('username'))
        flash(message, 'success' if success else 'danger')

        return redirect(url_for('main_menu'))



@app.route('/trial/expired')
def trial_expired():
    return render_template('trial_expired.html')


@app.route('/trial/extend', methods=['GET', 'POST'])
def extend_trial_route():
    if request.method == 'POST':
        extension_code = request.form.get('extension_code', '').strip()
        success, message = extend_trial(extension_code)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('main_menu'))

    return render_template('extend_trial.html')


# Add this to your routes
@app.route('/admin/generate_trial_key', methods=['POST'])
@login_required
@developer_required
def generate_trial_key():
    if not session.get('is_developer'):
        return jsonify({'success': False, 'message': 'Developer access required'}), 403

    days = int(request.json.get('days', 30))
    email = request.json.get('email', '')

    key = generate_trial_extension(days)

    if not key:
        return jsonify({'success': False, 'message': 'Failed to generate key'}), 500

    # In a real app, you would log this generation with the email
    return jsonify({
        'success': True,
        'key': key,
        'days': days
    })


@app.route('/admin/send_trial_key', methods=['POST'])
@developer_required
def send_trial_key():
    if not session.get('is_developer'):
        return jsonify({'success': False, 'message': 'Developer access required'}), 403

    email = request.json.get('email', '')
    key = request.json.get('key', '')

    if not email or not key:
        return jsonify({'success': False, 'message': 'Email and key required'}), 400

    # In a real app, you would implement email sending here
    # For now, we'll just log it
    print(f"System key {key} would be sent to {email}")

    return jsonify({
        'success': True,
        'message': f'Key {key} sent to {email}'
    })

@app.route('/admin/generate_extension_codes', methods=['POST'])
@developer_required
def generate_extension_codes():
    try:
        num_codes = int(request.form.get('num_codes', 5))
        days_per_code = int(request.form.get('days_per_code', 30))

        codes = [str(uuid.uuid4()).replace('-', '')[:12] for _ in range(num_codes)]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE TrialSettings 
                SET extension_codes = ?
                WHERE id = (SELECT MAX(id) FROM TrialSettings)
            """, (','.join(codes),))
            conn.commit()

        # Create a downloadable CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Extension Code', 'Days Added'])
        for code in codes:
            writer.writerow([code, days_per_code])
        output.seek(0)

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=trial_extension_codes.csv"}
        )

    except Exception as e:
        flash(f"Error generating codes: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))


@app.route('/')
@login_required
@trial_required
def main_menu():
    return render_template('main_menu.html', trial_status=get_trial_status())

# Add @trial_required to other important routes
@app.route('/admin/trial', methods=['GET', 'POST'])
@developer_required
def manage_trial():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'generate':
            days = int(request.form.get('days', 30))
            key = generate_trial_extension(days)

            if key:
                flash(f"System extension code generated: {key} - Adds {days} days", "success")
            else:
                flash("Failed to generate trial extension code", "danger")

        elif action == 'reset':
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE AppSettings SET setting_value = ? WHERE setting_key = 'trial_start_date'",
                        (datetime.now().strftime('%Y-%m-%d'),))
                    cursor.execute(
                        "UPDATE AppSettings SET setting_value = '30' WHERE setting_key = 'trial_days'")
                    conn.commit()

                flash("System period reset to 30 days from today", "success")
            except sqlite3.Error as e:
                flash(f"Error resetting trial: {e}", "danger")

        return redirect(url_for('manage_trial'))

    # Get all generated license keys
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM TrialLicenses ORDER BY created_at DESC")
            licenses = [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        licenses = []


    return render_template('admin/trial_management.html',
                           trial_status=trial_status,
                           licenses=licenses)


@app.route('/api/activate_trial', methods=['POST'])
def api_activate_trial():
    """API endpoint for remote trial activation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        license_key = data.get('license_key', '').strip()
        hostname = data.get('hostname', 'Unknown').strip()

        if not license_key:
            return jsonify({'success': False, 'message': 'License key required'}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if key exists and is unused
            cursor.execute(
                """SELECT id, days_added FROM TrialLicenses 
                WHERE license_key = ? AND is_used = 0""",
                (license_key,))
            result = cursor.fetchone()

            if not result:
                # Check if key exists but is used
                cursor.execute(
                    "SELECT id FROM TrialLicenses WHERE license_key = ?",
                    (license_key,))
                if cursor.fetchone():
                    return jsonify({
                        'success': False,
                        'message': 'License key already used'
                    }), 400
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid license key'
                    }), 400

            days = result['days_added']
            license_id = result['id']

            # Mark key as used
            cursor.execute(
                """UPDATE TrialLicenses SET 
                    is_used = 1, 
                    used_at = CURRENT_TIMESTAMP, 
                    used_by = 'remote_activation',
                    remote_ip = ?,
                    remote_hostname = ?
                WHERE id = ?""",
                (request.remote_addr, hostname, license_id))

            conn.commit()

            return jsonify({
                'success': True,
                'message': f'Trial extended by {days} days',
                'days_added': days
            })

    except sqlite3.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Unexpected error: {e}'}), 500

# Auth Routes
@app.route('/register', methods=['GET', 'POST'])

def register():
    if request.method == 'POST':
        # Validate CSRF token
        try:
            validate_csrf(request.form.get('csrf_token'))
        except:
            flash("Invalid CSRF token. Please try again.", "danger")
            return redirect(url_for('register'))

        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        full_name = request.form['full_name']

        if not username or not password or not email:
            flash("Username, password, and email are required.", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))

        existing_user = get_user_by_username(username)
        if existing_user:
            flash("Username already exists. Please choose another.", "danger")
            return redirect(url_for('register'))

        if create_user(username, password, email, full_name):
            flash("Registration successful! Please wait for admin approval.", "success")
            return redirect(url_for('login'))
        else:
            flash("Registration failed. Please try again.", "danger")

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Validate CSRF token first
        try:
            validate_csrf(request.form.get('csrf_token'))
        except:
            flash("Invalid CSRF token. Please try again.", "danger")
            return redirect(url_for('login'))

        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if not user:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))

        if not check_password_hash(user['password'], password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))

        if not user['is_approved']:
            flash("Your account is pending approval by an administrator.", "warning")
            return redirect(url_for('login'))

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        session['full_name'] = user['full_name']
        session['is_developer'] = user['is_developer']

        update_user_activity(user['id'], "Logged in")
        flash("Login successful!", "success")
        return redirect(url_for('main_menu'))

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    # Validate CSRF token
    try:
        validate_csrf(request.form.get('csrf_token'))
    except:
        flash("Invalid CSRF token", "danger")
        return redirect(url_for('main_menu'))

    # Log the logout activity
    update_user_activity(session['user_id'], "Logged out")

    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))


# Admin Routes
@app.route('/admin/pending_users')
@admin_required
def pending_users():
    users = get_all_pending_users()
    return render_template('pending_users.html', users=users)


@app.route('/admin/users')
@admin_required
def admin_users():
    users = get_all_users()
    return render_template('admin_users.html', users=users)


@app.route('/admin/activity')
@admin_required
def view_activity():
    try:
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'timestamp')  # Default sort by timestamp
        user_filter = request.args.get('user', None)
        per_page = 25  # Set the limit to 1000 per page

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Base query
            query = """
                SELECT ua.*, u.full_name 
                FROM UserActivity ua
                LEFT JOIN Users u ON ua.user_id = u.id
            """
            count_query = "SELECT COUNT(*) FROM UserActivity ua LEFT JOIN Users u ON ua.user_id = u.id"

            params = []
            where_clauses = []

            if user_filter:
                where_clauses.append("u.username = ?")
                params.append(user_filter)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                count_query += " WHERE " + " AND ".join(where_clauses)

            # Sorting
            query += " ORDER BY "
            if sort_by == 'user':
                query += "u.username, ua.timestamp DESC"
            else:  # Default sort by timestamp
                query += "ua.timestamp DESC"

            # Get total count
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Add pagination
            query += " LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])

            cursor.execute(query, params)
            activities = cursor.fetchall()

            # Convert to pagination object
            activities = Pagination(page=page, per_page=per_page, total=total,
                                    items=[dict(row) for row in activities])

            # Get distinct users for filter dropdown
            cursor.execute("SELECT DISTINCT username FROM UserActivity ORDER BY username")
            users = [row['username'] for row in cursor.fetchall()]

            return render_template('user_activity.html',
                                   activities=activities,
                                   users=users,
                                   current_sort=sort_by,
                                   current_user=user_filter)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('admin_users'))


@app.route('/admin/activity/export_csv')
@admin_required
def export_activity_csv():
    try:
        sort_by = request.args.get('sort', 'timestamp')
        user_filter = request.args.get('user', None)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT ua.timestamp, u.username, u.full_name, ua.action, ua.ip_address, ua.user_agent
                FROM UserActivity ua
                LEFT JOIN Users u ON ua.user_id = u.id
            """

            params = []

            if user_filter:
                query += " WHERE u.username = ?"
                params.append(user_filter)

            query += " ORDER BY "

            if sort_by == 'user':
                query += "u.username, ua.timestamp DESC"
            else:
                query += "ua.timestamp DESC"

            cursor.execute(query, params)
            activities = cursor.fetchall()

            # Create CSV output
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['Timestamp', 'Username', 'Full Name', 'Action', 'IP Address', 'User Agent'])

            # Write data
            for row in activities:
                writer.writerow([
                    row['timestamp'],
                    row['username'],
                    row['full_name'] or '',
                    row['action'],
                    row['ip_address'],
                    row['user_agent']
                ])

            output.seek(0)

            return Response(
                output,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=user_activity.csv"}
            )

    except Exception as e:
        flash(f"Error generating CSV: {e}", "danger")
        return redirect(url_for('view_activity'))


@app.route('/admin/approve_user/<int:user_id>')
@admin_required
def admin_approve_user(user_id):
    if approve_user(user_id):
        update_user_activity(session['user_id'], f"Approved user ID {user_id}")
        flash("User approved successfully.", "success")
    else:
        flash("Failed to approve user.", "danger")
    return redirect(url_for('pending_users'))


@app.route('/admin/update_role/<int:user_id>', methods=['POST'])
@admin_required
def update_user_role_route(user_id):
    if request.method == 'POST':
        try:
            validate_csrf(request.form.get('csrf_token'))
        except:
            return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 400

        is_admin = request.form.get('is_admin') == 'true'

        # Prevent modifying the current admin's own role
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'You cannot change your own admin status'}), 400

        if update_user_role(user_id, is_admin):
            action = f"Changed role for user ID {user_id} to {'admin' if is_admin else 'user'}"
            update_user_activity(session['user_id'], action)
            return jsonify({'success': True, 'message': 'User role updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update user role'}), 500

    return jsonify({'success': False, 'message': 'Invalid request method'}), 405


@app.route('/api/check_license_key/<key>')
@developer_required
def check_license_key(key):
    """Debug endpoint to check a license key status"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM TrialLicenses WHERE license_key = ?",
                (key,))
            result = cursor.fetchone()

            if not result:
                return jsonify({'exists': False, 'is_used': False})

            return jsonify({
                'exists': True,
                'is_used': bool(result['is_used']),
                'days_added': result['days_added'],
                'created_at': result['created_at'],
                'used_at': result['used_at'],
                'used_by': result['used_by']
            })
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def admin_delete_user(user_id):
    if delete_user(user_id):
        update_user_activity(session['user_id'], f"Deleted user ID {user_id}")
        flash("User deleted successfully.", "success")
    else:
        flash("Failed to delete user.", "danger")
    return redirect(url_for('pending_users'))


# Employee Management
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _generate_display_name(first_name: str, middle_name: Optional[str], last_name: str) -> str:
    return f"{first_name} ({middle_name}) {last_name}" if middle_name else f"{first_name} {last_name}"


def employee_id_exists(employee_id: str) -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM Employees WHERE EmployeeId = ?", (employee_id,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        error_message = f"Error checking employee ID: {e}"
        print(error_message)
        flash(error_message, "danger")
        abort(500)


def get_employee_by_id(employee_id: str) -> Optional[Dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM Employees WHERE EmployeeId = ?', (employee_id,))
            employee = cursor.fetchone()
            return dict(employee) if employee else None
    except sqlite3.Error as e:
        error_message = f"Error retrieving employee: {e}"
        print(error_message)
        flash(error_message, 'danger')
        abort(500)


def get_all_employees() -> list:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM Employees')
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        error_message = f"Error retrieving employees: {e}"
        print(error_message)
        flash(error_message, 'danger')
        abort(500)


def calculate_age(birthday: datetime.date) -> int:
    today = datetime.now().date()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


def _process_employee_form(form: dict, files: dict, employee_id: str, is_update: bool = False) -> Dict[str, Any]:
    first_name = form['first_name']
    middle_name = form['middle_name']
    last_name = form['last_name']
    display_name = _generate_display_name(first_name, middle_name, last_name)

    photo_path = None
    if 'photo' in files and files['photo']:
        photo = files['photo']
        if allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = f"uploads/{filename}"
            absolute_path = os.path.join(app.static_folder, photo_path)
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            photo.save(absolute_path)
        else:
            raise ValueError("Invalid file type. Allowed: png, jpg, jpeg, gif")

    required_fields = {
        'first_name': first_name,
        'last_name': last_name,
        'employee_id': employee_id,
        'employment_type': form['employment_type'],
        'passport_number': form['passport_number'],
        'contact_number': form['contact_number']
    }

    for field, value in required_fields.items():
        if not value:
            raise ValueError(f"Missing required field: {field.replace('_', ' ').title()}")

    try:
        birthday = datetime.strptime(form['birthday'], '%Y-%m-%d').date()
        age = calculate_age(birthday)
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    retired = form['retired']
    retirement_date = None
    if retired.lower() == 'yes':
        retirement_date = datetime.now().date().isoformat()

    # Process document uploads
    business_visa_path = None
    residence_visa_path = None
    passport_path = None

    # Business Visa File
    if 'business_visa_file' in files and files['business_visa_file']:
        file = files['business_visa_file']
        if file.filename:
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type for business visa document. Allowed: pdf, png, jpg, jpeg")
            filename = secure_filename(f"{employee_id}_business_visa_{file.filename}")
            file_path = os.path.join(app.config['VISA_DOCS_FOLDER'], filename)
            file.save(file_path)
            business_visa_path = f"visa_docs/{filename}"

    # Residence Visa File
    if 'residence_visa_file' in files and files['residence_visa_file']:
        file = files['residence_visa_file']
        if file.filename:
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type for residence visa document. Allowed: pdf, png, jpg, jpeg")
            filename = secure_filename(f"{employee_id}_residence_visa_{file.filename}")
            file_path = os.path.join(app.config['VISA_DOCS_FOLDER'], filename)
            file.save(file_path)
            residence_visa_path = f"visa_docs/{filename}"

    # Passport File
    if 'passport_file' in files and files['passport_file']:
        file = files['passport_file']
        if file.filename:
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type for passport document. Allowed: pdf, png, jpg, jpeg")
            filename = secure_filename(f"{employee_id}_passport_{file.filename}")
            file_path = os.path.join(app.config['PASSPORT_DOCS_FOLDER'], filename)
            file.save(file_path)
            passport_path = f"passport_docs/{filename}"

    return {
        'EmployeeId': employee_id,
        'FirstName': first_name,
        'MiddleName': middle_name,
        'LastName': last_name,
        'DisplayName': display_name,
        'FullNameArabic': form.get('full_name_arabic'),
        'EmploymentType': form['employment_type'],
        'Nationality': form['nationality'],
        'NationalityArabic': form.get('nationality_arabic'),
        'PassportNumber': form['passport_number'],
        'Designation': form['designation'],
        'DesignationArabic': form.get('designation_arabic'),
        'Company': form['company'],
        'CompanyArabic': form.get('company_arabic'),
        'PhotoPath': photo_path,
        'FieldOfAssignment': form['field_of_assignment'],
        'FieldSite': form['field_site'],
        'Rotation': form['rotation'],
        'Birthday': birthday,
        'Age': age,
        'EmailAddress': form.get('email_address'),
        'ContactNumber': form['contact_number'],
        'Rate': float(form['rate']),
        'RateDescription': form['rate_description'],
        'ArrivalDate': form['arrival_date'],
        'StartedDate': form['started_date'],
        'Retired': retired,
        'RetirementDate': retirement_date,
        'Status': form['status'],
        'DesertPassNumber': form.get('desert_pass_number'),
        'DesertPassIssuedDate': form.get('desert_pass_issued_date'),
        'DesertPassExpiryDate': form.get('desert_pass_expiry_date'),
        'BusinessVisaNumber': form.get('business_visa_number'),
        'BusinessVisaIssuedDate': form.get('business_visa_issued_date'),
        'BusinessVisaExpiryDate': form.get('business_visa_expiry_date'),
        'ResidenceVisaNumber': form.get('residence_visa_number'),
        'ResidenceVisaIssuedDate': form.get('residence_visa_issued_date'),
        'ResidenceVisaExpiryDate': form.get('residence_visa_expiry_date'),
        'PassportIssuedDate': form.get('passport_issued_date'),
        'PassportExpiryDate': form.get('passport_expiry_date'),
        'AccountName': form.get('account_name'),
        'AccountNumber': form.get('account_number'),
        'IBAN': form.get('iban'),
        'SwiftCode': form.get('swift_code'),
        'BankName': form.get('bank_name'),
        'BankAddress': form.get('bank_address'),
        'EmergencyContactName': form.get('emergency_contact_name'),
        'EmergencyContactRelationship': form.get('emergency_contact_relationship'),
        'EmergencyContactNumber': form.get('emergency_contact_number'),
        'EmergencyContactEmail': form.get('emergency_contact_email'),
        'BusinessVisaFilePath': business_visa_path,
        'ResidenceVisaFilePath': residence_visa_path,
        'PassportFilePath': passport_path
    }





@app.route('/register_employee', methods=['GET', 'POST'])
@login_required
def register_employee():
    if request.method == 'POST':
        try:
            employee_data = _process_employee_form(request.form, request.files, request.form['employee_id'])

            # Add system information fields with proper values
            employee_data.update({
                'CreatedBy': session['username'],
                'CreatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'UpdatedBy': session['username'],
                'UpdatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Employees (
                        EmployeeId, FirstName, MiddleName, LastName, DisplayName, 
                        FullNameArabic, EmploymentType, Nationality, NationalityArabic, 
                        PassportNumber, Designation, DesignationArabic, Company, 
                        CompanyArabic, PhotoPath, FieldOfAssignment, FieldSite, 
                        Rotation, Birthday, Age, EmailAddress, ContactNumber, 
                        Rate, RateDescription, ArrivalDate, StartedDate, 
                        Retired, RetirementDate, Status, DesertPassNumber, DesertPassIssuedDate,
                        DesertPassExpiryDate, BusinessVisaNumber, BusinessVisaIssuedDate,
                        BusinessVisaExpiryDate, ResidenceVisaNumber, ResidenceVisaIssuedDate,
                        ResidenceVisaExpiryDate, PassportIssuedDate, PassportExpiryDate,
                        AccountName, AccountNumber, IBAN, SwiftCode, BankName,
                        BankAddress, EmergencyContactName, EmergencyContactRelationship,
                        EmergencyContactNumber, EmergencyContactEmail,
                        BusinessVisaFilePath, ResidenceVisaFilePath, PassportFilePath,
                        CreatedBy, CreatedAt, UpdatedBy, UpdatedAt
                    ) VALUES (
                        :EmployeeId, :FirstName, :MiddleName, :LastName, :DisplayName, 
                        :FullNameArabic, :EmploymentType, :Nationality, :NationalityArabic, 
                        :PassportNumber, :Designation, :DesignationArabic, :Company, 
                        :CompanyArabic, :PhotoPath, :FieldOfAssignment, :FieldSite, 
                        :Rotation, :Birthday, :Age, :EmailAddress, :ContactNumber, 
                        :Rate, :RateDescription, :ArrivalDate, :StartedDate, 
                        :Retired, :RetirementDate, :Status, :DesertPassNumber, :DesertPassIssuedDate,
                        :DesertPassExpiryDate, :BusinessVisaNumber, :BusinessVisaIssuedDate,
                        :BusinessVisaExpiryDate, :ResidenceVisaNumber, :ResidenceVisaIssuedDate,
                        :ResidenceVisaExpiryDate, :PassportIssuedDate, :PassportExpiryDate,
                        :AccountName, :AccountNumber, :IBAN, :SwiftCode, :BankName,
                        :BankAddress, :EmergencyContactName, :EmergencyContactRelationship,
                        :EmergencyContactNumber, :EmergencyContactEmail,
                        :BusinessVisaFilePath, :ResidenceVisaFilePath, :PassportFilePath,
                        :CreatedBy, :CreatedAt, :UpdatedBy, :UpdatedAt
                    )
                """, employee_data)
                conn.commit()
                update_user_activity(session['user_id'], f"Registered new employee: {employee_data['EmployeeId']}")
                flash('Employee registered successfully!', 'success')
                return redirect(url_for('view_profile', employee_id=employee_data['EmployeeId']))

        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")

    return render_template('register_employee.html')


@app.route('/employee_details', methods=['GET', 'POST'])
@login_required
def employee_details():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        employee = get_employee_by_id(employee_id)
        if employee:
            update_user_activity(session['user_id'], f"Viewed details for employee: {employee_id}")
            return render_template('employee_details.html', employee=employee)
        flash("Employee not found.", "danger")
    return redirect(url_for('employee_list'))


@app.route('/update_employee/<employee_id>', methods=['GET', 'POST'])
@login_required
def update_employee(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash("Employee not found.", 'danger')
        return redirect(url_for('employee_list'))

    if request.method == 'POST':
        try:
            employee_data = _process_employee_form(request.form, request.files, employee_id, is_update=True)

            # Only update UpdatedBy and UpdatedAt fields, leave CreatedBy/CreatedAt unchanged
            employee_data.update({
                'UpdatedBy': session['username'],
                'UpdatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            if not employee_data['PhotoPath']:
                employee_data['PhotoPath'] = employee['PhotoPath']

            # Handle document deletions (existing code remains the same)
            # ...

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Employees SET 
                        FirstName = :FirstName, 
                        MiddleName = :MiddleName, 
                        LastName = :LastName,
                        DisplayName = :DisplayName, 
                        FullNameArabic = :FullNameArabic,
                        EmploymentType = :EmploymentType, 
                        Nationality = :Nationality,
                        NationalityArabic = :NationalityArabic, 
                        PassportNumber = :PassportNumber,
                        Designation = :Designation, 
                        DesignationArabic = :DesignationArabic,
                        Company = :Company, 
                        CompanyArabic = :CompanyArabic, 
                        PhotoPath = :PhotoPath,
                        FieldOfAssignment = :FieldOfAssignment, 
                        FieldSite = :FieldSite,
                        Rotation = :Rotation, 
                        Birthday = :Birthday, 
                        Age = :Age,
                        EmailAddress = :EmailAddress, 
                        ContactNumber = :ContactNumber,
                        Rate = :Rate, 
                        RateDescription = :RateDescription,
                        ArrivalDate = :ArrivalDate, 
                        StartedDate = :StartedDate,
                        Retired = :Retired, 
                        RetirementDate = :RetirementDate, 
                        Status = :Status,
                        DesertPassNumber = :DesertPassNumber,
                        DesertPassIssuedDate = :DesertPassIssuedDate,
                        DesertPassExpiryDate = :DesertPassExpiryDate,
                        BusinessVisaNumber = :BusinessVisaNumber,
                        BusinessVisaIssuedDate = :BusinessVisaIssuedDate,
                        BusinessVisaExpiryDate = :BusinessVisaExpiryDate,
                        ResidenceVisaNumber = :ResidenceVisaNumber,
                        ResidenceVisaIssuedDate = :ResidenceVisaIssuedDate,
                        ResidenceVisaExpiryDate = :ResidenceVisaExpiryDate,
                        PassportIssuedDate = :PassportIssuedDate,
                        PassportExpiryDate = :PassportExpiryDate,
                        AccountName = :AccountName, 
                        AccountNumber = :AccountNumber,
                        IBAN = :IBAN, 
                        SwiftCode = :SwiftCode, 
                        BankName = :BankName,
                        BankAddress = :BankAddress, 
                        EmergencyContactName = :EmergencyContactName,
                        EmergencyContactRelationship = :EmergencyContactRelationship,
                        EmergencyContactNumber = :EmergencyContactNumber,
                        EmergencyContactEmail = :EmergencyContactEmail,
                        BusinessVisaFilePath = CASE WHEN :BusinessVisaFilePath IS NOT NULL THEN :BusinessVisaFilePath ELSE BusinessVisaFilePath END,
                        ResidenceVisaFilePath = CASE WHEN :ResidenceVisaFilePath IS NOT NULL THEN :ResidenceVisaFilePath ELSE ResidenceVisaFilePath END,
                        PassportFilePath = CASE WHEN :PassportFilePath IS NOT NULL THEN :PassportFilePath ELSE PassportFilePath END,
                        UpdatedBy = :UpdatedBy,
                        UpdatedAt = :UpdatedAt
                    WHERE EmployeeId = :EmployeeId
                """, employee_data)
                conn.commit()
                update_user_activity(session['user_id'], f"Updated employee: {employee_id}")
                flash("Employee updated successfully!", "success")
                return redirect(url_for('view_profile', employee_id=employee_id))

        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")

    return render_template('update_employee.html', employee=employee)


@app.route('/list')
@login_required
def employee_list():
    employees = get_all_employees()
    # Extract unique companies from employees
    companies = list({emp['Company'] for emp in employees if emp.get('Company')})
    update_user_activity(session['user_id'], "Viewed employee list")
    return render_template('employee_list.html', employees=employees, companies=companies)


@app.route('/delete_employee/<employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT PhotoPath, BusinessVisaFilePath, ResidenceVisaFilePath, PassportFilePath FROM Employees WHERE EmployeeId = ?',
                (employee_id,))
            files = cursor.fetchone()

            cursor.execute('DELETE FROM Employees WHERE EmployeeId = ?', (employee_id,))
            conn.commit()

            # Delete associated files
            for file_field in ['PhotoPath', 'BusinessVisaFilePath', 'ResidenceVisaFilePath', 'PassportFilePath']:
                if files[file_field]:
                    full_path = os.path.join(app.static_folder, files[file_field])
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                        except OSError as e:
                            print(f"Error deleting {file_field}: {e}")

            update_user_activity(session['user_id'], f"Deleted employee: {employee_id}")
            return jsonify({'success': True, 'message': 'Employee deleted successfully'})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'message': f'Error deleting employee: {e}'}), 500


@app.route('/profile/<employee_id>')
@login_required
def view_profile(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('employee_list'))

    # Check if files exist
    for file_field in ['PhotoPath', 'BusinessVisaFilePath', 'ResidenceVisaFilePath', 'PassportFilePath']:
        if employee[file_field]:
            full_path = os.path.join(app.static_folder, employee[file_field])
            if not os.path.exists(full_path):
                employee[file_field] = None

    update_user_activity(session['user_id'], f"Viewed profile for employee: {employee_id}")
    return render_template('employee_profile.html', employee=employee)

# Flight Management Routes
@app.route('/flights')
@login_required
def view_flights():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) FROM Flights")
            total = cursor.fetchone()[0]

            # Get paginated flights
            cursor.execute("""
                SELECT f.*, u.username as created_by_name 
                FROM Flights f
                LEFT JOIN Users u ON f.created_by = u.id
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, (page - 1) * per_page))

            flights = [dict(row) for row in cursor.fetchall()]

            pagination = Pagination(
                page=page,
                per_page=per_page,
                total=total,
                items=flights
            )

            return render_template('flights/view_flights.html', flights=pagination)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('main_menu'))

@app.context_processor
def inject_trial_status():
    return {
        'trial_status': get_trial_status()
    }

@app.route('/flights/calendar')
@app.route('/flights/calendar/<int:year>/<int:month>')
@app.route('/flights/calendar/<int:year>/<int:month>/<int:day>')
@login_required
def flight_calendar(year=None, month=None, day=None):
    """View flight calendar in month, week or day view"""

    def process_flight_events(flight, events, start_date, end_date):
        """Helper function to process flight events into calendar structure"""
        # Process departures
        if flight['departure_date']:
            try:
                dep_date = datetime.strptime(str(flight['departure_date']), '%Y-%m-%d').date()
                if start_date <= dep_date <= end_date:
                    if dep_date not in events:
                        events[dep_date] = []
                    events[dep_date].append({
                        'type': 'departure',
                        'time': flight['departure_time'],
                        'country': flight['departure_country'],
                        'airport': flight['departure_airport'],
                        'passenger': flight['passenger_name'],
                        'passenger_id': flight['passenger_id'],
                        'ref': flight['company_flight_ref'],
                        'flight_id': flight['id'],
                        'css_class': 'event-departure'
                    })
            except ValueError:
                pass

        # Process arrivals
        if flight['arrival_date']:
            try:
                arr_date = datetime.strptime(str(flight['arrival_date']), '%Y-%m-%d').date()
                if start_date <= arr_date <= end_date:
                    if arr_date not in events:
                        events[arr_date] = []
                    events[arr_date].append({
                        'type': 'arrival',
                        'time': flight['arrival_time'],
                        'country': flight['arrival_country'],
                        'airport': flight['arrival_airport'],
                        'passenger': flight['passenger_name'],
                        'passenger_id': flight['passenger_id'],
                        'ref': flight['company_flight_ref'],
                        'flight_id': flight['id'],
                        'css_class': 'event-arrival'
                    })
            except ValueError:
                pass

    try:
        # Get and validate view type
        view = request.args.get('view', 'month').lower()
        if view not in {'month', 'week', 'day'}:
            view = 'month'

        # Set default to current date if not provided
        today = datetime.now().date()
        if None in (year, month):
            year, month = today.year, today.month
        if day is None:
            day = today.day

        # Ensure valid date parameters
        year, month, day = int(year), int(month), int(day)
        current_date = date(year, month, day)

        # Calculate navigation dates
        if view == 'month':
            prev_date = current_date - relativedelta(months=1)
            next_date = current_date + relativedelta(months=1)
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
        elif view == 'week':
            prev_date = current_date - timedelta(weeks=1)
            next_date = current_date + timedelta(weeks=1)
            start_of_week = current_date - timedelta(days=current_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
        else:  # day view
            prev_date = current_date - timedelta(days=1)
            next_date = current_date + timedelta(days=1)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            if view == 'month':
                # Month view query
                cursor.execute("""
                    SELECT id, company_flight_ref, passenger_name, passenger_id,
                           departure_date, departure_time, departure_country, departure_airport,
                           arrival_date, arrival_time, arrival_country, arrival_airport
                    FROM Flights
                    WHERE (departure_date BETWEEN ? AND ?) OR (arrival_date BETWEEN ? AND ?)
                    ORDER BY COALESCE(departure_date, arrival_date), 
                             COALESCE(departure_time, arrival_time)
                """, [first_day, last_day] * 2)

                # Process into calendar events
                events = {}
                for row in cursor.fetchall():
                    flight = dict(row)
                    process_flight_events(flight, events, first_day, last_day)

                # Build month grid
                cal = []
                week = []
                current_day = first_day

                # Pad beginning of month
                for _ in range(first_day.weekday()):
                    week.append(None)

                while current_day <= last_day:
                    if len(week) == 7:
                        cal.append(week)
                        week = []

                    week.append({
                        'date': current_day,
                        'day': current_day.day,
                        'events': events.get(current_day, []),
                        'is_today': current_day == today,
                        'is_weekend': current_day.weekday() >= 5
                    })
                    current_day += timedelta(days=1)

                # Pad end of month
                if week:
                    week.extend([None] * (7 - len(week)))
                    cal.append(week)

                template_data = {
                    'weeks': cal,
                    'week_data': None,
                    'day_data': None
                }

            elif view == 'week':
                # Week view query
                cursor.execute("""
                    SELECT id, company_flight_ref, passenger_name, passenger_id,
                           departure_date, departure_time, departure_country, departure_airport,
                           arrival_date, arrival_time, arrival_country, arrival_airport
                    FROM Flights
                    WHERE (departure_date BETWEEN ? AND ?) OR (arrival_date BETWEEN ? AND ?)
                    ORDER BY COALESCE(departure_date, arrival_date), 
                             COALESCE(departure_time, arrival_time)
                """, [start_of_week, end_of_week] * 2)

                # Process week events
                events = {}
                for row in cursor.fetchall():
                    flight = dict(row)
                    process_flight_events(flight, events, start_of_week, end_of_week)

                # Build week structure
                days = []
                for i in range(7):
                    day_date = start_of_week + timedelta(days=i)
                    days.append({
                        'date': day_date,
                        'day_name': day_date.strftime('%A'),
                        'day': day_date.day,
                        'month': day_date.month,
                        'year': day_date.year,
                        'is_today': day_date == today,
                        'events': events.get(day_date, [])
                    })

                template_data = {
                    'weeks': None,
                    'week_data': {
                        'start_date': start_of_week,
                        'end_date': end_of_week,
                        'days': days
                    },
                    'day_data': None
                }

            else:  # day view
                # Day view query
                cursor.execute("""
                    SELECT id, company_flight_ref, passenger_name, passenger_id,
                           departure_date, departure_time, departure_country, departure_airport,
                           arrival_date, arrival_time, arrival_country, arrival_airport
                    FROM Flights
                    WHERE departure_date = ? OR arrival_date = ?
                    ORDER BY COALESCE(departure_time, arrival_time)
                """, [current_date.isoformat()] * 2)

                # Process day events
                events = []
                for row in cursor.fetchall():
                    flight = dict(row)
                    if flight['departure_date']:
                        dep_date = datetime.strptime(str(flight['departure_date']), '%Y-%m-%d').date()
                        if dep_date == current_date:
                            events.append({
                                'type': 'departure',
                                'time': flight['departure_time'],
                                'country': flight['departure_country'],
                                'airport': flight['departure_airport'],
                                'passenger': flight['passenger_name'],
                                'passenger_id': flight['passenger_id'],
                                'ref': flight['company_flight_ref'],
                                'flight_id': flight['id'],
                                'css_class': 'event-departure'
                            })

                    if flight['arrival_date']:
                        arr_date = datetime.strptime(str(flight['arrival_date']), '%Y-%m-%d').date()
                        if arr_date == current_date:
                            events.append({
                                'type': 'arrival',
                                'time': flight['arrival_time'],
                                'country': flight['arrival_country'],
                                'airport': flight['arrival_airport'],
                                'passenger': flight['passenger_name'],
                                'passenger_id': flight['passenger_id'],
                                'ref': flight['company_flight_ref'],
                                'flight_id': flight['id'],
                                'css_class': 'event-arrival'
                            })

                template_data = {
                    'weeks': None,
                    'week_data': None,
                    'day_data': {
                        'date': current_date,
                        'day_name': current_date.strftime('%A'),
                        'month_name': current_date.strftime('%B'),
                        'is_today': current_date == today,
                        'events': sorted(events, key=lambda x: x['time'])
                    }
                }

            # Common template data
            template_data.update({
                'current_view': view,
                'month_name': current_date.strftime('%B %Y'),
                'today': today,
                'current_year': year,
                'current_month': month,
                'current_day': day,
                'prev_year': prev_date.year,
                'prev_month': prev_date.month,
                'prev_day': prev_date.day,
                'next_year': next_date.year,
                'next_month': next_date.month,
                'next_day': next_date.day
            })

            update_user_activity(
                session['user_id'],
                f"Viewed {view} calendar for {current_date.strftime('%Y-%m-%d')}"
            )
            return render_template('flights/calendar.html', **template_data)

    except (ValueError, TypeError) as e:
        flash(f"Invalid date parameters: {str(e)}", "danger")
        return redirect(url_for('flight_calendar'))
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "danger")
        return redirect(url_for('view_flights'))
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "danger")
        return redirect(url_for('main_menu'))


@app.route('/flights/<int:flight_id>')
@login_required
def view_flight_details(flight_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    f.*, 
                    u1.username as created_by_name,
                    u2.username as updated_by_name
                FROM Flights f
                LEFT JOIN Users u1 ON f.created_by = u1.id
                LEFT JOIN Users u2 ON f.updated_by = u2.id
                WHERE f.id = ?
            """, (flight_id,))

            flight = cursor.fetchone()

            if not flight:
                flash("Flight not found", "danger")
                return redirect(url_for('view_flights'))

            return render_template('flights/flight_details.html', flight=dict(flight))

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('view_flights'))


@app.route('/flights/edit/<int:flight_id>', methods=['GET', 'POST'])
@login_required
def edit_flight(flight_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if request.method == 'POST':
                validate_csrf(request.form.get('csrf_token'))

                # Get all form data
                company_flight_ref = request.form['company_flight_ref']
                pnr_ticket_number = request.form['pnr_ticket_number']
                ticket_status = request.form['ticket_status']
                flight_type = request.form['flight_type']
                passenger_id = request.form['passenger_id']
                flight_route = request.form['flight_route']

                # Get passenger details
                cursor.execute("""
                    SELECT DisplayName, Designation, Company 
                    FROM Employees 
                    WHERE EmployeeId = ?
                """, (passenger_id,))
                passenger = cursor.fetchone()

                if not passenger:
                    flash("Passenger not found in database", "danger")
                    return redirect(url_for('edit_flight', flight_id=flight_id))

                passenger_name = passenger['DisplayName']
                designation = passenger['Designation']
                company = passenger['Company']

                # Get departure details
                departure_country = request.form.get('departure_country')
                departure_airport = request.form.get('departure_airport')
                departure_date = request.form.get('departure_date')
                departure_time = request.form.get('departure_time')
                departure_airline = request.form.get('departure_airline')

                # Handle transit details
                has_transit = 'has_transit' in request.form
                transit_country = request.form.get('transit_country', '')
                transit_airport = request.form.get('transit_airport', '')
                transit_hours = request.form.get('transit_hours', '')
                transit_airline = request.form.get('transit_airline', '')

                # Get arrival details
                arrival_country = request.form['arrival_country']
                arrival_airport = request.form['arrival_airport']
                arrival_date = request.form['arrival_date']
                arrival_time = request.form['arrival_time']
                arrival_airline = request.form['arrival_airline']

                # Initialize ticket document variables
                new_ticket_document = None
                delete_ticket = False
                current_ticket_document = None

                # Get current ticket document path first
                cursor.execute("SELECT ticket_document FROM Flights WHERE id = ?", (flight_id,))
                current_ticket_document = cursor.fetchone()['ticket_document']

                # Handle file upload if new file was provided
                if 'ticket_document' in request.files:
                    file = request.files['ticket_document']
                    if file and file.filename and allowed_file(file.filename):
                        # Generate unique filename
                        filename = secure_filename(
                            f"ticket_{flight_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                        file_path = os.path.join(app.config['TICKET_DOCS_FOLDER'], filename)

                        # Save new file
                        file.save(file_path)
                        new_ticket_document = f"ticket_docs/{filename}"

                        # Delete old file if it exists (only after new file is successfully saved)
                        if current_ticket_document:
                            try:
                                os.remove(os.path.join(app.static_folder, current_ticket_document))
                            except OSError as e:
                                print(f"Error deleting old ticket file: {e}")
                    elif file.filename:  # File was uploaded but not allowed type
                        flash("Invalid file type. Only PDF, JPG, and PNG files are allowed.", "warning")

                # Handle explicit document deletion
                if 'delete_ticket_document' in request.form and request.form['delete_ticket_document'] == 'on':
                    delete_ticket = True
                    if current_ticket_document:
                        try:
                            os.remove(os.path.join(app.static_folder, current_ticket_document))
                        except OSError as e:
                            print(f"Error deleting ticket file: {e}")

                # Determine what to store in database
                final_ticket_document = None
                if new_ticket_document:
                    final_ticket_document = new_ticket_document
                elif delete_ticket:
                    final_ticket_document = None  # Will set to NULL in DB
                else:
                    final_ticket_document = current_ticket_document  # Keep existing

                # Update flight in database
                cursor.execute("""
                    UPDATE Flights SET
                        company_flight_ref = ?,
                        pnr_ticket_number = ?,
                        ticket_status = ?,
                        flight_type = ?,
                        passenger_id = ?,
                        passenger_name = ?,
                        designation = ?,
                        company = ?,
                        flight_route = ?,
                        departure_country = ?,
                        departure_airport = ?,
                        departure_date = ?,
                        departure_time = ?,
                        departure_airline = ?,
                        has_transit = ?,
                        transit_country = ?,
                        transit_airport = ?,
                        transit_hours = ?,
                        transit_airline = ?,
                        arrival_country = ?,
                        arrival_airport = ?,
                        arrival_date = ?,
                        arrival_time = ?,
                        arrival_airline = ?,
                        ticket_document = ?,
                        updated_at = ?,
                        updated_by = ?
                    WHERE id = ?
                """, (
                    company_flight_ref,
                    pnr_ticket_number,
                    ticket_status,
                    flight_type,
                    passenger_id,
                    passenger_name,
                    designation,
                    company,
                    flight_route,
                    departure_country,
                    departure_airport,
                    departure_date,
                    departure_time,
                    departure_airline,
                    has_transit,
                    transit_country,
                    transit_airport,
                    transit_hours,
                    transit_airline,
                    arrival_country,
                    arrival_airport,
                    arrival_date,
                    arrival_time,
                    arrival_airline,
                    final_ticket_document,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    session['user_id'],
                    flight_id
                ))
                conn.commit()

                flash("Flight details updated successfully!", "success")
                return redirect(url_for('view_flight_details', flight_id=flight_id))

            else:
                # GET request - load flight data
                cursor.execute("""
                    SELECT f.*, u.username as created_by_name 
                    FROM Flights f
                    LEFT JOIN Users u ON f.created_by = u.id
                    WHERE f.id = ?
                """, (flight_id,))
                flight = cursor.fetchone()

                if not flight:
                    flash("Flight not found", "danger")
                    return redirect(url_for('view_flights'))

                # Get list of employees for dropdown
                cursor.execute("SELECT EmployeeId, DisplayName FROM Employees ORDER BY DisplayName")
                employees = cursor.fetchall()

                return render_template('flights/edit_flight.html',
                                       flight=dict(flight),
                                       employees=employees)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('view_flights'))


# Update your existing ticket_document route to force download
@app.route('/ticket_docs/<path:filename>')
@login_required
def ticket_document(filename):
    try:
        # Secure the filename to prevent directory traversal
        safe_filename = secure_filename(filename)
        if not safe_filename:
            abort(404)

        # Check if file exists
        filepath = os.path.join(app.config['TICKET_DOCS_FOLDER'], safe_filename)
        if not os.path.exists(filepath):
            abort(404)

        return send_from_directory(
            app.config['TICKET_DOCS_FOLDER'],
            safe_filename,
            as_attachment=True
        )
    except Exception as e:
        app.logger.error(f"Error downloading ticket: {str(e)}")
        abort(404)
# Add this route to your Python code
@app.route('/reports/flight_records', methods=['GET', 'POST'])
@login_required
def flight_records_report():
    if request.method == 'POST':
        try:
            # Get filter parameters from form
            date_from = request.form.get('date_from')
            date_to = request.form.get('date_to')
            flight_type = request.form.get('flight_type')
            ticket_status = request.form.get('ticket_status')
            company = request.form.get('company')

            # Build query based on filters
            query = """
                SELECT 
                    f.id, f.company_flight_ref, f.pnr_ticket_number, f.ticket_status,
                    f.flight_type, f.passenger_name, f.designation, f.company,
                    f.flight_route, f.departure_airport, f.departure_date, f.departure_time,
                    f.arrival_airport, f.arrival_date, f.arrival_time, 
                    u.username as created_by, f.created_at
                FROM Flights f
                LEFT JOIN Users u ON f.created_by = u.id
                WHERE 1=1
            """
            params = []

            if date_from:
                query += " AND (f.departure_date >= ? OR f.arrival_date >= ?)"
                params.extend([date_from, date_from])
            if date_to:
                query += " AND (f.departure_date <= ? OR f.arrival_date <= ?)"
                params.extend([date_to, date_to])
            if flight_type and flight_type != 'all':
                query += " AND f.flight_type = ?"
                params.append(flight_type)
            if ticket_status and ticket_status != 'all':
                query += " AND f.ticket_status = ?"
                params.append(ticket_status)
            if company and company != 'all':
                query += " AND f.company = ?"
                params.append(company)

            query += " ORDER BY f.departure_date, f.departure_time"

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                flights = [dict(row) for row in cursor.fetchall()]

                # Get distinct values for dropdowns
                cursor.execute("SELECT DISTINCT flight_type FROM Flights ORDER BY flight_type")
                flight_types = [row['flight_type'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT ticket_status FROM Flights ORDER BY ticket_status")
                ticket_statuses = [row['ticket_status'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT company FROM Flights ORDER BY company")
                companies = [row['company'] for row in cursor.fetchall()]

                # Handle export requests
                if 'export' in request.form:
                    output = io.StringIO()
                    writer = csv.writer(output)

                    # Write header
                    writer.writerow([
                        'Ref No', 'PNR/Ticket', 'Status', 'Type', 'Passenger',
                        'Designation', 'Company', 'Route', 'Departure Airport',
                        'Departure Date', 'Departure Time', 'Arrival Airport',
                        'Arrival Date', 'Arrival Time', 'Created By', 'Created At'
                    ])

                    # Write data
                    for flight in flights:
                        writer.writerow([
                            flight['company_flight_ref'],
                            flight['pnr_ticket_number'],
                            flight['ticket_status'],
                            flight['flight_type'],
                            flight['passenger_name'],
                            flight['designation'],
                            flight['company'],
                            flight['flight_route'],
                            flight['departure_airport'],
                            flight['departure_date'],
                            flight['departure_time'],
                            flight['arrival_airport'],
                            flight['arrival_date'],
                            flight['arrival_time'],
                            flight['created_by'],
                            flight['created_at']
                        ])

                    output.seek(0)

                    # Log the export activity
                    update_user_activity(session['user_id'], "Exported flight records to CSV")

                    return Response(
                        output,
                        mimetype="text/csv",
                        headers={"Content-Disposition": "attachment;filename=flight_records.csv"}
                    )

                update_user_activity(session['user_id'], "Generated flight records report")
                return render_template('/flights/flight_records_report.html',
                                       flights=flights,
                                       flight_types=flight_types,
                                       ticket_statuses=ticket_statuses,
                                       companies=companies,
                                       filters=request.form)

        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")
            return redirect(url_for('flight_records_report'))

    # GET request - show empty form
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT flight_type FROM Flights ORDER BY flight_type")
            flight_types = [row['flight_type'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT ticket_status FROM Flights ORDER BY ticket_status")
            ticket_statuses = [row['ticket_status'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT company FROM Flights ORDER BY company")
            companies = [row['company'] for row in cursor.fetchall()]

            return render_template('flights/flight_records_report.html',
                                   flight_types=flight_types,
                                   ticket_statuses=ticket_statuses,
                                   companies=companies)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('main_menu'))


# Add this route for viewing tickets (add with your other routes)
@app.route('/view_ticket/<path:filename>')
@login_required
def view_ticket(filename):
    try:
        # Secure the filename to prevent directory traversal
        safe_filename = secure_filename(filename)
        if not safe_filename:
            abort(404)

        # Check if file exists
        filepath = os.path.join(app.config['TICKET_DOCS_FOLDER'], safe_filename)
        if not os.path.exists(filepath):
            abort(404)

        # Determine content type based on file extension
        ext = os.path.splitext(safe_filename)[1].lower()
        mimetype = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png'
        }.get(ext, 'application/octet-stream')

        # For images and PDFs, send the file to be displayed in browser
        if ext in ['.pdf', '.jpg', '.jpeg', '.png']:
            return send_from_directory(
                app.config['TICKET_DOCS_FOLDER'],
                safe_filename,
                mimetype=mimetype
            )
        else:
            # For other file types, force download
            return send_from_directory(
                app.config['TICKET_DOCS_FOLDER'],
                safe_filename,
                as_attachment=True
            )

    except Exception as e:
        app.logger.error(f"Error viewing ticket: {str(e)}")
        abort(404)



@app.route('/trips/new', methods=['GET', 'POST'])
@login_required
def new_trip():
    if request.method == 'POST':
        try:
            # Validate CSRF token
            validate_csrf(request.form.get('csrf_token'))

            # Handle ticket document upload
            ticket_document = None
            if 'ticket_document' in request.files and request.files['ticket_document'].filename:
                file = request.files['ticket_document']
                if allowed_file(file.filename):
                    filename = secure_filename(f"ticket_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    file_path = os.path.join(app.config['TICKET_DOCS_FOLDER'], filename)
                    file.save(file_path)
                    ticket_document = f"ticket_docs/{filename}"
                else:
                    flash("Invalid file type for ticket document. Allowed: pdf, png, jpg, jpeg", "warning")


            # Get basic flight details
            company_flight_ref = request.form['company_flight_ref']
            pnr_ticket_number = request.form['pnr_ticket_number']
            ticket_status = request.form['ticket_status']
            flight_type = request.form['flight_type']
            passenger_id = request.form['passenger_id']
            flight_route = request.form['flight_route']

            # Get passenger details from Employees table
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DisplayName, Designation, Company 
                    FROM Employees 
                    WHERE EmployeeId = ?
                """, (passenger_id,))
                passenger = cursor.fetchone()

                if not passenger:
                    flash("Passenger not found in database", "danger")
                    return redirect(url_for('new_trip'))

                passenger_name = passenger['DisplayName']
                designation = passenger['Designation']
                company = passenger['Company']

            # Get departure details
            departure_country = request.form.get('departure_country')
            departure_airport = request.form.get('departure_airport')
            departure_date = request.form.get('departure_date')
            departure_time = request.form.get('departure_time')
            departure_airline = request.form.get('departure_airline')

            # Handle transit details
            has_transit = 'has_transit' in request.form
            transit_country = request.form.get('transit_country', '')
            transit_airport = request.form.get('transit_airport', '')
            transit_hours = request.form.get('transit_hours', '')
            transit_airline = request.form.get('transit_airline', '')

            # Get arrival details
            arrival_country = request.form['arrival_country']
            arrival_airport = request.form['arrival_airport']
            arrival_date = request.form['arrival_date']
            arrival_time = request.form['arrival_time']
            arrival_airline = request.form['arrival_airline']

            # Insert flight into database
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Flights (
                        company_flight_ref, pnr_ticket_number, ticket_status, flight_type,
                        passenger_id, passenger_name, designation, company, flight_route,
                        departure_country, departure_airport, departure_date, departure_time, departure_airline,
                        has_transit, transit_country, transit_airport, transit_hours, transit_airline,
                        arrival_country, arrival_airport, arrival_date, arrival_time, arrival_airline,
                        ticket_document, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_flight_ref, pnr_ticket_number, ticket_status, flight_type,
                    passenger_id, passenger_name, designation, company, flight_route,
                    departure_country, departure_airport, departure_date, departure_time, departure_airline,
                    has_transit, transit_country, transit_airport, transit_hours, transit_airline,
                    arrival_country, arrival_airport, arrival_date, arrival_time, arrival_airline,
                    ticket_document,  # Add this
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    session['user_id']
                ))
                conn.commit()


            flash("Flight details saved successfully!", "success")
            return redirect(url_for('view_flights'))

        except Exception as e:
            flash(f"Error saving flight details: {str(e)}", "danger")

    # For GET request, get list of employees for passenger dropdown
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EmployeeId, DisplayName FROM Employees ORDER BY DisplayName")
            employees = cursor.fetchall()

        return render_template('flights/new_trip.html', employees=employees)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('main_menu'))


@app.route('/flights/delete/<int:flight_id>', methods=['POST'])
@login_required
def delete_flight(flight_id):
    try:
        # Validate CSRF token
        validate_csrf(request.headers.get('X-CSRFToken'))

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if flight exists
            cursor.execute("SELECT id FROM Flights WHERE id = ?", (flight_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Flight not found'}), 404

            # Delete the flight
            cursor.execute("DELETE FROM Flights WHERE id = ?", (flight_id,))
            conn.commit()

            update_user_activity(session['user_id'], f"Deleted flight ID {flight_id}")
            return jsonify({'success': True, 'message': 'Flight deleted successfully'})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/search_profile', methods=['GET', 'POST'])
@login_required
def search_profile():
    # Initialize default values
    search_query = request.form.get('name', '')
    search_field = request.form.get('search_field', 'all')
    employment_type = request.form.get('employment_type', '')
    status = request.form.get('status', '')
    retired = request.form.get('retired', '')
    field_site = request.form.get('field_site', '')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Base query
            query = "SELECT * FROM Employees WHERE 1=1"
            params = []

            # Handle search query based on search field
            if search_query:
                if search_field == 'all':
                    query += " AND (DisplayName LIKE ? OR FullNameArabic LIKE ? OR EmployeeId LIKE ? OR Designation LIKE ? OR Company LIKE ?)"
                    params.extend([f'%{search_query}%'] * 5)
                elif search_field == 'name':
                    query += " AND (DisplayName LIKE ? OR FullNameArabic LIKE ?)"
                    params.extend([f'%{search_query}%'] * 2)
                elif search_field == 'id':
                    query += " AND EmployeeId LIKE ?"
                    params.append(f'%{search_query}%')
                elif search_field == 'department':
                    query += " AND Designation LIKE ?"
                    params.append(f'%{search_query}%')
                elif search_field == 'company':
                    query += " AND Company LIKE ?"
                    params.append(f'%{search_query}%')

            # Add filters for other fields
            if employment_type:
                query += " AND EmploymentType = ?"
                params.append(employment_type)

            if status:
                query += " AND Status = ?"
                params.append(status)

            if retired:
                query += " AND Retired = ?"
                params.append(retired)

            if field_site:
                query += " AND FieldSite = ?"
                params.append(field_site)

            # Execute the query
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Log the activity
            update_user_activity(session['user_id'], f"Employee search with filters: {request.form}")

            return render_template('search_profile.html', results=results, request=request)

    except sqlite3.Error as e:
        flash(f"Search error: {e}", "danger")
        return render_template('search_profile.html', results=[], request=request)


@app.route('/reports', methods=['GET', 'POST'])
@login_required
def generate_reports():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        filter_value = request.form.get('filter_value')

        if not report_type or not filter_value:
            flash("Please select both report type and filter value", "danger")
            return redirect(url_for('generate_reports'))

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                if report_type == 'all':
                    cursor.execute("SELECT * FROM Employees")
                else:
                    cursor.execute(f"SELECT * FROM Employees WHERE {report_type} = ?", (filter_value,))

                employees = [dict(row) for row in cursor.fetchall()]

                if not employees:
                    flash("No employees found matching your criteria", "warning")
                    return redirect(url_for('generate_reports'))

                cursor.execute("SELECT DISTINCT Company FROM Employees ORDER BY Company")
                companies = [row['Company'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT Status FROM Employees ORDER BY Status")
                statuses = [row['Status'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT FieldOfAssignment FROM Employees ORDER BY FieldOfAssignment")
                fields = [row['FieldOfAssignment'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT FieldSite FROM Employees ORDER BY FieldSite")
                sites = [row['FieldSite'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT Nationality FROM Employees ORDER BY Nationality")
                nationalities = [row['Nationality'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT Designation FROM Employees ORDER BY Designation")
                designations = [row['Designation'] for row in cursor.fetchall()]

                cursor.execute("SELECT DISTINCT EmploymentType FROM Employees ORDER BY EmploymentType")
                employment_types = [row['EmploymentType'] for row in cursor.fetchall()]

                update_user_activity(session['user_id'], f"Generated report: {report_type}={filter_value}")
                return render_template('report_results.html',
                                       employees=employees,
                                       report_type=report_type,
                                       filter_value=filter_value,
                                       companies=companies,
                                       statuses=statuses,
                                       fields=fields,
                                       sites=sites,
                                       nationalities=nationalities,
                                       designations=designations,
                                       employment_types=employment_types)

        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")
            return redirect(url_for('generate_reports'))

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT Company FROM Employees ORDER BY Company")
            companies = [row['Company'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT Status FROM Employees ORDER BY Status")
            statuses = [row['Status'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT FieldOfAssignment FROM Employees ORDER BY FieldOfAssignment")
            fields = [row['FieldOfAssignment'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT FieldSite FROM Employees ORDER BY FieldSite")
            sites = [row['FieldSite'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT Nationality FROM Employees ORDER BY Nationality")
            nationalities = [row['Nationality'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT Designation FROM Employees ORDER BY Designation")
            designations = [row['Designation'] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT EmploymentType FROM Employees ORDER BY EmploymentType")
            employment_types = [row['EmploymentType'] for row in cursor.fetchall()]

            return render_template('generate_reports.html',
                                   companies=companies,
                                   statuses=statuses,
                                   fields=fields,
                                   sites=sites,
                                   nationalities=nationalities,
                                   designations=designations,
                                   employment_types=employment_types)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('main_menu'))


@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    return value.strftime(format)


@app.template_filter('is_expired')
def is_expired(date_str):
    if not date_str:
        return False
    try:
        expiry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        return expiry_date < date.today()
    except ValueError:
        return False


@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
@app.route('/calendar/<int:year>/<int:month>/<int:day>')
@login_required
def calendar_view(year=None, month=None, day=None):
    # Get view type from query params
    current_view = request.args.get('view', 'month')

    # Set default to current date if not provided
    today = datetime.now().date()
    if None in (year, month):
        year, month = today.year, today.month
    if day is None:
        day = today.day

    # Ensure valid date parameters
    year, month, day = int(year), int(month), int(day)
    current_date = date(year, month, day)

    # Calculate navigation dates
    if current_view == 'month':
        prev_date = current_date - relativedelta(months=1)
        next_date = current_date + relativedelta(months=1)
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
    elif current_view == 'week':
        prev_date = current_date - timedelta(weeks=1)
        next_date = current_date + timedelta(weeks=1)
        start_of_week = current_date - timedelta(days=current_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
    else:  # day view
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get all employees with their birthdays and document expiries
            cursor.execute("""
                SELECT 
                    EmployeeId,
                    DisplayName,
                    Birthday,
                    PassportExpiryDate as passport,
                    DesertPassExpiryDate as desert,
                    BusinessVisaExpiryDate as business,
                    ResidenceVisaExpiryDate as residence
                FROM Employees
                WHERE 
                    Birthday IS NOT NULL OR
                    PassportExpiryDate IS NOT NULL OR
                    DesertPassExpiryDate IS NOT NULL OR
                    BusinessVisaExpiryDate IS NOT NULL OR
                    ResidenceVisaExpiryDate IS NOT NULL
            """)

            employees = [dict(row) for row in cursor.fetchall()]

            if current_view == 'month':
                # Process into month calendar structure
                events = {}
                for emp in employees:
                    # Add birthdays - compare month and day only
                    if emp['Birthday']:
                        try:
                            bday = datetime.strptime(emp['Birthday'], '%Y-%m-%d').date()
                            # Check if birthday falls in current month (any year)
                            if bday.month == month:
                                # Create date in current year for display
                                bday_date = date(year, bday.month, bday.day)
                                if bday_date not in events:
                                    events[bday_date] = []
                                events[bday_date].append({
                                    'name': emp['DisplayName'],
                                    'type': 'birthday',
                                    'id': emp['EmployeeId']
                                })
                        except ValueError:
                            continue

                    # Add document expiries
                    for doc_type in ['passport', 'desert', 'business', 'residence']:
                        if emp[doc_type]:
                            try:
                                expiry_date = datetime.strptime(emp[doc_type], '%Y-%m-%d').date()
                                if first_day <= expiry_date <= last_day:
                                    if expiry_date not in events:
                                        events[expiry_date] = []
                                    events[expiry_date].append({
                                        'name': emp['DisplayName'],
                                        'type': doc_type,
                                        'id': emp['EmployeeId']
                                    })
                            except ValueError:
                                continue

                # Build month grid
                month_weeks = []
                week = []
                current_day = first_day

                # Pad beginning of month
                for _ in range(first_day.weekday()):
                    week.append(None)

                while current_day <= last_day:
                    if len(week) == 7:
                        month_weeks.append(week)
                        week = []

                    day_events = events.get(current_day, [])
                    week.append({
                        'date': current_day,
                        'day': current_day.day,
                        'events': day_events,
                        'is_today': current_day == today
                    })
                    current_day += timedelta(days=1)

                # Pad end of month
                if week:
                    week.extend([None] * (7 - len(week)))
                    month_weeks.append(week)

                template_data = {
                    'month_weeks': month_weeks,
                    'week_days': None,
                    'day_events': None
                }

            elif current_view == 'week':
                # Process into week structure
                events = {}
                for emp in employees:
                    # Add birthdays - compare month and day only
                    if emp['Birthday']:
                        try:
                            bday = datetime.strptime(emp['Birthday'], '%Y-%m-%d').date()
                            # Create date in current year for comparison
                            bday_current_year = date(year, bday.month, bday.day)
                            if start_of_week <= bday_current_year <= end_of_week:
                                if bday_current_year not in events:
                                    events[bday_current_year] = []
                                events[bday_current_year].append({
                                    'name': emp['DisplayName'],
                                    'type': 'birthday',
                                    'id': emp['EmployeeId']
                                })
                        except ValueError:
                            continue

                    # Add document expiries
                    for doc_type in ['passport', 'desert', 'business', 'residence']:
                        if emp[doc_type]:
                            try:
                                expiry_date = datetime.strptime(emp[doc_type], '%Y-%m-%d').date()
                                if start_of_week <= expiry_date <= end_of_week:
                                    if expiry_date not in events:
                                        events[expiry_date] = []
                                    events[expiry_date].append({
                                        'name': emp['DisplayName'],
                                        'type': doc_type,
                                        'id': emp['EmployeeId']
                                    })
                            except ValueError:
                                continue

                # Build week structure
                week_days = []
                for i in range(7):
                    day_date = start_of_week + timedelta(days=i)
                    week_days.append({
                        'date': day_date,
                        'events': events.get(day_date, [])
                    })

                template_data = {
                    'month_weeks': None,
                    'week_days': week_days,
                    'day_events': None,
                    'week_start': start_of_week,
                    'week_end': end_of_week
                }

            else:  # day view
                # Process day events
                day_events = []
                for emp in employees:
                    # Check for birthdays - compare month and day only
                    if emp['Birthday']:
                        try:
                            bday = datetime.strptime(emp['Birthday'], '%Y-%m-%d').date()
                            if bday.month == current_date.month and bday.day == current_date.day:
                                day_events.append({
                                    'name': emp['DisplayName'],
                                    'type': 'birthday',
                                    'id': emp['EmployeeId'],
                                    'time': None  # All day event
                                })
                        except ValueError:
                            continue

                    # Check for document expiries
                    for doc_type in ['passport', 'desert', 'business', 'residence']:
                        if emp[doc_type]:
                            try:
                                expiry_date = datetime.strptime(emp[doc_type], '%Y-%m-%d').date()
                                if expiry_date == current_date:
                                    day_events.append({
                                        'name': emp['DisplayName'],
                                        'type': doc_type,
                                        'id': emp['EmployeeId'],
                                        'time': None  # All day event
                                    })
                            except ValueError:
                                continue

                template_data = {
                    'month_weeks': None,
                    'week_days': None,
                    'day_events': day_events
                }

            # Common template data
            template_data.update({
                'current_view': current_view,
                'current_date': current_date,
                'today': today,
                'prev_year': prev_date.year,
                'prev_month': prev_date.month,
                'prev_day': prev_date.day,
                'next_year': next_date.year,
                'next_month': next_date.month,
                'next_day': next_date.day
            })

            update_user_activity(
                session['user_id'],
                f"Viewed {current_view} calendar for {current_date.strftime('%Y-%m-%d')}"
            )
            return render_template('calendar.html', **template_data)

    except (ValueError, TypeError) as e:
        flash(f"Invalid date parameters: {str(e)}", "danger")
        return redirect(url_for('calendar_view'))
    except sqlite3.Error as e:
        flash(f"Database error: {str(e)}", "danger")
        return redirect(url_for('main_menu'))
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "danger")
        return redirect(url_for('main_menu'))


@app.route('/reports/expiries')
@login_required
def expiry_reports():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Company FROM Employees ORDER BY Company")
            companies = [row['Company'] for row in cursor.fetchall()]

            return render_template('expiry_reports.html',
                                   companies=companies,
                                   today=date.today())

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('main_menu'))


@app.route('/reports/expiries/generate', methods=['POST'])
@login_required
def generate_expiry_report():
    try:
        company = request.form.get('company')
        days_threshold = int(request.form.get('days_threshold', 30))
        today = date.today()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    EmployeeId,
                    DisplayName,
                    Company,
                    PassportExpiryDate,
                    DesertPassExpiryDate,
                    BusinessVisaExpiryDate,
                    ResidenceVisaExpiryDate
                FROM Employees
                WHERE ? = '' OR Company = ?
            """, (company or '', company or ''))

            employees = []
            for row in cursor.fetchall():
                emp = dict(row)
                docs = [
                    ('Passport', emp['PassportExpiryDate']),
                    ('Desert Pass', emp['DesertPassExpiryDate']),
                    ('Business Visa', emp['BusinessVisaExpiryDate']),
                    ('Residence Visa', emp['ResidenceVisaExpiryDate'])
                ]

                emp['expiring_docs'] = []
                for name, expiry in docs:
                    if expiry:
                        try:
                            expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                            days_remaining = (expiry_date - today).days
                            if days_remaining <= days_threshold:
                                status = 'expired' if days_remaining < 0 else 'warning' if days_remaining <= 30 else 'upcoming'
                                emp['expiring_docs'].append({
                                    'name': name,
                                    'date': expiry_date.strftime('%Y-%m-%d'),
                                    'days': days_remaining,
                                    'status': status
                                })
                        except ValueError:
                            continue

                if emp['expiring_docs']:
                    employees.append(emp)

            update_user_activity(session['user_id'], f"Generated expiry report for {company or 'all companies'}")
            return render_template('expiry_report_results.html',
                                   employees=employees,
                                   company=company or 'All Companies',
                                   days_threshold=days_threshold,
                                   today=today)

    except sqlite3.Error as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('expiry_reports'))


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')


@app.route('/terms-and-conditions')
def terms_and_conditions():
    return render_template('terms_and_conditions.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/visa_docs/<filename>')
def visa_document(filename):
    return send_from_directory(app.config['VISA_DOCS_FOLDER'], filename)


@app.route('/passport_docs/<filename>')
def passport_document(filename):
    return send_from_directory(app.config['PASSPORT_DOCS_FOLDER'], filename)


@app.template_filter('days_until_expiry')
def days_until_expiry(date_str):
    if not date_str:
        return float('inf')  # Return infinity if no date is provided

    try:
        expiry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        delta = expiry_date - today
        return delta.days
    except ValueError:
        return float('inf')  # Return infinity if date format is invalid


# Help Center routes
@app.route('/help')
@login_required
def help_center():
    update_user_activity(session['user_id'], "Accessed Help Center")
    return render_template('help_center.html')


@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact_us():
    if request.method == 'POST':
        try:
            validate_csrf(request.form.get('csrf_token'))

            name = request.form['name']
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['message']

            # Here you would typically send an email or save to database
            # For now, we'll just log it
            print(f"Contact Form Submission:\nName: {name}\nEmail: {email}\nSubject: {subject}\nMessage: {message}")

            flash("Your message has been sent successfully! We'll get back to you soon.", "success")
            update_user_activity(session['user_id'], "Submitted contact form")
            return redirect(url_for('contact_us'))

        except Exception as e:
            flash(f"Error submitting form: {str(e)}", "danger")

    update_user_activity(session['user_id'], "Accessed Contact Us")
    return render_template('contact_us.html')


if __name__ == '__main__':
    try:
        # Initialize database
        init_db()

        # Run the app
        app.run(host="0.0.0.0", port=8000, debug=True)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)