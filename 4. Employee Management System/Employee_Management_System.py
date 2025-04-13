import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from datetime import datetime
import re
from contextlib import contextmanager
from typing import Optional, Dict, Any

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect('employees.db')
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        error_message = f"Database error: {e}"
        print(error_message)
        flash(error_message, 'danger')
        raise
    finally:
        if conn:
            conn.close()


def init_db():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Employees (
                    EmployeeId TEXT PRIMARY KEY,
                    FirstName TEXT NOT NULL,
                    MiddleName TEXT,
                    LastName TEXT NOT NULL,
                    DisplayName TEXT NOT NULL,
                    FullNameArabic TEXT,
                    EmploymentType TEXT NOT NULL,
                    Nationality TEXT NOT NULL,
                    NationalityArabic TEXT,
                    PassportNumber TEXT NOT NULL,
                    Designation TEXT NOT NULL,
                    DesignationArabic TEXT,
                    Company TEXT NOT NULL,
                    CompanyArabic TEXT,
                    PhotoPath TEXT,
                    FieldOfAssignment TEXT NOT NULL,
                    FieldSite TEXT NOT NULL,
                    Rotation TEXT NOT NULL,
                    Birthday DATE NOT NULL,
                    Age INTEGER,
                    EmailAddress TEXT,
                    ContactNumber TEXT NOT NULL,
                    Rate REAL NOT NULL,
                    RateDescription TEXT NOT NULL,
                    ArrivalDate DATE NOT NULL,
                    StartedDate DATE NOT NULL,
                    Retired TEXT NOT NULL,
                    Status TEXT NOT NULL
                );
            """)
            conn.commit()
    except sqlite3.Error as e:
        error_message = f"Error initializing database: {e}"
        print(error_message)
        flash(error_message, "danger")
        abort(500)


init_db()


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
    # Process all form fields
    first_name = form['first_name']
    middle_name = form['middle_name']
    last_name = form['last_name']
    display_name = _generate_display_name(first_name, middle_name, last_name)

    # Handle file upload
    photo_path = None
    if 'photo' in files and files['photo']:
        photo = files['photo']
        if allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            # Store path relative to static folder
            photo_path = f"uploads/{filename}"
            absolute_path = os.path.join(app.static_folder, photo_path)
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            photo.save(absolute_path)
        else:
            raise ValueError("Invalid file type. Allowed: png, jpg, jpeg, gif")

    # Validate required fields
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

    # Process dates
    try:
        birthday = datetime.strptime(form['birthday'], '%Y-%m-%d').date()
        age = calculate_age(birthday)
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

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
        'Retired': form['retired'],
        'Status': form['status']
    }


@app.route('/')
def main_menu():
    return render_template('main_menu.html')


@app.route('/register', methods=['GET', 'POST'])
def register_employee():
    if request.method == 'POST':
        try:
            employee_data = _process_employee_form(request.form, request.files, request.form['employee_id'])

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Employees VALUES (
                        :EmployeeId, :FirstName, :MiddleName, :LastName, :DisplayName, 
                        :FullNameArabic, :EmploymentType, :Nationality, :NationalityArabic, 
                        :PassportNumber, :Designation, :DesignationArabic, :Company, 
                        :CompanyArabic, :PhotoPath, :FieldOfAssignment, :FieldSite, 
                        :Rotation, :Birthday, :Age, :EmailAddress, :ContactNumber, 
                        :Rate, :RateDescription, :ArrivalDate, :StartedDate, 
                        :Retired, :Status
                    )
                """, employee_data)
                conn.commit()
                flash("Employee registered successfully!", "success")
                return redirect(url_for('employee_list'))

        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")

    return render_template('register_employee.html')


@app.route('/employee_details', methods=['GET', 'POST'])
def employee_details():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        employee = get_employee_by_id(employee_id)
        if employee:
            return render_template('employee_details.html', employee=employee)
        flash("Employee not found.", "danger")
    return redirect(url_for('employee_list'))


@app.route('/update/<employee_id>', methods=['GET', 'POST'])
def update_employee(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash("Employee not found.", 'danger')
        return redirect(url_for('employee_list'))

    if request.method == 'POST':
        try:
            employee_data = _process_employee_form(request.form, request.files, employee_id, is_update=True)

            # Keep existing photo if no new one uploaded
            if not employee_data['PhotoPath']:
                employee_data['PhotoPath'] = employee['PhotoPath']

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Employees SET 
                        FirstName = :FirstName, MiddleName = :MiddleName, LastName = :LastName,
                        DisplayName = :DisplayName, FullNameArabic = :FullNameArabic,
                        EmploymentType = :EmploymentType, Nationality = :Nationality,
                        NationalityArabic = :NationalityArabic, PassportNumber = :PassportNumber,
                        Designation = :Designation, DesignationArabic = :DesignationArabic,
                        Company = :Company, CompanyArabic = :CompanyArabic, PhotoPath = :PhotoPath,
                        FieldOfAssignment = :FieldOfAssignment, FieldSite = :FieldSite,
                        Rotation = :Rotation, Birthday = :Birthday, Age = :Age,
                        EmailAddress = :EmailAddress, ContactNumber = :ContactNumber,
                        Rate = :Rate, RateDescription = :RateDescription,
                        ArrivalDate = :ArrivalDate, StartedDate = :StartedDate,
                        Retired = :Retired, Status = :Status
                    WHERE EmployeeId = :EmployeeId
                """, employee_data)
                conn.commit()
                flash("Employee updated successfully!", "success")
                return redirect(url_for('view_profile', employee_id=employee_id))

        except ValueError as e:
            flash(str(e), "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")

    return render_template('update_employee_form.html', employee=employee)


@app.route('/list')
def employee_list():
    employees = get_all_employees()
    return render_template('employee_list.html', employees=employees)


@app.route('/delete/<employee_id>', methods=['POST'])
def delete(employee_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT PhotoPath FROM Employees WHERE EmployeeId = ?', (employee_id,))
            photo_path = cursor.fetchone()['PhotoPath']

            cursor.execute('DELETE FROM Employees WHERE EmployeeId = ?', (employee_id,))
            conn.commit()

            if photo_path:
                full_path = os.path.join(app.static_folder, photo_path)
                if os.path.exists(full_path):
                    os.remove(full_path)

            flash("Employee deleted successfully!", "success")
    except sqlite3.Error as e:
        flash(f"Error deleting employee: {e}", "danger")

    return redirect(url_for('employee_list'))


@app.route('/profile/<employee_id>')
def view_profile(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('employee_list'))

    # Verify photo exists
    if employee['PhotoPath']:
        photo_path = os.path.join(app.static_folder, employee['PhotoPath'])
        if not os.path.exists(photo_path):
            employee['PhotoPath'] = None

    return render_template('employee_profile.html', employee=employee)


@app.route('/search_profile', methods=['GET', 'POST'])
def search_profile():
    if request.method == 'POST':
        name = request.form['name']
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM Employees WHERE DisplayName LIKE ? OR FullNameArabic LIKE ?",
                    (f'%{name}%', f'%{name}%')
                )
                results = [dict(row) for row in cursor.fetchall()]
                return render_template('search_profile.html', results=results)
        except sqlite3.Error as e:
            flash(f"Search error: {e}", "danger")

    return render_template('search_profile.html', results=[])


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)