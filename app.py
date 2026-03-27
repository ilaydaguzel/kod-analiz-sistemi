import json
import os
import mysql.connector
import pandas as pd
from mysql.connector import IntegrityError
from flask import Flask, render_template, redirect, url_for, request, session
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = "secret"


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.environ.get("MYSQL_DATABASE_PASSWORD"),
        database="code_analyzer"
    )


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password2 = request.form["password2"]
        role = request.form['role']
        if password != password2:
            return "Şifreler uyuşmuyor"
        hashed_password = generate_password_hash(password)
        conn = None
        cur = None

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users(username, password, role) VALUES(%s, %s, %s)",
                (username, hashed_password, role)
            )
            conn.commit()

        except IntegrityError:
            return "Bu kullanıcı adı zaten kayıtlı"


        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = None
        cur = None

        try:
            conn = get_db_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, username, password, role FROM users WHERE username=%s",
                (username,)
            )
            user = cur.fetchone()

        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "teacher":
                return redirect(url_for("teacher_panel"))
            else:
                return redirect(url_for("student_panel"))

        return "Hatalı giriş!"

    return render_template("login.html")

@app.route('/student')
def student_panel():
    if "user_id" not in session or session.get("role") != "student":
        return "Yetki yok"

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                homework_assignments.id AS assignment_id,
                homeworks.id AS homework_id,
                homeworks.title,
                homeworks.description,
                homeworks.language,
                homeworks.due_date,
                homeworks.max_score,
                homework_assignments.status
            FROM homework_assignments
            JOIN homeworks ON homework_assignments.homework_id = homeworks.id
            WHERE homework_assignments.student_id = %s
            ORDER BY homeworks.due_date ASC
        """, (session["user_id"],))

        homeworks = cursor.fetchall()

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    return render_template("student.html", homeworks=homeworks)

@app.route('/student/homework/<int:homework_id>')
def student_homework(homework_id):
    if "user_id" not in session or session.get("role") != "student":
        return "Yetki yok"

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                homeworks.id,
                homeworks.title,
                homeworks.description,
                homeworks.language,
                homeworks.due_date,
                homeworks.max_score,
                homework_assignments.status
            FROM homework_assignments
            JOIN homeworks ON homework_assignments.homework_id = homeworks.id
            WHERE homework_assignments.student_id = %s AND homeworks.id = %s
        """, (session["user_id"], homework_id))

        homework = cursor.fetchone()

        if not homework:
            return "Ödev bulunamadı"

        cursor.execute("""
            UPDATE homework_assignments
            SET status = 'started'
            WHERE student_id = %s AND homework_id = %s AND status = 'assigned'
        """, (session["user_id"], homework_id))

        connection.commit()

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    return render_template("student_homework.html", homework=homework)

@app.route('/save_analysis', methods=['POST'])
def save_analysis():
    if session.get("role") != "student":
        return {"status": "error", "message": "Yetki yok"}, 403

    data = request.get_json()

    insert_count = data.get("insert", 0)
    delete_count = data.get("delete", 0)
    pause_count = data.get("pause", 0)
    paste_count = data.get("paste", 0)
    total_time = data.get("time", 0)
    line_count = data.get("length", 0)

    timeline = data.get("timeline", [])
    pause_timeline = data.get("pauseTimeline", [])

    typing_speed = 0
    if total_time and total_time > 0:
        typing_speed = insert_count / total_time

    edit_ratio = 0
    if insert_count and insert_count > 0:
        edit_ratio = delete_count / insert_count

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO code_analysis
            (username, insert_count, delete_count, pause_count,
             total_time, typing_speed, edit_ratio,
             paste_count, line_count, timeline, pause_timeline)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["username"],
                insert_count,
                delete_count,
                pause_count,
                total_time,
                typing_speed,
                edit_ratio,
                paste_count,
                line_count,
                json.dumps(timeline),
                json.dumps(pause_timeline)
            )
        )

        conn.commit()

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    return {"status": "ok"}


@app.route('/teacher')
def teacher_panel():
    if session.get('role') != 'teacher':
        return "Yetki yok"

    conn = None
    cur = None
    analysis_rows = []
    homeworks = []

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, title, description, language, due_date, max_score, created_at
            FROM homeworks
            WHERE teacher_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))
        homeworks = cur.fetchall()

        # Eski analizler
        cur.execute("SELECT * FROM code_analysis ORDER BY created_at DESC")
        analysis_rows = cur.fetchall()

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    avg_speed = 0
    avg_edit_ratio = 0
    fastest_student = None
    most_pause_student = None
    most_edit_student = None
    charts = []

    if analysis_rows:
        df = pd.DataFrame(analysis_rows)

        if "typing_speed" in df.columns:
            avg_speed = round(df["typing_speed"].mean(), 2)
            fastest_student = df.loc[df["typing_speed"].idxmax()].to_dict()

        if "edit_ratio" in df.columns:
            avg_edit_ratio = round(df["edit_ratio"].mean(), 2)
            most_edit_student = df.loc[df["edit_ratio"].idxmax()].to_dict()

        if "pause_count" in df.columns:
            most_pause_student = df.loc[df["pause_count"].idxmax()].to_dict()

        def classify(row):
            if row.get("paste_count", 0) > 0 and row.get("typing_speed", 0) > 4:
                return "Olası Kopyalama"
            elif row.get("pause_count", 0) >= 2:
                return "Düşünerek Yazıyor"
            elif row.get("edit_ratio", 0) > 0.3:
                return "Deneme-Yanılma"
            elif row.get("typing_speed", 0) > 4 and row.get("pause_count", 0) <= 1:
                return "Hızlı Yazıcı"
            else:
                return "Normal"

        df["behavior"] = df.apply(classify, axis=1)
        analysis_rows = df.to_dict(orient="records")

        for i, row in enumerate(analysis_rows):
            timeline_data = []
            pause_data = []

            if row.get("timeline"):
                timeline_data = json.loads(row["timeline"])

            if row.get("pause_timeline"):
                pause_data = json.loads(row["pause_timeline"])

            charts.append({
                "chart_id": f"timelineChart{i}",
                "title": f"Analysis {i+1} - {row['created_at']}",
                "timeline": timeline_data,
                "pauses": pause_data
            })

    return render_template(
        "teacher.html",
        homeworks=homeworks,
        analysis_rows=analysis_rows,
        avg_speed=avg_speed,
        avg_edit_ratio=avg_edit_ratio,
        fastest_student=fastest_student,
        most_pause_student=most_pause_student,
        most_edit_student=most_edit_student,
        charts=charts
    )
@app.route('/create_homework', methods=['GET', 'POST'])
def create_homework():
    if "user_id" not in session or session.get("role") != "teacher":
        return "Bu sayfaya erişim yetkiniz yok."

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        language = request.form['language']
        due_date = request.form['due_date']
        max_score = request.form['max_score']

        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO homeworks (teacher_id, title, description, language, due_date, max_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session["user_id"], title, description, language, due_date, max_score))

            homework_id = cursor.lastrowid

            cursor.execute("SELECT id FROM users WHERE role = 'student'")
            students = cursor.fetchall()

            for student in students:
                cursor.execute("""
                    INSERT INTO homework_assignments (homework_id, student_id, status)
                    VALUES (%s, %s, %s)
                """, (homework_id, student["id"], "assigned"))

            connection.commit()

        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

        return redirect(url_for('teacher_panel'))

    return render_template('create_homework.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)