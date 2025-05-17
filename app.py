from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session handling

# Initialize DB only once at startup
def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        roll TEXT,
        email TEXT UNIQUE,
        password TEXT,
        grade TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    current_date = datetime.now()
    return render_template('index.html', date=current_date)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = (
            request.form['name'],
            request.form['roll'],
            request.form['email'],
            request.form['password'],
            request.form['grade']
        )
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO students (name, roll, email, password, grade) VALUES (?, ?, ?, ?, ?)", data)
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered!"
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['student_id'] = user[0]
            session['name'] = user[1]
            return redirect('/student/dashboard')
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect('/admin/dashboard')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', students=students)

@app.route('/admin/attendance', methods=['GET', 'POST'])
def mark_attendance():
    if 'admin' not in session:
        return redirect('/admin')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    if request.method == 'POST':
        attendance_date = request.form['date']
        for student_id, status in request.form.items():
            if student_id != 'date':
                cur.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                            (student_id, attendance_date, status))
        conn.commit()
        conn.close()
        return redirect('/admin/dashboard')
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    return render_template('attendance.html', students=students)

@app.route('/admin/report')
def report():
    if 'admin' not in session:
        return redirect('/admin')
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT s.name, 
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
    """)
    data = cur.fetchall()
    conn.close()
    return render_template('report.html', data=data)

@app.route('/student/dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/login')
    student_id = session['student_id']
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT date, status FROM attendance WHERE student_id=?", (student_id,))
    records = cur.fetchall()
    total = len(records)
    present = sum(1 for r in records if r[1] == 'Present')
    percentage = (present / total * 100) if total > 0 else 0
    conn.close()
    return render_template('student_dashboard.html', records=records, percentage=percentage)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)